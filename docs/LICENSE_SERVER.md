# GBot License Server Documentation

## 1. Overview

The **License Server** is a standalone web application built with **FastAPI** that manages access control for the Albion Market Bot. It ensures that only authorized users with valid license keys can use the software.

*   **Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy (SQLite), Jinja2 (Admin UI).
*   **Deployment:** Docker container (optimized for Fly.io).
*   **Security:** Hardware ID (HWID) lock, Rate Limiting, Admin Authentication.

---

## 2. Architecture & Database

The server uses a lightweight **SQLite** database (`licenses.db`) to store key information. In production (Fly.io), this file is stored on a persistent volume mounted at `/data` to survive restarts.

### Database Schema (`licenses` table)
| Column | Type | Description |
| :--- | :--- | :--- |
| `key` | UUID (String) | Unique license key (Format: `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`). Primary Key. |
| `hwid` | String | Hardware ID hash of the bound machine. `NULL` if new/unbound. |
| `expires_at` | DateTime | Expiration timestamp. |
| `is_active` | Boolean | Global kill switch for the key (Default: `True`). |

### Security Features
1.  **HWID Locking:** Once a key is used on a machine (via `/activate`), it locks to that specific Hardware ID. It cannot be used on another PC unless reset by an Admin.
2.  **Rate Limiting:** `slowapi` limits requests by IP (e.g., 10 req/min for validation) to prevent brute-force attacks.
3.  **Admin Session:** The Admin Panel uses secure, HTTP-only cookies with IP + User-Agent binding to prevent session hijacking.

---

## 3. API Reference

### 1. Validate License
Checks if a key is valid and allowed to run on the current machine.

*   **Endpoint:** `POST /api/v1/validate`
*   **Rate Limit:** 10/minute
*   **Request JSON:**
    ```json
    {
      "key": "UUID-KEY-...",
      "hwid": "MACHINE-HASH-..."
    }
    ```
*   **Response JSON:**
    *   **Valid:** `{"status": "valid", "expires_at": "..."}`
    *   **New Key:** `{"status": "unbound", ...}` (Client should call `/activate`)
    *   **Error:** `{"status": "invalid" | "expired" | "hwid_mismatch", "message": "..."}`

### 2. Activate License
Binds a new (unbound) key to the current machine.

*   **Endpoint:** `POST /api/v1/activate`
*   **Rate Limit:** 10/minute
*   **Request JSON:** Same as Validate.
*   **Response JSON:**
    *   **Success:** `{"status": "valid", "message": "Activation successful"}`
    *   **Failure:** `{"status": "invalid", "message": "Key already bound to another PC"}`

### 3. Generate Keys (Admin API)
Programmatically generate keys. **Requires Admin Password.**

*   **Endpoint:** `POST /api/v1/admin/generate`
*   **Rate Limit:** 5/minute
*   **Request JSON:**
    ```json
    {
      "admin_password": "YOUR_SECRET_PASSWORD",
      "days": 30,
      "count": 1
    }
    ```

---

## 4. Admin Panel

A web-based interface for managing licenses.

*   **URL:** `/admin/` (Redirects to `/admin/login`)
*   **Credentials:** Requires the `ADMIN_PASSWORD` environment variable.

### Features
*   **Dashboard:** View stats (Total, Active, Expired, Unbound keys).
*   **License List:** 
    *   Search by Key or HWID.
    *   Filter by Status (Active, Expired, Unbound).
    *   **Actions:** 
        *   **Deactivate:** Temporarily ban a key.
        *   **Delete:** Permanently remove a key.
*   **Generator:** UI to create bulk keys (e.g., "Generate 10 keys for 30 days").

---

## 5. Deployment Guide (Fly.io)

The project is configured for one-command deployment on [Fly.io](https://fly.io/).

### Prerequisites
1.  Install `flyctl` command line tool.
2.  Login: `fly auth login`.

### Initial Setup
1.  Navigate to `server/` directory.
2.  Initialize app (if not already):
    ```bash
    fly launch
    ```
    *   Follow prompts. **Do not** set up a Postgres/Redis database (we use SQLite).

3.  **Create Persistent Volume** (Critical for database storage):
    ```bash
    fly vol create gbot_data --size 1
    ```
    *   Size: 1GB is more than enough for SQLite.
    *   Region: Should match your app region (e.g., `fra` for Frankfurt).

### Deploy
```bash
fly deploy
```

### Updates
To update the server code:
1.  Make changes locally.
2.  Run `fly deploy`.
The database on `/data` will persist across deployments.

### Local Development
To run the server locally for testing:
1.  Install dependencies: `pip install -r requirements.txt`
2.  Set Admin Password:
    *   Windows (PowerShell): `$env:ADMIN_PASSWORD="admin"; uvicorn main:app --reload`
3.  Access at `http://127.0.0.1:8000/admin`

---

## 6. Security Analysis (Vulnerabilities)

This system provides **Basic Protection** suitable for preventing casual sharing (e.g., "copy-pasting" to a friend). It is **NOT** proof against skilled reverse engineering.

### Known Loopholes
1.  **Client-Side Patching:**
    *   The license check occurs in `src/ui/launcher.py`. A skilled user could modify the compiled bytecode (even with Nuitka) to bypass the `if not license.validate():` check, as the core methods in `Bot` classes do not re-verify the license.
    *   *Mitigation:* Use Nuitka with `--nofollow-imports` for core modules and `onefile` mode to make patching harder, though not impossible.

2.  **Server Emulation (DNS Spoofing):**
    *   The client trusts the response from `SERVER_URL`. A user could modify their `hosts` file to redirect `gbot-license.fly.dev` to `127.0.0.1` and run a local server that mimics the API and returns `{"status": "valid"}`.
    *   *Mitigation:* Implement **Response Signing**. The server should sign the JSON response with a private RSA key, and the client should verify it with a hardcoded public key.

3.  **Time Manipulation:**
    *   The `should_check_today()` logic relies on a local file (`.last_check`) and the system clock. A user could freeze their system time or manipulate the file to prevent re-validation.

---

## 7. Key Management & RSA Setup

To enable **Response Signing** (anti-tamper protection), you must generate an RSA Key Pair.

### Step 1: Generate Keys
Run the included helper script:
```bash
python tools/generate_keys.py
```
This will create two files in the `keys/` directory:
*   `private.pem` (KEEP SECRET! For Server)
*   `public.pem` (Public! For Client)

### Step 2: Configure Server (Fly.io)
The server needs the **Private Key** to sign responses.
1.  Open `keys/private.pem` and copy the **ENTIRE** content (including Header/Footer).
2.  Set it as a secret environment variable on Fly.io:
    ```bash
    fly secrets set LICENSE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
    ...your private key content...
    -----END PRIVATE KEY-----"
    ```
    *Tip: If using PowerShell, you might need to handle newlines carefully or use the web dashboard at fly.io.*

### Step 3: Configure Client
The client needs the **Public Key** to verify signatures.
1.  Open `keys/public.pem`.
2.  Copy the content.
3.  Open `src/core/license.py`.
4.  Update the `PUBLIC_KEY_PEM` constant at the top of the file:
    ```python
    PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
    ...your public key content...
    -----END PUBLIC KEY-----"""
    ```
5.  Recompile/Distribute your bot.
