import hashlib
import secrets
import functools
import os
from models import user_model

# --- DEFINISI HAK AKSES (RBAC) ---
# 1 = Admin, 2 = Kasir, 3 = Stok Manager
ROLE_PERMISSIONS = {
    1: ["transaksi", "royalti", "storage", "supplier", "laporan", "manajemen_user"],
    2: ["transaksi", "royalti"],
    3: ["storage", "supplier"]
}

# ── FUNGSI INTERNAL & KEAMANAN ──

def _hash_password(plain: str) -> str:
    """Hash password sebelum disimpan."""
    return hashlib.sha256(plain.encode()).hexdigest()

def _is_email_taken(email: str) -> bool:
    """Cek apakah email sudah dipakai user lain."""
    users = user_model.get_all_users()
    return any(u["email"] == email for u in users)

def check_access(auth_token: str, feature: str) -> bool:
    """Mengecek apakah pengguna yang login berhak membuka fitur tertentu."""
    if not auth_token:
        raise ValueError("Akses ditolak: Harap login terlebih dahulu")

    user_id = user_model.get_user_id_by_token(auth_token)
    if not user_id:
        raise ValueError("Akses ditolak: Sesi tidak valid atau sudah kadaluarsa")

    user = user_model.get_user(user_id)
    if not user or not user.get("is_active"):
        raise ValueError("Akses ditolak: Akun tidak ditemukan atau nonaktif")
    raw_role = user.get("role_id", 0)
    role_id = int(raw_role)
    allowed_features = ROLE_PERMISSIONS.get(role_id, [])

    if feature not in allowed_features:
        raise PermissionError(f"Akses ditolak: Role Anda tidak diizinkan membuka menu '{feature}'")

    return True

def requires_permission(feature: str):
    """Decorator untuk mengecek hak akses secara otomatis."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(auth_token, *args, **kwargs):
            check_access(auth_token, feature)
            return func(auth_token, *args, **kwargs)
        return wrapper
    return decorator


# ── FUNGSI AUTENTIKASI (YANG DIPANGGIL OLEH VIEW) ──

def login(email: str, password: str) -> str:
    """Verifikasi kredensial dan hasilkan auth token."""
    if not email or not password:
        raise ValueError("Email dan password tidak boleh kosong")

    user = user_model.get_user_by_email(email)
    if not user or not user.get("is_active"):
        raise ValueError("Email tidak terdaftar atau akun dinonaktifkan")

    if user["password"] != _hash_password(password):
        raise ValueError("Password salah")

    auth_token = secrets.token_hex(16)
    user_model.save_session(auth_token, user["id"])
    return auth_token

def logout(auth_token: str) -> bool:
    """Menghapus sesi pengguna."""
    if not auth_token:
        return False
    return user_model.delete_session(auth_token)

def get_allowed_features(auth_token: str) -> list:
    """Mengembalikan daftar fitur yang diizinkan untuk merender Menu UI."""
    if not auth_token: return []
    user_id = user_model.get_user_id_by_token(auth_token)
    if not user_id: return []
    user = user_model.get_user(user_id)
    if not user or not user.get("is_active"): return []
    role_id_raw = user.get("role_id", 0)
    role_id_int = int(role_id_raw)
    return ROLE_PERMISSIONS.get((role_id_int), [])


# ── FUNGSI MANAJEMEN USER (DILINDUNGI DECORATOR) ──

@requires_permission("manajemen_user")
def create_user(auth_token: str, name: str, email: str, password: str, role_id: int) -> str:
    """[CREATE] Validasi input lalu simpan (Hanya bisa dipanggil Admin)."""
    if not name or not email or not password:
        raise ValueError("Nama, email, dan password tidak boleh kosong")
    if "@" not in email:
        raise ValueError("Format email tidak valid")
    if len(password) < 8:
        raise ValueError("Password minimal 8 karakter")
    if _is_email_taken(email):
        raise ValueError("Email sudah digunakan")

    hashed = _hash_password(password)
    return user_model.create_user(name, email, hashed, role_id)

@requires_permission("manajemen_user")
def get_user(auth_token: str, user_id: str) -> dict:
    """[READ] Ambil data user, hapus field sensitif."""
    user = user_model.get_user(user_id)
    if not user:
        raise ValueError(f"User {user_id} tidak ditemukan")

    safe = user.copy()
    safe.pop("password", None)
    return safe

@requires_permission("manajemen_user")
def get_all_users(auth_token: str) -> list[dict]:
    """[READ] Ambil semua user aktif (Hanya bisa dipanggil Admin)."""
    users = user_model.get_all_users()
    return [
        {k: v for k, v in u.items() if k != "password"}
        for u in users if u.get("is_active")
    ]

@requires_permission("manajemen_user")
def update_user(auth_token: str, user_id: str, name: str, email: str, role_id: int) -> bool:
    """[UPDATE] Validasi lalu update data user."""
    if not name or not email:
        raise ValueError("Nama dan email tidak boleh kosong")

    existing = user_model.get_user(user_id)
    if not existing:
        raise ValueError("User tidak ditemukan")

    all_users = user_model.get_all_users()
    for u in all_users:
        if u["email"] == email and u["id"] != user_id:
            raise ValueError("Email sudah digunakan user lain")

    return user_model.update_user(user_id, name, email, role_id)

@requires_permission("manajemen_user")
def update_password(auth_token: str, user_id: str, old_password: str, new_password: str) -> bool:
    """[UPDATE] Verifikasi password lama sebelum ganti baru."""
    user = user_model.get_user(user_id)
    if not user:
        raise ValueError("User tidak ditemukan")

    if user["password"] != _hash_password(old_password):
        raise ValueError("Password lama tidak sesuai")
    if len(new_password) < 8:
        raise ValueError("Password baru minimal 8 karakter")

    hashed_new = _hash_password(new_password)
    return user_model.update_password(user_id, hashed_new)

@requires_permission("manajemen_user")
def delete_user(auth_token: str, user_id: str) -> bool:
    """[DELETE] Soft delete akun pengguna."""
    user = user_model.get_user(user_id)
    if not user:
        raise ValueError("User tidak ditemukan")

    return user_model.delete_user(user_id)

"""
UNTUK VIEW NANTI
import user_controller
# import modul lain yang mungkin dibuat temanmu

def routing_menu(auth_token, pilihan):
    if pilihan == "1":
        # GEMBOK DIPASANG DI SINI: Saat user mencoba BUKA MENU Transaksi
        try:
            user_controller.check_access(auth_token, "transaksi")
            
            # Jika lolos (tidak error), baru halaman transaksinya dibuka
            print("Membuka Halaman Kasir...")
            # modul_transaksi.buka_layar_kasir() 
            
        except Exception as e:
            # Jika gagal, tampilkan pesan error dari controllermu
            print(f"⛔ {e}")

    elif pilihan == "2":
        # GEMBOK: Saat user mencoba BUKA MENU Storage
        try:
            user_controller.check_access(auth_token, "storage")
            
            print("Membuka Halaman Gudang...")
            # modul_storage.buka_layar_gudang()
            
        except Exception as e:
            print(f"⛔ {e}")
"""