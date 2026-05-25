import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path("data/users.json")
SESSION_DB_PATH = Path("data/sessions.json") # Tambahan untuk Sesi Login

# ── FUNGSI INTERNAL UNTUK FILE JSON ──

def _load() -> list[dict]:
    """Baca semua data dari file JSON."""
    if not DB_PATH.exists():
        return []
    with open(DB_PATH, "r") as f:
        return json.load(f)

def _save(data: list[dict]) -> None:
    """Tulis semua data ke file JSON."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True) # Perbaikan bug folder belum ada
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=2)

def _load_sessions() -> dict:
    """Baca data sesi aktif dari file JSON."""
    if not SESSION_DB_PATH.exists():
        return {}
    with open(SESSION_DB_PATH, "r") as f:
        return json.load(f)

def _save_sessions(data: dict) -> None:
    """Tulis data sesi ke file JSON."""
    SESSION_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SESSION_DB_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── CRUD & GETTER — dipanggil oleh Controller, bukan View ──

def create_user(name: str, email: str, password: str, role_id: int) -> str:
    """[CREATE] Membuat akun pengguna baru, kembalikan User ID."""
    users = _load()
    user_id = f"USR-{str(uuid.uuid4())[:8].upper()}"
    users.append({
        "id":       user_id,
        "name":     name,
        "email":    email,
        "password": password,
        "role_id":  role_id,
        "is_active": True,
    })
    _save(users)
    return user_id

def get_user(user_id: str) -> dict:
    """[READ] Ambil data user berdasarkan ID."""
    users = _load()
    for u in users:
        if u["id"] == user_id:
            return u
    return {}

def get_user_by_email(email: str) -> dict:
    """[READ] Ambil data user berdasarkan Email untuk Login."""
    users = _load()
    for u in users:
        if u["email"] == email:
            return u
    return {}

def get_all_users() -> list[dict]:
    """[READ] Ambil semua data user."""
    return _load()

def update_user(user_id: str, name: str, email: str, role_id: int) -> bool:
    """[UPDATE] Perbarui data user."""
    users = _load()
    for u in users:
        if u["id"] == user_id:
            u["name"]    = name
            u["email"]   = email
            u["role_id"] = role_id
            _save(users)
            return True
    return False

def update_password(user_id: str, hashed_new: str) -> bool:
    """[UPDATE] Ganti password."""
    users = _load()
    for u in users:
        if u["id"] == user_id:
            u["password"] = hashed_new
            _save(users)
            return True
    return False

def delete_user(user_id: str) -> bool:
    """[DELETE] Nonaktifkan user (soft delete)."""
    users = _load()
    for u in users:
        if u["id"] == user_id:
            u["is_active"] = False
            _save(users)
            return True
    return False


# ── MANAJEMEN SESI (LOGIN/LOGOUT) ──

SESSION_EXPIRY_HOURS = 8  # Token kadaluarsa setelah 8 jam

def _purge_expired_sessions(sessions: dict) -> dict:
    """Hapus semua sesi yang sudah kadaluarsa."""
    now = datetime.now()
    valid = {}
    for token, data in sessions.items():
        if isinstance(data, dict):
            created_at_str = data.get("created_at", "")
            try:
                created_at = datetime.fromisoformat(created_at_str)
                if now - created_at < timedelta(hours=SESSION_EXPIRY_HOURS):
                    valid[token] = data
            except (ValueError, TypeError):
                pass  # Token format lama tanpa timestamp, buang
        # Token format lama (hanya string user_id) - buang
    return valid

def save_session(token: str, user_id: str) -> None:
    """[CREATE] Simpan token login."""
    sessions = _load_sessions()
    sessions = _purge_expired_sessions(sessions)
    sessions[token] = {
        "user_id": user_id,
        "created_at": datetime.now().isoformat()
    }
    _save_sessions(sessions)

def delete_session(token: str) -> bool:
    """[DELETE] Hapus token saat logout."""
    sessions = _load_sessions()
    if token in sessions:
        del sessions[token]
        _save_sessions(sessions)
        return True
    return False

def get_user_id_by_token(token: str) -> str:
    """[READ] Ambil User ID dari token. Kembalikan string kosong jika token tidak ada atau kadaluarsa."""
    sessions = _load_sessions()
    data = sessions.get(token)
    if data is None:
        return ""
    if isinstance(data, dict):
        created_at_str = data.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_at_str)
            if datetime.now() - created_at >= timedelta(hours=SESSION_EXPIRY_HOURS):
                return ""  # Token kadaluarsa
        except (ValueError, TypeError):
            return ""
        return data.get("user_id", "")
    # Format lama (string) - anggap tidak valid
    return ""