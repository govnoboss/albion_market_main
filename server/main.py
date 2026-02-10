from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import os
import json # Added for JSON serialization
import base64 # Added for signature encoding
from pathlib import Path

# Cryptography Imports
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import SessionLocal, License, init_db

# Get the directory where this file is located
BASE_DIR = Path(__file__).resolve().parent

# Rate limiter - prioritize Fly-Client-IP header
def get_real_ip(request: Request):
    client_host = request.client.host if request.client else "127.0.0.1"
    return request.headers.get("fly-client-ip") or client_host

limiter = Limiter(key_func=get_real_ip)

# Admin password (MUST be set via environment variable!)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD environment variable is required!")

# --- RSA PRIVATE KEY LOADING ---
PRIVATE_KEY = None

def load_private_key():
    global PRIVATE_KEY
    # 1. Try Environment Variable
    env_key = os.getenv("LICENSE_PRIVATE_KEY")
    if env_key:
        try:
            # Fix newlines if passed as single line string in env
            if "-----BEGIN PRIVATE KEY-----" not in env_key:
                 env_key = env_key.replace(" ", "\n")
                 env_key = f"-----BEGIN PRIVATE KEY-----\n{env_key}\n-----END PRIVATE KEY-----"
            
            PRIVATE_KEY = serialization.load_pem_private_key(
                env_key.encode(),
                password=None
            )
            print("RSA Private Key loaded from Environment.")
            return
        except Exception as e:
            print(f"Failed to load key from ENV: {e}")

    # 2. Try File (Development)
    key_path = BASE_DIR.parent / "keys" / "private.pem"
    if key_path.exists():
        try:
            with open(key_path, "rb") as f:
                PRIVATE_KEY = serialization.load_pem_private_key(
                    f.read(),
                    password=None
                )
            print(f"RSA Private Key loaded from file: {key_path}")
            return
        except Exception as e:
            print(f"Failed to load key from file: {e}")
            
    print("WARNING: NO PRIVATE KEY LOADED! SIGNING WILL FAIL.")

# Load key on startup
load_private_key()

