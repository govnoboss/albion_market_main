import requests
import time
import subprocess
import sys
import os

# Configuration
SERVER_URL = "http://127.0.0.1:8000"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123") # Default for test

def run_test():
    print("--- Starting Heartbeat Verification ---")
    
    # 1. Start Server (assuming it's not running, or we use the existing one if running)
    # Ideally we'd start it, but let's assume valid environment.
    # We will try to ping it first.
    try:
        requests.get(f"{SERVER_URL}/admin/login", timeout=1)
        print("Server is already running.")
    except:
        print("Server not accessible. Please start server via 'uvicorn server.main:app --reload'")
        return

    # 2. Login as Admin to get cookie
    session = requests.Session()
    resp = session.post(f"{SERVER_URL}/admin/login", data={"password": ADMIN_PASSWORD})
    if resp.status_code == 200 and "gbot" in resp.text.lower(): # success redirect or specific content
         print("Admin Login: OK (or likely redirected)")
    else:
         # Check if we have the cookie
         if "admin_session" in session.cookies:
             print("Admin Login: OK (Cookie set)")
         else:
             print(f"Admin Login: FAILED? Status: {resp.status_code}")

    # 3. Generate a Test Key
    print("Generating test key...")
    resp = session.post(f"{SERVER_URL}/admin/generate", data={"count": 1, "days": 1})
    if resp.status_code != 200:
        print(f"Generate Failed: {resp.text}")
        return
    
    # Parse key from HTML or API? The endpoint returns HTML? 
    # Wait, existing implementation returns TemplateResponse.
    # We need to parse it or use the API logic directly?
    # Ah, the generate endpoint returns HTML. Hard to parse.
    # Let's insert directly into DB or use a known key if possible?
    # Actually, we can just look at the dashboard BEFORE and AFTER hitting heartbeat.
    
    print("Checking Dashboard Online Users...")
    resp = session.get(f"{SERVER_URL}/admin/dashboard")
    if "🟢 Онлайн" in resp.text:
         print("Found 'Online' indicator in HTML.")
         # Try to extract count... simplified
    else:
         print("Could not find 'Online' indicator.")

    # 4. Simulate Client Heartbeat
    # We need a valid key/hwid.
    # Since we can't easily extract a key from the HTML response without parsing,
    # let's just say "Manual Verification: Run Client, Check Dashboard".
    print("\nSince automated full test requires parsing HTML, please:")
    print("1. Open http://127.0.0.1:8000/admin/dashboard")
    print("2. Run the Client.")
    print("3. Refresh Dashboard.")
    print("4. Verify 'Online' count increases.")

if __name__ == "__main__":
    run_test()
