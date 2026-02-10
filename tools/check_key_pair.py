from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def check_keys():
    try:
        # Load Private Key
        with open("keys/private.pem", "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)

        # Load Public Key
        with open("keys/public.pem", "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
            
        # Derive Public Key from Private Key
        derived_public_key = private_key.public_key()
        
        # Compare
        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        derived_bytes = derived_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        if pub_bytes == derived_bytes:
            print("✅ keys/private.pem MATCHES keys/public.pem")
        else:
            print("❌ KEY MISMATCH: keys/private.pem does NOT match keys/public.pem")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_keys()