def sign_data(data: Dict[str, Any]) -> str:
    """
    Signs a dictionary using RSA Private Key.
    Returns base64 encoded signature.
    """
    if not PRIVATE_KEY:
        return "NO_KEY"
        
    try:
        # Canonical JSON string: sorted keys, no spaces
        canonical_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
        
        signature = PRIVATE_KEY.sign(
            canonical_json.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode()
    except Exception as e:
        print(f"Signing error: {e}")
        return "SIGN_ERROR"


# Admin sessions are now stateless (JWT in cookies)


app = FastAPI(
    title="GBot License Server",
    docs_url=None,      # Disable /docs
    redoc_url=None,     # Disable /redoc
    openapi_url=None    # Disable /openapi.json
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration - allows admin panel to work from any origin
# In production, replace "*" with your actual domain
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev: allow all. Production: ["https://yourdomain.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

# Mount static files and templates (using absolute paths)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Request Logging Middleware
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("gbot_server")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Log the request (skip static files to reduce noise)
    if not request.url.path.startswith("/static"):
        logger.info(
            f"{client_ip} | {request.method} {request.url.path} | "
            f"Status: {response.status_code} | Time: {duration:.3f}s"
        )
    
    return response

# --- Dependencies ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Models ---
class LicenseCheckRequest(BaseModel):
    key: str
    hwid: str

class LicenseActivateRequest(BaseModel):
    key: str
    hwid: str

class HeartbeatRequest(BaseModel):
    key: str
    hwid: str

# NEW Response Model with Signature
class SignedResponse(BaseModel):
    data: Dict[str, Any]
    signature: str
    timestamp: float

class AdminGenerateRequest(BaseModel):
    admin_password: str
    days: int = 30
    count: int = 1

# --- Events ---
@app.on_event("startup")
def on_startup():
    init_db()

# --- Endpoints ---

@app.post("/api/v1/validate", response_model=SignedResponse)
@limiter.limit("10/minute")
def validate_license(request: Request, req: LicenseCheckRequest, db: Session = Depends(get_db)):
    """
    Checks if the license is valid for the given HWID.
    Returns SIGNED response.
    """
    license_obj = db.query(License).filter(License.key == req.key).first()
    
    response_data = {}

    if not license_obj:
        response_data = {"status": "invalid", "message": "Key not found"}
    
    elif not license_obj.is_active:
        response_data = {"status": "invalid", "message": "Key is disabled"}

    # Check Expiry
    elif datetime.utcnow() > license_obj.expires_at:
        response_data = {"status": "expired", "expires_at": str(license_obj.expires_at)}

    # Check Binding
    elif license_obj.hwid is None:
        response_data = {"status": "unbound", "message": "Key is new, please activate"}

    elif license_obj.hwid != req.hwid:
        # Security by obscurity: don't tell the attacker WHY it failed
        response_data = {"status": "invalid", "message": "Key is invalid or disabled"}
    
    else:
        # Valid! Update last_seen and IP
        license_obj.last_seen = datetime.utcnow()
        license_obj.last_ip = get_real_ip(request)
        db.commit()
        response_data = {"status": "valid", "expires_at": str(license_obj.expires_at)}

    # SIGNING
    timestamp = datetime.utcnow().timestamp()
    
    # We sign the combination of data + timestamp
    payload_to_sign = response_data.copy()
    payload_to_sign["timestamp"] = timestamp
    
    sig = sign_data(payload_to_sign)

    return SignedResponse(
        data=response_data,
        signature=sig,
        timestamp=timestamp
    )

@app.post("/api/v1/heartbeat")
@limiter.limit("20/minute")
def heartbeat_endpoint(request: Request, data: HeartbeatRequest, db: Session = Depends(get_db)):
    """Updates the last_seen timestamp for a license"""
    license_obj = db.query(License).filter(License.key == data.key).first()
    
    if not license_obj:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Key not found"})
        
    if not license_obj.is_active:
        return JSONResponse(status_code=403, content={"status": "error", "message": "Key banned"})
        
    if license_obj.hwid != data.hwid:
         return JSONResponse(status_code=403, content={"status": "error", "message": "HWID Mismatch"})
         
    if datetime.utcnow() > license_obj.expires_at:
         return JSONResponse(status_code=403, content={"status": "error", "message": "Expired"})

    # Update last_seen and IP
    license_obj.last_seen = datetime.utcnow()
    license_obj.last_ip = get_real_ip(request)
    db.commit()
    
    return {"status": "ok"}

@app.post("/api/v1/activate", response_model=SignedResponse)
@limiter.limit("10/minute")
def activate_license(request: Request, req: LicenseActivateRequest, db: Session = Depends(get_db)):
    """
    Binds a new license key to a HWID.
    Returns SIGNED response.
    """
    license_obj = db.query(License).filter(License.key == req.key).first()
    
    response_data = {}

    if not license_obj:
         response_data = {"status": "invalid", "message": "Key not found"} # Keep consistant invalid status for missing keys

    elif license_obj.hwid is not None:
        if license_obj.hwid == req.hwid:
            response_data = {"status": "valid", "expires_at": str(license_obj.expires_at), "message": "Already bound to this PC"}
        else:
            response_data = {"status": "invalid", "message": "Key is invalid or disabled"}
            
    else:
        # Bind
        license_obj.hwid = req.hwid
        license_obj.last_seen = datetime.utcnow() # Update last_seen
        license_obj.last_ip = get_real_ip(request)
        db.commit()
        response_data = {"status": "valid", "expires_at": str(license_obj.expires_at), "message": "Activation successful"}

    # SIGNING
    timestamp = datetime.utcnow().timestamp()
    
    payload_to_sign = response_data.copy()
    payload_to_sign["timestamp"] = timestamp
    
    sig = sign_data(payload_to_sign)
    
    return SignedResponse(
        data=response_data,
        signature=sig,
        timestamp=timestamp
    )

@app.post("/api/v1/admin/generate")
@limiter.limit("5/minute")
def generate_keys(request: Request, req: AdminGenerateRequest, db: Session = Depends(get_db)):
    """
    Admin endpoint to create new keys.
    REPLACE 'secret_password' WITH A SECURE PASSWORD IN PRODUCTION!
    """
    if not secrets.compare_digest(req.admin_password, ADMIN_PASSWORD):
        raise HTTPException(status_code=403, detail="Invalid admin password")
        
    generated = []
    expires = datetime.now() + timedelta(days=req.days)
    
    for _ in range(req.count):
        key_str = License.generate_key()
        new_license = License(key=key_str, expires_at=expires)
        db.add(new_license)
        generated.append(key_str)
        
    db.commit()
    
    return {"count": req.count, "keys": generated, "expires_at": str(expires)}

# === ADMIN PANEL ROUTES ===

# --- JWT Authentication (Replaces in-memory sessions) ---
import jwt

# Using ADMIN_PASSWORD as the secret key for JWT (simple and effective for this use case)
# In a larger app, we'd want a separate SECRET_KEY
JWT_SECRET = ADMIN_PASSWORD
JWT_ALGORITHM = "HS256"
SESSION_DURATION_MINUTES = 60

def create_session_token() -> str:
    """Creates a JWT token for the admin session"""
    expiration = datetime.utcnow() + timedelta(minutes=SESSION_DURATION_MINUTES)
    payload = {
        "sub": "admin",
        "exp": expiration,
        "iat": datetime.utcnow()
    }
    encoded_jwt = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_admin_session(request: Request) -> bool:
    """
    Validates the admin session using JWT from the cookie.
    Stateless: Works even if the server restarts.
    """
    token = request.cookies.get("admin_session")
    if not token:
        return False
    
    try:
        # Verify signature and expiration
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Check if token is for admin (extra safety)
        if payload.get("sub") != "admin":
            return False
            
        return True
    except jwt.ExpiredSignatureError:
        # Token expired
        return False
    except jwt.InvalidTokenError:
        # Invalid token (tampered or wrong key)
        return False

@app.get("/admin/login", response_class=HTMLResponse)
@limiter.limit("10/minute")
def admin_login_page(request: Request):
    if verify_admin_session(request):
        return RedirectResponse("/admin/", status_code=302)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "session_active": False
    })

@app.post("/admin/login", response_class=HTMLResponse)
@limiter.limit("5/minute")
def admin_login(request: Request, password: str = Form(...)):
    if not secrets.compare_digest(password, ADMIN_PASSWORD):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "session_active": False,
            "message": "Неверный пароль",
            "message_type": "error"
        })
    
    # Generate JWT Token AND Redirect
    response = RedirectResponse("/admin/", status_code=302)
    
    token = create_session_token()
    
    # Set Secure Cookie
    response.set_cookie(
        key="admin_session",
        value=token,
        httponly=True,       # Prevent JS access (XSS protection)
        samesite="lax",      # Protect against CSRF
        secure=True,         # Only send over HTTPS (Critical for Fly.io)
        max_age=SESSION_DURATION_MINUTES * 60
    )
    
    return response

