import requests
import json

URL = "https://gbot-license.fly.dev/api/v1/validate"

def test_prod():
    print(f"Testing {URL}...")
    try:
        # Send a dummy request
        resp = requests.post(URL, json={"key": "test-key-123", "hwid": "test-hwid"}, timeout=10)
        data = resp.json()
        
        print("\nResponse Status:", resp.status_code)
        print("Response Keys:", list(data.keys()))
        
        if "signature" in data:
            print("\n✅ SUCCESS: 'signature' field found in response!")
            print(f"Signature: {data['signature'][:30]}...")
            print(f"Timestamp: {data.get('timestamp')}")
        else:
            print("\n❌ FAILURE: 'signature' field MISSING! The server might be running old code.")
            print("Full Response:", data)
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    test_prod()
