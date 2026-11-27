import hashlib
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "after" / "app"))
import main  # noqa: E402

SALT = os.urandom(16)
os.environ["PASSWORD_SALT"] = SALT.hex()
os.environ["PASSWORD_HASH"] = hashlib.scrypt(b"correct horse", salt=SALT, n=2**14, r=8, p=1).hex()
client = TestClient(main.app)


def test_user_id_must_be_an_integer():
    assert client.get("/user/1").json() == {"id": 1, "name": "Alice"}
    assert client.get("/user/abc").status_code == 422


def test_login_accepts_only_the_right_password():
    assert client.post("/login", json={"username": "a", "password": "correct horse"}).status_code == 200
    assert client.post("/login", json={"username": "a", "password": "secret"}).status_code == 401


def test_login_rejects_unknown_fields():
    r = client.post("/login", json={"username": "a", "password": "correct horse", "role": "admin"})
    assert r.status_code == 422


def test_login_fails_closed_without_secret(monkeypatch):
    monkeypatch.delenv("PASSWORD_HASH")
    assert client.post("/login", json={"username": "a", "password": "correct horse"}).status_code == 401
