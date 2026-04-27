import json
import uuid
from pathlib import Path

DB_PATH = Path("data/users.json")

def _load() -> list[dict]:
    """Baca semua data dari file JSON."""
    if not DB_PATH.exists():
        return []
    with open(DB_PATH, "r") as f:
        return json.load(f)

def _save(data: list[dict]) -> None:
    """Tulis semua data ke file JSON."""
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── CRUD — dipanggil oleh Controller, bukan View ──

def create_user(name: str, email: str, password: str, role_id: int) -> str:
    """[CREATE] Membuat akun pengguna baru, kembalikan User ID."""
    users = _load()
    user_id = f"USR-{str(uuid.uuid4())[:8].upper()}"
    users.append({
        "id":       user_id,
        "name":     name,
        "email":    email,
        "password": password,   # sudah di-hash oleh Controller sebelum sampai sini
        "role_id":  role_id,
        "is_active": True,
    })
    _save(users)
    return user_id              # -> str


def get_user(user_id: str) -> dict:
    """[READ] Ambil data user berdasarkan ID."""
    users = _load()
    for u in users:
        if u["id"] == user_id:
            return u            # -> dict
    return {}                   # kosong jika tidak ditemukan


def get_all_users() -> list[dict]:
    """[READ] Ambil semua data user."""
    return _load()              # -> list[dict]


def update_user(user_id: str, name: str, email: str, role_id: int) -> bool:
    """[UPDATE] Perbarui data user."""
    users = _load()
    for u in users:             # mutable dict — langsung modifikasi
        if u["id"] == user_id:
            u["name"]    = name
            u["email"]   = email
            u["role_id"] = role_id
            _save(users)
            return True         # -> bool
    return False


def update_password(user_id: str, hashed_new: str) -> bool:
    """[UPDATE] Ganti password (menerima hash, bukan plain text)."""
    users = _load()
    for u in users:
        if u["id"] == user_id:
            u["password"] = hashed_new
            _save(users)
            return True
    return False


def delete_user(user_id: str) -> bool:
    """[DELETE] Nonaktifkan user (soft delete — data tidak benar-benar dihapus)."""
    users = _load()
    for u in users:
        if u["id"] == user_id:
            u["is_active"] = False  # soft delete, bukan hapus dari list
            _save(users)
            return True
    return False