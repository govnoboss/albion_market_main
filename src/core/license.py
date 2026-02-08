import subprocess
import hashlib
import requests
import json
import os
import sys
import base64
from pathlib import Path
from datetime import datetime, timedelta

# Production server URL
SERVER_URL = "https://gbot-license.fly.dev/api/v1"

# Secure storage location
APP_DATA_DIR = Path(os.getenv('LOCALAPPDATA', Path.home())) / '.gbot'
LICENSE_FILE = APP_DATA_DIR / 'license.dat'
HWID_FALLBACK_FILE = APP_DATA_DIR / '.hwid'
LAST_CHECK_FILE = APP_DATA_DIR / '.last_check'

class LicenseManager:
    def __init__(self):
        self.cached_key = None
        self.cached_status = False
        # Ensure app data directory exists
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

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
            data = resp.json()
            
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
            return {"success": False, "message": str(e), "code": "error"}

    def activate_key(self, key: str) -> dict:
        """
        Activates a new key for this HWID
        """
        hwid = self.get_hwid()
        try:
            resp = requests.post(f"{SERVER_URL}/activate", json={"key": key, "hwid": hwid}, timeout=5)
            data = resp.json()
            
            if data.get("status") == "valid":
                 self.save_key(key)
                 return {"success": True, "message": "Activated Successfully", "expires": data.get("expires_at")}
            else:
                 return {"success": False, "message": data.get("message"), "code": "activation_failed"}
                 
        except Exception as e:
            return {"success": False, "message": str(e), "code": "error"}

# Singleton instance
license_manager = LicenseManager()