@app.get("/admin/logout")
def admin_logout(request: Request):
    response = RedirectResponse("/admin/login", status_code=302)
    response.delete_cookie("admin_session")
    return response

@app.get("/admin/", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    if not verify_admin_session(request):
        return RedirectResponse("/admin/login", status_code=302)
    
    now = datetime.utcnow()
    all_licenses = db.query(License).all()
    
    total = len(all_licenses)
    active = sum(1 for l in all_licenses if l.is_active and l.hwid and l.expires_at > now)
    expired = sum(1 for l in all_licenses if l.expires_at <= now)
    unbound = sum(1 for l in all_licenses if l.hwid is None and l.expires_at > now)
    
    # Online Users (seen in last 5 minutes)
    five_min_ago = now - timedelta(minutes=5)
    # Handle None in last_seen
    online_users = sum(1 for l in all_licenses if l.last_seen and l.last_seen >= five_min_ago)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "session_active": True,
        "total_keys": total,
        "active_keys": active,
        "expired_keys": expired,
        "unbound_keys": unbound,
        "online_users": online_users
    })

@app.get("/admin/licenses", response_class=HTMLResponse)
def admin_licenses(request: Request, search: str = "", status: str = "", db: Session = Depends(get_db)):
    if not verify_admin_session(request):
        return RedirectResponse("/admin/login", status_code=302)
    
    now = datetime.utcnow()
    query = db.query(License)
    
    # Search filter
    if search:
        query = query.filter(
            (License.key.contains(search)) | (License.hwid.contains(search))
        )
    
    licenses = query.all()
    
    # Add computed property for template
    five_min_ago = now - timedelta(minutes=5)
    
    for lic in licenses:
        lic.is_expired = lic.expires_at <= now
        # Check if online (seen in last 5 mins)
        lic.is_online = lic.last_seen and lic.last_seen >= five_min_ago
    
    # Status filter
    if status == "active":
        licenses = [l for l in licenses if l.is_active and l.hwid and not l.is_expired]
    elif status == "expired":
        licenses = [l for l in licenses if l.is_expired]
    elif status == "unbound":
        licenses = [l for l in licenses if l.hwid is None and not l.is_expired]
    
    return templates.TemplateResponse("licenses.html", {
        "request": request,
        "session_active": True,
        "licenses": licenses,
        "search": search,
        "status_filter": status
    })

