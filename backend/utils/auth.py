"""
Authentication and security utilities
"""

import os
import jwt
from functools import wraps
from flask import request, jsonify, current_app
from cryptography.fernet import Fernet
import base64

def auth_required(f):
    """Decorator for routes requiring authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({'error': 'Authorization header required'}), 401

        try:
            token = auth_header.split(' ')[1]  # Bearer <token>
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = payload['user_id']
        except (IndexError, jwt.InvalidTokenError):
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)
    return decorated

def validate_api_credentials(api_key, api_secret):
    """Validate Binance API credentials format"""
    if not api_key or not api_secret:
        return False

    # Basic format validation
    if len(api_key) != 64 or len(api_secret) != 64:
        return False

    # Check if they contain only valid characters
    valid_chars = set('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')

    if not set(api_key).issubset(valid_chars) or not set(api_secret).issubset(valid_chars):
        return False

    return True

class CredentialManager:
    """Secure credential encryption/decryption"""

    def __init__(self):
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            # Generate a key if not provided (for development only)
            key = Fernet.generate_key()
            os.environ['ENCRYPTION_KEY'] = base64.urlsafe_b64encode(key).decode()

        if isinstance(key, str):
            key = base64.urlsafe_b64decode(key.encode())

        self.cipher = Fernet(key)

    def encrypt_credential(self, credential: str) -> str:
        """Encrypt a credential"""
        return self.cipher.encrypt(credential.encode()).decode()

    def decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt a credential"""
        return self.cipher.decrypt(encrypted_credential.encode()).decode()
