from datetime import datetime, timedelta
from typing import Optional
import hmac
import hashlib
import json
import base64
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from ..config.settings import JWT_SECRET, ADMIN_USERNAME, ADMIN_PASSWORD, JWT_EXPIRE_MINUTES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": int(expire.timestamp())})
    
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header, separators=(',', ':')).encode()).rstrip(b'=')
    payload_b64 = base64.urlsafe_b64encode(json.dumps(to_encode, separators=(',', ':')).encode()).rstrip(b'=')
    
    signature = hmac.new(
        JWT_SECRET.encode(),
        f"{header_b64.decode()}.{payload_b64.decode()}".encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=')
    
    return f"{header_b64.decode()}.{payload_b64.decode()}.{signature_b64.decode()}"

def verify_token(token: str) -> dict:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        
        header_b64, payload_b64, signature_b64 = parts
        
        expected_signature = hmac.new(
            JWT_SECRET.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()
        expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).rstrip(b'=')
        
        if not secrets.compare_digest(signature_b64, expected_signature_b64.decode()):
            raise ValueError("Invalid signature")
        
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + '==').decode())
        
        if "exp" in payload:
            if datetime.utcnow().timestamp() > payload["exp"]:
                raise ValueError("Token expired")
        
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )

def authenticate_admin(username: str, password: str) -> bool:
    return secrets.compare_digest(username, ADMIN_USERNAME) and secrets.compare_digest(password, ADMIN_PASSWORD)

async def get_current_admin(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    if not secrets.compare_digest(username, ADMIN_USERNAME):
        raise credentials_exception
    
    return {"username": username}
