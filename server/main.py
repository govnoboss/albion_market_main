from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import secrets
import os
import json # Added for JSON serialization
import base64 # Added for signature encoding
import re
import urllib.request
import urllib.error
from pathlib import Path

# Cryptography Imports
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from database import SessionLocal, License, PurchaseSession, PurchaseItem, init_db

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

# === Public download page (GitHub Releases) ===
# Configurable via env vars so you can reuse this server for different repos/assets.
DOWNLOAD_GITHUB_REPO = os.getenv("DOWNLOAD_GITHUB_REPO", "govnoboss/albion_market_main")
DOWNLOAD_ASSET_NAME = os.getenv("DOWNLOAD_ASSET_NAME", "")  # e.g. "GBot.zip"
DOWNLOAD_ASSET_REGEX = os.getenv("DOWNLOAD_ASSET_REGEX", r"\.zip$")
DOWNLOAD_CACHE_TTL_SECONDS = int(os.getenv("DOWNLOAD_CACHE_TTL_SECONDS", "300"))  # 5 min default

_latest_release_cache: dict = {"fetched_at": 0.0, "data": None}

def _github_api_get_json(url: str, timeout_seconds: int = 10) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "gbot-license-server",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))

def _select_release_asset(release_data: dict) -> dict | None:
    assets = release_data.get("assets") or []
    if not assets:
        return None

    if DOWNLOAD_ASSET_NAME:
        for a in assets:
            if (a.get("name") or "") == DOWNLOAD_ASSET_NAME:
                return a

    try:
        rx = re.compile(DOWNLOAD_ASSET_REGEX, re.IGNORECASE)
    except re.error:
        rx = re.compile(r"\.zip$", re.IGNORECASE)

    for a in assets:
        name = (a.get("name") or "")
        if rx.search(name):
            return a

    return None

def get_latest_release_info() -> dict | None:
    """
    Returns cached latest release info or fetches from GitHub.
    Shape:
      {
        "repo": "...",
        "tag": "v1.2.3",
        "name": "...",
        "html_url": "...",
        "published_at": "...",
        "body": "...",
        "asset_name": "...",
        "asset_size": 123,
        "download_url": "https://.../asset.zip"
      }
    """
    now_ts = time.time()
    cached = _latest_release_cache.get("data")
    fetched_at = float(_latest_release_cache.get("fetched_at") or 0.0)
    if cached and (now_ts - fetched_at) < DOWNLOAD_CACHE_TTL_SECONDS:
        return cached

    try:
        url = f"https://api.github.com/repos/{DOWNLOAD_GITHUB_REPO}/releases/latest"
        data = _github_api_get_json(url)

        asset = _select_release_asset(data)
        download_url = asset.get("browser_download_url") if asset else None

        info = {
            "repo": DOWNLOAD_GITHUB_REPO,
            "tag": data.get("tag_name") or "",
            "name": data.get("name") or "",
            "html_url": data.get("html_url") or f"https://github.com/{DOWNLOAD_GITHUB_REPO}/releases/latest",
            "published_at": data.get("published_at") or "",
            "body": data.get("body") or "",
            "asset_name": (asset.get("name") if asset else "") or "",
            "asset_size": int(asset.get("size") or 0) if asset else 0,
            "download_url": download_url or "",
        }

        _latest_release_cache["data"] = info
        _latest_release_cache["fetched_at"] = now_ts
        return info
    except urllib.error.HTTPError as e:
        logger.warning(f"[DOWNLOAD] GitHub HTTP error: {e.code}")
        return cached
    except Exception as e:
        logger.warning(f"[DOWNLOAD] Failed to fetch latest release: {e}")
        return cached

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

class SessionItemDetail(BaseModel):
    name: str
    qty: int = 0
    spent: int = 0
    profit: int = 0

class SessionReportRequest(BaseModel):
    key: str
    hwid: str
    session_id: str
    city: str = ""
    items_bought: int = 0
    total_spent: int = 0
    total_profit_est: int = 0
    duration_seconds: int = 0
    items_detail: List[SessionItemDetail] = []

