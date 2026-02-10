import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def generate_keys():
    print("Generating 2048-bit RSA Key Pair...")
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Serialize private key
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Serialize public key
    public_key = private_key.public_key()
    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Ensure output dir exists
    os.makedirs("keys", exist_ok=True)

    # Save files
    with open("keys/private.pem", "wb") as f:
        f.write(pem_private)
    
    with open("keys/public.pem", "wb") as f:
        f.write(pem_public)

    print("\nSUCCESS! Keys generated in 'keys/' directory.")
    
    # --- AUTOMATICALLY UPDATE CLIENT CODE ---
    try:
        license_file = "src/core/license.py"
        if os.path.exists(license_file):
            print(f"Updating {license_file}...")
            with open(license_file, "r", encoding="utf-8") as f:
                content = f.read()

            import re
            # Regex to find the PUBLIC_KEY_PEM block
            pattern = re.compile(r'PUBLIC_KEY_PEM\s*=\s*b"""-----BEGIN PUBLIC KEY-----.*?-----END PUBLIC KEY-----"""', re.DOTALL)
            
            new_block = f'PUBLIC_KEY_PEM = b"""{pem_public.decode().strip()}"""'
            
            if pattern.search(content):
                new_content = pattern.sub(new_block, content)
                with open(license_file, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"✅ {license_file} updated successfully!")
            else:
                print(f"⚠️ Could not find PUBLIC_KEY_PEM in {license_file}. Please update manually.")
        else:
             print(f"⚠️ {license_file} not found. Skipping auto-update.")
             
    except Exception as e:
        print(f"❌ Failed to update client code: {e}")

    print("-" * 50)
    print("1. SERVER: Content of 'keys/private.pem' -> env variable LICENSE_PRIVATE_KEY")
    print("2. CLIENT: Public key already updated in src/core/license.py")
    print("-" * 50)

if __name__ == "__main__":
    generate_keys()
