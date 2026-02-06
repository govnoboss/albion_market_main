from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from database import SessionLocal, License, init_db

app = FastAPI(title="GBot License Server")

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

class LicenseResponse(BaseModel):
    status: str  # valid, expired, invalid, unbound, hwid_mismatch
    expires_at: Optional[str] = None
    message: Optional[str] = None

class AdminGenerateRequest(BaseModel):
    admin_password: str
    days: int = 30
    count: int = 1

# --- Events ---
@app.on_event("startup")
def on_startup():
    init_db()

# --- Endpoints ---

@app.post("/api/v1/validate", response_model=LicenseResponse)
def validate_license(req: LicenseCheckRequest, db: Session = Depends(get_db)):
    """
    Checks if the license is valid for the given HWID.
    """
    license_obj = db.query(License).filter(License.key == req.key).first()

    if not license_obj:
        return LicenseResponse(status="invalid", message="Key not found")

    if not license_obj.is_active:
        return LicenseResponse(status="invalid", message="Key is disabled")

    # Check Expiry
    if datetime.now() > license_obj.expires_at:
        return LicenseResponse(status="expired", expires_at=str(license_obj.expires_at))

    # Check Binding
    if license_obj.hwid is None:
        return LicenseResponse(status="unbound", message="Key is new, please activate")

    if license_obj.hwid != req.hwid:
        return LicenseResponse(status="hwid_mismatch", message="Key is bound to another PC")

    return LicenseResponse(status="valid", expires_at=str(license_obj.expires_at))

@app.post("/api/v1/activate", response_model=LicenseResponse)
def activate_license(req: LicenseActivateRequest, db: Session = Depends(get_db)):
    """
    Binds a new license key to a HWID.
    """
    license_obj = db.query(License).filter(License.key == req.key).first()

    if not license_obj:
        raise HTTPException(status_code=404, detail="Key not found")

    if license_obj.hwid is not None:
        if license_obj.hwid == req.hwid:
            return LicenseResponse(status="valid", expires_at=str(license_obj.expires_at), message="Already bound to this PC")
        else:
            return LicenseResponse(status="hwid_mismatch", message="Key already used on another PC")
            
    # Bind
    license_obj.hwid = req.hwid
    db.commit()
    
    return LicenseResponse(status="valid", expires_at=str(license_obj.expires_at), message="Activation successful")

@app.post("/api/v1/admin/generate")
def generate_keys(req: AdminGenerateRequest, db: Session = Depends(get_db)):
    """
    Admin endpoint to create new keys.
    REPLACE 'secret_password' WITH A SECURE PASSWORD IN PRODUCTION!
    """
    if req.admin_password != "secret_password":
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

if __name__ == "__main__":
    import uvicorn
    # Run localhost on port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