# NEW Response Model with Signature
class SignedResponse(BaseModel):
    data: Dict[str, Any]
    signature: str
    timestamp: float

class AdminGenerateRequest(BaseModel):
    admin_password: str
    days: int = 30
    count: int = 1
    note: Optional[str] = None

# --- Events ---
@app.on_event("startup")
def on_startup():
    init_db()

# --- Endpoints ---

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/download", status_code=302)

@app.get("/download", response_class=HTMLResponse, include_in_schema=False)
def download_page(request: Request):
    release = get_latest_release_info()
    return templates.TemplateResponse("download.html", {
        "request": request,
        "session_active": False,
        "release": release,
        "github_repo": DOWNLOAD_GITHUB_REPO,
    })

@app.get("/download/latest", include_in_schema=False)
def download_latest():
    release = get_latest_release_info() or {}
    url = (release.get("download_url") or "").strip()
    if url:
        # Redirect directly to the asset (GitHub serves the file)
        return RedirectResponse(url, status_code=302)
    return RedirectResponse(f"https://github.com/{DOWNLOAD_GITHUB_REPO}/releases/latest", status_code=302)

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
        
        # Start timer if duration_days is set
        if license_obj.duration_days is not None:
            license_obj.expires_at = datetime.utcnow() + timedelta(days=license_obj.duration_days)
            license_obj.duration_days = None
            
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
        # Initial long expiry date (year 2099ish) so it doesn't expire before activation
        expires_placeholder = datetime.utcnow() + timedelta(days=36500)
        new_license = License(
            key=key_str,
            expires_at=expires_placeholder,
            duration_days=req.days,
            note=req.note
        )
        db.add(new_license)
        generated.append(key_str)
        
    db.commit()
    
    return {"count": req.count, "keys": generated, "days": req.days, "note": req.note}

# === TELEMETRY ENDPOINT ===

@app.post("/api/v1/report-session")
@limiter.limit("10/minute")
def report_session(request: Request, req: SessionReportRequest, db: Session = Depends(get_db)):
    """
    Receives aggregated purchase session data from buyer clients.
    Validates license key, deduplicates by session_id.
    """
    # Validate license key exists and is active
    license_obj = db.query(License).filter(License.key == req.key).first()
    if not license_obj:
        return JSONResponse(status_code=403, content={"status": "error", "message": "Invalid key"})
    
    if not license_obj.is_active:
        return JSONResponse(status_code=403, content={"status": "error", "message": "Key disabled"})
    
    if license_obj.hwid and license_obj.hwid != req.hwid:
        return JSONResponse(status_code=403, content={"status": "error", "message": "HWID mismatch"})
    
    # Skip empty sessions
    if req.items_bought <= 0:
        return {"status": "skipped", "message": "No items bought"}
    
    # Dedup: check if session_id already exists
    existing = db.query(PurchaseSession).filter(PurchaseSession.session_id == req.session_id).first()
    if existing:
        return {"status": "duplicate", "message": "Session already reported"}
    
    # Save session
    client_ip = get_real_ip(request)
    session = PurchaseSession(
        session_id=req.session_id,
        license_key=req.key,
        city=req.city,
        items_bought=req.items_bought,
        total_spent=req.total_spent,
        total_profit_est=req.total_profit_est,
        duration_seconds=req.duration_seconds,
        client_ip=client_ip
    )
    db.add(session)
    
    # Save per-item breakdown (up to 20 items)
    for item_data in req.items_detail[:20]:
        pi = PurchaseItem(
            session_id=req.session_id,
            item_name=item_data.name,
            qty=item_data.qty,
            total_spent=item_data.spent,
            profit_est=item_data.profit
        )
        db.add(pi)
    
    db.commit()
    
    logger.info(f"{client_ip} | REPORT | {req.city} | {req.items_bought} items | {req.total_spent} silver | profit {req.total_profit_est} | {len(req.items_detail)} item types")
    
    return {"status": "ok", "message": "Session recorded"}

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

