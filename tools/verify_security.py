import sys
import os
import json
import base64
from datetime import datetime, timezone, timedelta
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.license import license_manager

def test_security():
    print("=== SECURITY VERIFICATION TEST ===")
    
    # 1. Load Real Private Key (to simulate VALID server)
    try:
        with open("keys/private.pem", "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        print("✅ Private Key loaded for simulation")
    except Exception as e:
        print(f"❌ Failed to load private key: {e}")
        return

    # Helper to sign
    def sign_mock(data, ts, key=private_key):
        payload = data.copy()
        payload["timestamp"] = ts
        match_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        sig = key.sign(
            match_json.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return base64.b64encode(sig).decode()

    # --- TEST CASES ---

    # Case 1: Valid Response
    print("\n[TEST 1] Valid Response")
    ts = datetime.now(timezone.utc).timestamp()
    data = {"status": "valid", "expires_at": "2030-01-01T00:00:00"}
    sig = sign_mock(data, ts)
    
    response = {"data": data, "timestamp": ts, "signature": sig}
    result = license_manager.verify_signature(response)
    if result:
        print("✅ PASS: Valid signature accepted")
    else:
        print("❌ FAIL: Valid signature rejected")

    # Case 2: Tampered Data (Server Emulation Attack)
    print("\n[TEST 2] Tampered Data (Server Emulation)")
    # Attacker tries to change 'invalid' to 'valid' but cannot sign it
    fake_data = {"status": "valid", "expires_at": "2099-01-01"} 
    # Attacker uses OLD signature or Random signature
    response = {"data": fake_data, "timestamp": ts, "signature": sig} # Sig matches OLD data, not NEW
    
    result = license_manager.verify_signature(response)
    if not result:
        print("✅ PASS: Tampered data rejected")
    else:
        print("❌ FAIL: Tampered data accepted! (CRITICAL)")

    # Case 3: Replay Attack (Old Timestamp)
    print("\n[TEST 3] Replay Attack (Old Timestamp)")
    old_ts = (datetime.now(timezone.utc) - timedelta(minutes=20)).timestamp()
    # Signature is VALID for this data/time, but time is too old
    old_sig = sign_mock(data, old_ts)
    
    response = {"data": data, "timestamp": old_ts, "signature": old_sig}
    result = license_manager.verify_signature(response)
    if not result:
        print("✅ PASS: Expired replay rejected")
    else:
        print("❌ FAIL: Old timestamp accepted!")
        
    # Case 4: Fake Key Attack
    print("\n[TEST 4] Fake Key Signing")
    # Attacker generates THEIR OWN keypair
    fake_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    fake_sig = sign_mock(data, ts, key=fake_key)
    
    response = {"data": data, "timestamp": ts, "signature": fake_sig}
    result = license_manager.verify_signature(response)
    if not result:
        print("✅ PASS: Signature from unknown key rejected")
    else:
        print("❌ FAIL: Fake key accepted! (CRITICAL)")

if __name__ == "__main__":
    test_security()
