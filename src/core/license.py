import subprocess
import hashlib
import requests
import json
import os
import sys
import base64
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Cryptography
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

# Production server URL
SERVER_URL = "https://gbot-license.fly.dev/api/v1"

# Secure storage location
APP_DATA_DIR = Path(os.getenv('LOCALAPPDATA', Path.home())) / '.gbot'
LICENSE_FILE = APP_DATA_DIR / 'license.dat'
HWID_FALLBACK_FILE = APP_DATA_DIR / '.hwid'
LAST_CHECK_FILE = APP_DATA_DIR / '.last_check'

# --- EMBEDDED PUBLIC KEY ---
# Replace this with the content of keys/public.pem
PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtHDocWXCv6ulUD7TgEEH
w2OVFQLsqcZsfEZjgKCkQQa3vSXcpRBYC9S2JzaxNHFnrcKy8q39HOly255jdkOS
n3w3lL2/T1DB5EKY5sp/63b78uOmoHsZD8HQFeApkGnvpcRsZzb1BNUNfsSBAqrq
3HWl+dnYTfk/STCkgWf+kN3FsYy4cYLR3yCdlB29EcYGg+tRKXrwi5fL+Kbksp67
UEgq5MV/9Sep0Zuj6hn7VkCnQJkym9whgbujb+UrKyJulkO0qxHMVUn1PfWRUyyF
MnY590eFH/j60TwT8zYi2Z7C51DzoEJSL2hoCczmfb99FQLqEyPIgJCDr8avpA36
/wIDAQAB
-----END PUBLIC KEY-----"""

class LicenseManager:
    def __init__(self):
        self.cached_key = None
        self.cached_status = False
        # Ensure app data directory exists
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load Public Key
        try:
            self.public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM)
        except Exception as e:
            print(f"CRITICAL: Failed to load public key: {e}")
            self.public_key = None

    def get_hwid(self) -> str:
        """
        Generates a unique Hardware ID based on Motherboard Serial + CPU ID.
        Works for Windows. Uses PowerShell (wmic is deprecated in Windows 11+).
        """
        try:
            # 1. Motherboard Serial (via PowerShell)
            cmd_mb = 'powershell -Command "Get-WmiObject Win32_BaseBoard | Select-Object -ExpandProperty SerialNumber"'
            mb_serial = subprocess.check_output(cmd_mb, shell=True, stderr=subprocess.DEVNULL).decode().strip()
            if not mb_serial or mb_serial == "None":
                mb_serial = "UNKNOWN_MB"

            # 2. CPU ID (via PowerShell)
            cmd_cpu = 'powershell -Command "Get-WmiObject Win32_Processor | Select-Object -ExpandProperty ProcessorId"'
            cpu_id = subprocess.check_output(cmd_cpu, shell=True, stderr=subprocess.DEVNULL).decode().strip()
            if not cpu_id or cpu_id == "None":
                cpu_id = "UNKNOWN_CPU"
            
            # 3. Windows Machine GUID (Registry) - Most reliable
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            
            raw_id = f"{mb_serial}_{cpu_id}_{machine_guid}"
            # Hash it to make it look nicer and hide raw serials
            return hashlib.sha256(raw_id.encode()).hexdigest().upper()[:32]
            
        except Exception as e:
            # Fallback: use persistent random ID stored locally
            # This ensures the same HWID is used consistently on this machine
            return self._get_fallback_hwid()
    
    def _get_fallback_hwid(self) -> str:
        """Generate or retrieve a persistent fallback HWID"""
        if HWID_FALLBACK_FILE.exists():
            try:
                return HWID_FALLBACK_FILE.read_text().strip()
            except:
                pass
        
        # Generate new persistent HWID
        import secrets
        fallback_hwid = secrets.token_hex(16).upper()
        try:
            HWID_FALLBACK_FILE.write_text(fallback_hwid)
        except:
            pass
        return fallback_hwid
    
    def _get_encryption_key(self) -> bytes:
        """Generate encryption key based on machine-specific data"""
        hwid = self.get_hwid()
        # Create a valid 32-byte key for Fernet-like encryption
        return hashlib.sha256(hwid.encode()).digest()
    
    def _simple_encrypt(self, data: str) -> str:
        """Simple XOR encryption with base64 encoding"""
        key = self._get_encryption_key()
        encrypted = bytes([ord(c) ^ key[i % len(key)] for i, c in enumerate(data)])
        return base64.b64encode(encrypted).decode()
    
    def _simple_decrypt(self, data: str) -> str:
        """Simple XOR decryption"""
        try:
            key = self._get_encryption_key()
            decoded = base64.b64decode(data.encode())
            decrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(decoded)])
            return decrypted.decode()
        except:
            return ""

    def save_key(self, key: str):
        """Saves the key locally (encrypted) to avoid re-typing"""
        try:
            encrypted = self._simple_encrypt(key.strip())
            LICENSE_FILE.write_text(encrypted)
        except Exception:
            pass

    def load_key(self) -> str:
        """Loads and decrypts key from local file"""
        if LICENSE_FILE.exists():
            try:
                encrypted = LICENSE_FILE.read_text().strip()
                return self._simple_decrypt(encrypted)
            except Exception:
                pass
        return ""
    
    def get_network_time(self) -> datetime:
        """
        Attempts to get accurate time from Google via HTTP headers.
        Falls back to system time but returns flag.
        """
        try:
            # Quick HEAD request to a reliable server
            response = requests.head("https://www.google.com", timeout=3)
            date_str = response.headers['Date']
            # Parse 'Sat, 07 Feb 2026 12:00:00 GMT'
            network_time = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
            return network_time.replace(tzinfo=timezone.utc)
        except Exception as e:
            # Fallback to local time (UTC)
            print(f"Time Check Failed: {e}")
            return datetime.now(timezone.utc)

    def verify_signature(self, response_json: dict) -> bool:
        """
        Verifies that the response was signed by our Private Key.
        Prevents Server Emulation attacks.
        """
        if not self.public_key:
            return False
            
        try:
            signature_b64 = response_json.get("signature")
            timestamp = response_json.get("timestamp")
            data = response_json.get("data")
            
            if not signature_b64 or not timestamp or not data:
                return False

            # 1. Reconstruct Payload
            payload = data.copy()
            payload["timestamp"] = timestamp
            
            canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
            
            # 2. Verify Signature
            signature = base64.b64decode(signature_b64)
            
            self.public_key.verify(
                signature,
                canonical_json.encode(),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            # 3. Verify Timestamp (Anti-Replay & Time Tamper)
            server_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            network_time = self.get_network_time()
            
            # Allow 10 minutes drift
            delta = abs((network_time - server_time).total_seconds())
            if delta > 600:
                print(f"Security: Time skew too large! Server: {server_time}, Network: {network_time}")
                return False
                
            return True
            
        except Exception as e:
            print(f"Security: Signature verification failed! {e}")
            return False

    def should_check_today(self) -> bool:
        """Returns True if we haven't validated today yet"""
        if not LAST_CHECK_FILE.exists():
            return True
        try:
            last_check_str = LAST_CHECK_FILE.read_text().strip()
            last_check = datetime.fromisoformat(last_check_str)
            return datetime.now() - last_check > timedelta(days=1)
        except:
            return True
    
    def mark_checked(self):
        """Mark that we validated the license today"""
        try:
            LAST_CHECK_FILE.write_text(datetime.now().isoformat())
        except:
            pass

    def validate_key(self, key: str = None) -> dict:
        """
        Checks key with the server.
        Returns dict with 'success' (bool) and 'message' (str).
        """
        if not key:
            key = self.load_key()
            
        if not key:
            return {"success": False, "message": "No key found", "code": "no_key"}

        hwid = self.get_hwid()
        
        try:
            # 1. First, try to VALIDATE
            resp = requests.post(f"{SERVER_URL}/validate", json={"key": key, "hwid": hwid}, timeout=5)
            full_response = resp.json()
            
            # NEW: Validate Signature
            if not self.verify_signature(full_response):
                return {"success": False, "message": "Security Error: Server Signature Invalid!", "code": "security_error"}

            data = full_response.get("data", {})
            status = data.get("status")
            
            if status == "valid":
                self.save_key(key)
                return {"success": True, "message": "Valid", "expires": data.get("expires_at")}
                
            elif status == "unbound":
                # Key is new, let's try to ACTIVATE automatically
                return self.activate_key(key)
                
            elif status == "hwid_mismatch":
                 return {"success": False, "message": "Key is used on another PC!", "code": "hwid_error"}
                 
            elif status == "expired":
                 return {"success": False, "message": f"Expired at {data.get('expires_at')}", "code": "expired"}
                 
            else:
                 return {"success": False, "message": f"Invalid Key: {data.get('message')}", "code": "invalid"}

        except requests.exceptions.ConnectionError:
            return {"success": False, "message": "Server unavailable. Check internet.", "code": "connection_error"}
        except Exception as e:
             # In case of verification error, return generic error
            return {"success": False, "message": f"Error: {str(e)}", "code": "error"}

    def activate_key(self, key: str) -> dict:
        """
        Activates a new key for this HWID
        """
        hwid = self.get_hwid()
        try:
            resp = requests.post(f"{SERVER_URL}/activate", json={"key": key, "hwid": hwid}, timeout=5)
            full_response = resp.json()
            
            # NEW: Validate Signature
            if not self.verify_signature(full_response):
                return {"success": False, "message": "Security Error: Server Signature Invalid!", "code": "security_error"}

            data = full_response.get("data", {})
            
            if data.get("status") == "valid":
                 self.save_key(key)
                 return {"success": True, "message": "Activated Successfully", "expires": data.get("expires_at")}
            else:
                 return {"success": False, "message": data.get("message"), "code": "activation_failed"}
                 
        except Exception as e:
            return {"success": False, "message": str(e), "code": "error"}

# Singleton instance
license_manager = LicenseManager()

