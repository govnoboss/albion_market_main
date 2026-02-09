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
    print("-" * 50)
    print("1. SERVER: Content of 'keys/private.pem' -> env variable LICENSE_PRIVATE_KEY")
    print("2. CLIENT: Content of 'keys/public.pem' -> src/core/license.py (PUBLIC_KEY_PEM)")
    print("-" * 50)

if __name__ == "__main__":
    generate_keys()
