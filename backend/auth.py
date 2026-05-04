"""Basic Authentication for order management system."""
import secrets
import os
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()


def _load_users() -> dict:
    """Load users from AUTH_USERS env var. Format: user1:pass1,user2:pass2"""
    users_str = os.getenv("AUTH_USERS", "")
    if users_str:
        users = {}
        for pair in users_str.split(","):
            if ":" in pair:
                username, password = pair.split(":", 1)
                users[username.strip()] = password.strip()
        return users
    return {}


USERS = _load_users()


def verify_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Verify any authenticated user. Returns username."""
    if not USERS:
        return "anonymous"

    correct_pw = USERS.get(credentials.username)
    if not correct_pw or not secrets.compare_digest(
        credentials.password.encode(), correct_pw.encode()
    ):
        raise HTTPException(
            status_code=401,
            detail="Sai tên đăng nhập hoặc mật khẩu",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Verify admin user only."""
    if not USERS:
        return "anonymous"

    username = verify_user(credentials)
    if username != "admin" and username != "anonymous":
        raise HTTPException(
            status_code=403,
            detail="Chỉ admin mới có quyền thực hiện thao tác này",
        )
    return username
