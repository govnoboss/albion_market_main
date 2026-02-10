import sys
from pathlib import Path
import os
import secrets
import jwt
from datetime import datetime, timedelta

# Add server directory to path
server_dir = Path(r"c:\Users\Student\Documents\GitHub\albion_market_main\server")
sys.path.append(str(server_dir))

# Mock environment variables
os.environ["ADMIN_PASSWORD"] = "testpassword123"
os.environ["LICENSE_PRIVATE_KEY"] = "MOCK_KEY" # We don't need real signing key for this test

# Import app components (AFTER setting env vars)
try:
    from main import create_session_token, verify_admin_session, JWT_SECRET, JWT_ALGORITHM
    from fastapi import Request
    from unittest.mock import MagicMock
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def test_jwt_flow():
    print("--- Testing JWT Flow ---")
    
    # 1. Create Token
    print("1. Creating Token...")
    token = create_session_token()
    assert token, "Token creation failed"
    print(f"   Token created: {token[:20]}...")

    # 2. Verify Token (Manual decode)
    print("2. Verifying Token manually...")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == "admin"
        print("   Token is valid and payload correct.")
    except Exception as e:
        print(f"   Verification failed: {e}")
        return False

    # 3. Verify using main.py function (Mock Request)
    print("3. Testing verify_admin_session()...")
    mock_request = MagicMock(spec=Request)
    mock_request.cookies = {"admin_session": token}
    
    is_valid = verify_admin_session(mock_request)
    if is_valid:
        print("   verify_admin_session returned TRUE (Success)")
    else:
        print("   verify_admin_session returned FALSE (Failure)")
        return False

    # 4. Test Expired Token
    print("4. Testing Expired Token...")
    expired_payload = {
        "sub": "admin",
        "exp": datetime.utcnow() - timedelta(minutes=1),
        "iat": datetime.utcnow() - timedelta(minutes=60)
    }
    expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    mock_request_expired = MagicMock(spec=Request)
    mock_request_expired.cookies = {"admin_session": expired_token}
    
    is_valid_expired = verify_admin_session(mock_request_expired)
    if not is_valid_expired:
        print("   verify_admin_session correctly rejected expired token (Success)")
    else:
        print("   verify_admin_session Accepted expired token (Failure)")
        return False

    return True

if __name__ == "__main__":
    if test_jwt_flow():
        print("\nALL TESTS PASSED")
    else:
        print("\nTESTS FAILED")