@app.get("/admin/generate", response_class=HTMLResponse)
def admin_generate_page(request: Request):
    if not verify_admin_session(request):
        return RedirectResponse("/admin/login", status_code=302)
    return templates.TemplateResponse("generate.html", {
        "request": request,
        "session_active": True
    })

@app.post("/admin/generate", response_class=HTMLResponse)
def admin_generate_keys(request: Request, count: int = Form(...), days: int = Form(...), db: Session = Depends(get_db)):
    if not verify_admin_session(request):
        return RedirectResponse("/admin/login", status_code=302)
    
    generated = []
    expires = datetime.utcnow() + timedelta(days=days)
    
    for _ in range(min(count, 100)):  # Max 100 at a time
        key_str = License.generate_key()
        new_license = License(key=key_str, expires_at=expires)
        db.add(new_license)
        generated.append(key_str)
    
    db.commit()
    
    return templates.TemplateResponse("generate.html", {
        "request": request,
        "session_active": True,
        "generated_keys": generated,
        "expires_at": expires.strftime("%d.%m.%Y %H:%M")
    })

@app.post("/admin/deactivate/{key}")
def admin_deactivate_key(key: str, request: Request, db: Session = Depends(get_db)):
    if not verify_admin_session(request):
        return RedirectResponse("/admin/login", status_code=302)
    
    license_obj = db.query(License).filter(License.key == key).first()
    if license_obj:
        license_obj.is_active = False
        db.commit()
    
    return RedirectResponse("/admin/licenses", status_code=302)

@app.post("/admin/delete/{key}")
def admin_delete_key(key: str, request: Request, db: Session = Depends(get_db)):
    """Permanently delete a license key"""
    if not verify_admin_session(request):
        return RedirectResponse("/admin/login", status_code=302)
    
    license_obj = db.query(License).filter(License.key == key).first()
    if license_obj:
        db.delete(license_obj)
        db.commit()
    
    return RedirectResponse("/admin/licenses", status_code=302)

if __name__ == "__main__":
    import uvicorn
    # Run localhost on port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)

