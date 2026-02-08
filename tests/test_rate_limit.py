from unittest.mock import Mock
import sys
import os

# Add server directory to path so we can import main and it can import database
server_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'server')
sys.path.insert(0, server_dir)

# Set dummy env var for main.py check
os.environ["ADMIN_PASSWORD"] = "test_password"

from main import get_real_ip

def test_get_real_ip_with_fly_header():
    mock_request = Mock()
    mock_request.headers = {"fly-client-ip": "100.0.0.1", "other": "value"}
    mock_request.client.host = "10.0.0.2"
    
    ip = get_real_ip(mock_request)
    print(f"Test with Fly header: Expected '100.0.0.1', Got '{ip}'")
    assert ip == "100.0.0.1"

def test_get_real_ip_without_header():
    mock_request = Mock()
    mock_request.headers = {}
    mock_request.client.host = "10.0.0.2"
    
    ip = get_real_ip(mock_request)
    print(f"Test without Fly header: Expected '10.0.0.2', Got '{ip}'")
    assert ip == "10.0.0.2"

def test_get_real_ip_no_client():
    mock_request = Mock()
    mock_request.headers = {}
    mock_request.client = None
    
    ip = get_real_ip(mock_request)
    print(f"Test with no client: Expected '127.0.0.1', Got '{ip}'")
    assert ip == "127.0.0.1"

if __name__ == "__main__":
    print("Running tests...")
    try:
        test_get_real_ip_with_fly_header()
        test_get_real_ip_without_header()
        test_get_real_ip_no_client()
        print("✅ All tests passed!")
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)
