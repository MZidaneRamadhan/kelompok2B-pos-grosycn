import hashlib
from models import user_model

def _hash_password(plain: str) -> str:
    """Hash password sebelum disimpan — logika bisnis ada di Controller."""
    return hashlib.sha256(plain.encode()).hexdigest()

def _is_email_taken(email: str) -> bool:
    """Cek apakah email sudah dipakai user lain."""
    users = user_model.get_all_users()
    return any(u["email"] == email for u in users)


# ── FUNGSI YANG DIPANGGIL OLEH VIEW ──

def create_user(name: str, email: str, password: str, role_id: int) -> str:
    """[CREATE] Validasi input lalu simpan ke Model."""
    # Validasi — tanggung jawab Controller
    if not name or not email or not password:
        raise ValueError("Nama, email, dan password tidak boleh kosong")
    if "@" not in email:
        raise ValueError("Format email tidak valid")
    if len(password) < 8:
        raise ValueError("Password minimal 8 karakter")
    if _is_email_taken(email):
        raise ValueError("Email sudah digunakan")

    # Proses — hash password sebelum kirim ke Model
    hashed = _hash_password(password)

    # Panggil Model — Controller tidak tahu detail JSON
    user_id = user_model.create_user(name, email, hashed, role_id)
    return user_id              # -> str, diteruskan ke View


def get_user(user_id: str) -> dict:
    """[READ] Ambil data user, hapus field sensitif sebelum kirim ke View."""
    user = user_model.get_user(user_id)
    if not user:
        raise ValueError(f"User {user_id} tidak ditemukan")

    # Jangan kirim password ke View — Controller yang menyaring
    safe = user.copy()
    safe.pop("password", None)
    return safe                 # -> dict (tanpa password)


def get_all_users() -> list[dict]:
    """[READ] Ambil semua user aktif untuk ditampilkan di tabel."""
    users = user_model.get_all_users()
    # Filter hanya yang aktif, hapus field sensitif
    return [
        {k: v for k, v in u.items() if k != "password"}
        for u in users if u.get("is_active")
    ]                           # -> list[dict]


def update_user(user_id: str, name: str, email: str, role_id: int) -> bool:
    """[UPDATE] Validasi lalu update data user."""
    if not name or not email:
        raise ValueError("Nama dan email tidak boleh kosong")

    existing = user_model.get_user(user_id)
    if not existing:
        raise ValueError("User tidak ditemukan")

    # Cek email bentrok dengan user LAIN
    all_users = user_model.get_all_users()
    for u in all_users:
        if u["email"] == email and u["id"] != user_id:
            raise ValueError("Email sudah digunakan user lain")

    return user_model.update_user(user_id, name, email, role_id)  # -> bool


def update_password(user_id: str, old_password: str, new_password: str) -> bool:
    """[UPDATE] Verifikasi password lama sebelum ganti baru."""
    user = user_model.get_user(user_id)
    if not user:
        raise ValueError("User tidak ditemukan")

    # Verifikasi password lama — logika bisnis di Controller
    if user["password"] != _hash_password(old_password):
        raise ValueError("Password lama tidak sesuai")
    if len(new_password) < 8:
        raise ValueError("Password baru minimal 8 karakter")

    hashed_new = _hash_password(new_password)
    return user_model.update_password(user_id, hashed_new)  # -> bool


def delete_user(user_id: str) -> bool:
    """[DELETE] Pastikan user ada sebelum dihapus."""
    user = user_model.get_user(user_id)
    if not user:
        raise ValueError("User tidak ditemukan")

    return user_model.delete_user(user_id)  # -> bool