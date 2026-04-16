import base64
import os
import uuid
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# File to store encrypted keys
KEYS_FILE = ".keys.enc"

def _get_master_key():
    """Derive a stable master key from the hardware ID (MAC address)."""
    hw_id = str(uuid.getnode()).encode()
    # Use a fixed salt for stability across refreshes on the same machine
    salt = b'antigravity_salt_123' 
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(hw_id))
    return key

def save_keys_encrypted(owm_key: str, openai_key: str):
    """Encrypt and save API keys to a local file."""
    master_key = _get_master_key()
    f = Fernet(master_key)
    
    data = {
        "owm": owm_key,
        "openai": openai_key
    }
    
    encrypted_data = f.encrypt(json.dumps(data).encode())
    with open(KEYS_FILE, "wb") as file:
        file.write(encrypted_data)

def load_keys_encrypted():
    """Load and decrypt API keys from the local file."""
    if not os.path.exists(KEYS_FILE):
        return None
        
    try:
        master_key = _get_master_key()
        f = Fernet(master_key)
        
        with open(KEYS_FILE, "rb") as file:
            encrypted_data = file.read()
            
        decrypted_data = f.decrypt(encrypted_data).decode()
        return json.loads(decrypted_data)
    except Exception as e:
        print(f"Decryption error: {e}")
        return None

def delete_stored_keys():
    """Delete the encrypted keys file."""
    if os.path.exists(KEYS_FILE):
        os.remove(KEYS_FILE)