@app.get("/admin/stats", response_class=HTMLResponse)
def admin_stats(request: Request, days: int = 30, db: Session = Depends(get_db)):
    """Purchase statistics page with KPI cards and session table"""
    if not verify_admin_session(request):
        return RedirectResponse("/admin/login", status_code=302)
    
    now = datetime.utcnow()
    
    # --- License Stats ---
    all_licenses = db.query(License).all()
    total_users = sum(1 for l in all_licenses if l.is_active and l.hwid and l.expires_at > now)
    five_min_ago = now - timedelta(minutes=5)
    online_users = sum(1 for l in all_licenses if l.last_seen and l.last_seen >= five_min_ago)
    
    # --- Purchase Stats (period filter) ---
    period_start = now - timedelta(days=days)
    
    # All-time aggregates
    from sqlalchemy import func
    all_time = db.query(
        func.coalesce(func.sum(PurchaseSession.total_spent), 0),
        func.coalesce(func.sum(PurchaseSession.total_profit_est), 0),
        func.coalesce(func.sum(PurchaseSession.items_bought), 0),
        func.count(PurchaseSession.id)
    ).first()
    
    # Period aggregates
    period = db.query(
        func.coalesce(func.sum(PurchaseSession.total_spent), 0),
        func.coalesce(func.sum(PurchaseSession.total_profit_est), 0),
        func.coalesce(func.sum(PurchaseSession.items_bought), 0),
        func.count(PurchaseSession.id)
    ).filter(PurchaseSession.timestamp >= period_start).first()
    
    # Today aggregates
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today = db.query(
        func.coalesce(func.sum(PurchaseSession.total_spent), 0),
        func.coalesce(func.sum(PurchaseSession.total_profit_est), 0),
        func.coalesce(func.sum(PurchaseSession.items_bought), 0)
    ).filter(PurchaseSession.timestamp >= today_start).first()
    
    # Sessions list (period, limited to 100)
    sessions = db.query(PurchaseSession).filter(
        PurchaseSession.timestamp >= period_start
    ).order_by(PurchaseSession.timestamp.desc()).limit(100).all()
    
    # Compute derived fields for each session
    for s in sessions:
        s.revenue = s.total_spent + s.total_profit_est  # Expected revenue
        s.margin = round((s.total_profit_est / s.total_spent * 100), 1) if s.total_spent > 0 else 0
    
    # Top 5 most bought items for period
    session_ids_in_period = db.query(PurchaseSession.session_id).filter(
        PurchaseSession.timestamp >= period_start
    ).subquery()
    
    top_items_raw = db.query(
        PurchaseItem.item_name,
        func.sum(PurchaseItem.qty).label('total_qty'),
        func.sum(PurchaseItem.total_spent).label('total_spent'),
        func.sum(PurchaseItem.profit_est).label('total_profit')
    ).filter(
        PurchaseItem.session_id.in_(session_ids_in_period)
    ).group_by(PurchaseItem.item_name).order_by(
        func.sum(PurchaseItem.qty).desc()
    ).limit(5).all()
    
    top_items = []
    for item in top_items_raw:
        top_items.append({
            "name": item.item_name,
            "qty": item.total_qty,
            "spent": item.total_spent,
            "profit": item.total_profit,
            "margin": round((item.total_profit / item.total_spent * 100), 1) if item.total_spent > 0 else 0
        })
    
    return templates.TemplateResponse("stats.html", {
        "request": request,
        "session_active": True,
        "days": days,
        # All-time KPIs
        "total_spent_all": all_time[0],
        "total_profit_all": all_time[1],
        "total_items_all": all_time[2],
        "total_sessions_all": all_time[3],
        # Period KPIs
        "total_spent": period[0],
        "total_profit": period[1],
        "total_items": period[2],
        "total_sessions": period[3],
        "total_investment": period[0],  # alias
        "total_revenue": period[0] + period[1],  # spent + profit = expected revenue
        # Today
        "today_spent": today[0],
        "today_profit": today[1],
        "today_items": today[2],
        # Users
        "total_users": total_users,
        "online_users": online_users,
        # Sessions table
        "sessions": sessions,
        # Top 5 items
        "top_items": top_items,
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
        # Note: if duration_days is set, it won't actually expire until activated.
        lic.is_expired = lic.expires_at <= now and lic.duration_days is None
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

@app.post("/admin/unbind/{key}")
def admin_unbind(request: Request, key: str, db: Session = Depends(get_db)):
    """Unbinds a key from its HWID without resetting its expiration timer."""
    if not verify_admin_session(request):
        return RedirectResponse("/admin/login", status_code=302)
        
    license_obj = db.query(License).filter(License.key == key).first()
    if license_obj:
        license_obj.hwid = None
        db.commit()
        
    return RedirectResponse("/admin/licenses", status_code=302)

@app.get("/admin/generate", response_class=HTMLResponse)
def admin_generate_page(request: Request):
    if not verify_admin_session(request):
        return RedirectResponse("/admin/login", status_code=302)
    return templates.TemplateResponse("generate.html", {
        "request": request,
        "session_active": True
    })

@app.post("/admin/generate", response_class=HTMLResponse)
def admin_generate_keys(request: Request, count: int = Form(...), days: int = Form(...), note: Optional[str] = Form(None), db: Session = Depends(get_db)):
    if not verify_admin_session(request):
        return RedirectResponse("/admin/login", status_code=302)
    
    generated = []
    # Initial long expiry date (year 2099ish) so it doesn't expire before activation
    expires_placeholder = datetime.utcnow() + timedelta(days=36500)
    
    for _ in range(min(count, 100)):  # Max 100 at a time
        key_str = License.generate_key()
        new_license = License(
            key=key_str,
            expires_at=expires_placeholder,
            duration_days=days,
            note=note
        )
        db.add(new_license)
        generated.append(key_str)
    
    db.commit()
    
    return templates.TemplateResponse("generate.html", {
        "request": request,
        "session_active": True,
        "generated_keys": generated,
        "expires_at": expires_placeholder.strftime("%d.%m.%Y %H:%M")
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

# === SESSION DETAIL & DELETE ===

@app.get("/admin/session/{session_id}", response_class=HTMLResponse)
def admin_session_detail(session_id: str, request: Request, db: Session = Depends(get_db)):
    """View details of a single purchase session"""
    if not verify_admin_session(request):
        return RedirectResponse("/admin/login", status_code=302)
    
    session_obj = db.query(PurchaseSession).filter(PurchaseSession.session_id == session_id).first()
    if not session_obj:
        return RedirectResponse("/admin/stats", status_code=302)
    
    # Compute derived fields
    session_obj.revenue = session_obj.total_spent + session_obj.total_profit_est
    session_obj.margin = round((session_obj.total_profit_est / session_obj.total_spent * 100), 1) if session_obj.total_spent > 0 else 0
    
    # Get per-item breakdown
    items = db.query(PurchaseItem).filter(PurchaseItem.session_id == session_id).order_by(PurchaseItem.qty.desc()).all()
    
    for item in items:
        item.margin = round((item.profit_est / item.total_spent * 100), 1) if item.total_spent > 0 else 0
    
    return templates.TemplateResponse("session_detail.html", {
        "request": request,
        "session_active": True,
        "s": session_obj,
        "items": items,
    })

@app.post("/admin/session/{session_id}/delete")
def admin_delete_session(session_id: str, request: Request, db: Session = Depends(get_db)):
    """Delete a purchase session and its items"""
    if not verify_admin_session(request):
        return RedirectResponse("/admin/login", status_code=302)
    
    # Delete items first
    db.query(PurchaseItem).filter(PurchaseItem.session_id == session_id).delete()
    # Delete session
    db.query(PurchaseSession).filter(PurchaseSession.session_id == session_id).delete()
    db.commit()
    
    return RedirectResponse("/admin/stats", status_code=302)

if __name__ == "__main__":
    import uvicorn
    # Run localhost on port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)

