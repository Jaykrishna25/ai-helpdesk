"""Auth: password hashing + JWT. Production: Amazon Cognito user pools + MFA."""
import datetime as dt
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .config import settings

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def hash_pw(p): return pwd.hash(p)
def verify_pw(p, h): return pwd.verify(p, h)

def make_token(sub, role, utype):
    exp = dt.datetime.utcnow() + dt.timedelta(minutes=settings.JWT_EXPIRE_MIN)
    return jwt.encode({"sub": sub, "role": role, "utype": utype, "exp": exp},
                      settings.JWT_SECRET, algorithm=settings.JWT_ALG)

def current_user(token: str = Depends(oauth2)):
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        return {"id": payload["sub"], "role": payload["role"], "utype": payload["utype"]}
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

def require_role(*roles):
    def dep(user=Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient privileges")
        return user
    return dep
