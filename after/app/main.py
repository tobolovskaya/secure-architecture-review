"""Hardened version of before/app/main.py."""
import hashlib
import hmac
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title="user-api")


class UserOut(BaseModel):
    id: int
    name: str


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown fields are rejected, not ignored
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class LoginOut(BaseModel):
    status: str


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)


def verify_password(password: str) -> bool:
    """Compare against a salted scrypt hash from the environment, in constant time.

    PASSWORD_SALT and PASSWORD_HASH are hex strings injected at runtime (Kubernetes secret).
    """
    salt_hex, hash_hex = os.environ.get("PASSWORD_SALT"), os.environ.get("PASSWORD_HASH")
    if not salt_hex or not hash_hex:
        return False  # fail closed when the secret is missing
    return hmac.compare_digest(_hash(password, bytes.fromhex(salt_hex)), bytes.fromhex(hash_hex))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/user/{user_id}", response_model=UserOut)
def get_user(user_id: int) -> UserOut:
    return UserOut(id=user_id, name="Alice")


@app.post("/login", response_model=LoginOut)
def login(body: LoginIn) -> LoginOut:
    if not verify_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return LoginOut(status="ok")
