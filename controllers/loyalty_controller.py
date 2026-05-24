from models import loyalty_model
from controllers.user_controller import requires_permission  # Add 'controllers.' here!

# --- LOGIKA BISNIS INTERNAL ---

def _calculate_tier(total_spent: float) -> str:
    """Menentukan level tier pelanggan berdasarkan total akumulasi belanja."""
    if total_spent >= 750000: return "Platinum" # Rp 10 Juta
    if total_spent >= 250000:  return "Gold"     # Rp 5 Juta
    if total_spent >= 100000:  return "Silver"   # Rp 1 Juta
    return "Bronze"                               # Default

# --- LAYANAN MEMBERSHIP (CRUD) ---

@requires_permission("royalti")
def create_member(auth_token: str, member_name: str, email: str, phone_number: str) -> str:
    """[CREATE] Mendaftarkan pelanggan setia baru dan mengembalikan Member ID."""
    if not member_name or not phone_number:
        raise ValueError("Nama dan Nomor HP wajib diisi!")
        
    # Validasi Nomor HP / Email Kembar
    all_members = loyalty_model.get_all_members()
    for m in all_members:
        if m["is_active"]:
            if m["phone"] == phone_number:
                raise ValueError("Nomor HP sudah terdaftar sebagai member!")
            if email and m["email"] == email:
                raise ValueError("Email sudah terdaftar sebagai member!")

    return loyalty_model.create_member(member_name, email, phone_number)

@requires_permission("royalti")
def get_member(auth_token: str, member_id: str) -> dict:
    """[READ] Menampilkan profil dan data kontak pelanggan berdasarkan Member ID."""
    member = loyalty_model.get_member(member_id)
    if not member or not member.get("is_active"):
        raise ValueError("Data pelanggan tidak ditemukan atau sudah dinonaktifkan")
    return member

@requires_permission("transaksi") 
def verify_member(auth_token: str, identifier: str) -> dict:
    if not identifier:
        raise ValueError("Masukkan Nomor HP atau Email member")
        
    all_members = loyalty_model.get_all_members()
    for m in all_members:
        # Gracefully handle whichever column name the DB uses
        is_active = m.get("is_active") or m.get("active") or m.get("status", 1)
        if is_active and (m.get("phone") == identifier or m.get("email") == identifier):
            return m
    if all_members:
        print("Member keys:", dict(all_members[0]).keys())
        
    raise ValueError("Pelanggan dengan kontak tersebut tidak ditemukan")

@requires_permission("royalti")
def update_member(auth_token: str, member_id: str, member_name: str, email: str, phone_number: str) -> bool:
    """[UPDATE] Memperbarui data kontak pelanggan setia."""
    if not member_name or not phone_number:
        raise ValueError("Nama dan Nomor HP tidak boleh kosong")
        
    # Validasi kembar (Abaikan jika itu nomor HP miliknya sendiri)
    all_members = loyalty_model.get_all_members()
    for m in all_members:
        if m["id"] != member_id and m["is_active"]:
            if m["phone"] == phone_number:
                raise ValueError("Nomor HP sudah dipakai pelanggan lain")
            if email and m["email"] == email:
                raise ValueError("Email sudah dipakai pelanggan lain")

    return loyalty_model.update_member(member_id, member_name, email, phone_number)

@requires_permission("royalti")
def delete_member(auth_token: str, member_id: str) -> bool:
    """[DELETE] Menghapus data keanggotaan pelanggan (Soft delete)."""
    if member := loyalty_model.get_member(member_id):
        return loyalty_model.delete_member(member_id)
    else:
        raise ValueError("Member tidak ditemukan")


# --- LAYANAN POIN & TRANSAKSI ---

@requires_permission("transaksi")
def add_points_from_transaction(auth_token: str, member_id: str, total_belanja: float) -> dict:
    """
    Dipanggil secara otomatis oleh modul Kasir setelah pembayaran COMPLETED.
    Menghitung poin yang didapat, menjumlah total belanja, dan mengupdate Tier.
    """
    member = loyalty_model.get_member(member_id)
    if not member or not member.get("is_active"):
        raise ValueError("Member tidak valid")
        
    # Logika Bisnis: 1 Poin per setiap Rp 10.000,- belanja
    poin_didapat = int(total_belanja // 1000)
    
    # Hitung Tier Baru
    akumulasi_belanja_baru = member["spent"] + total_belanja
    tier_baru = _calculate_tier(akumulasi_belanja_baru)
    
    # Simpan ke Model
    loyalty_model.update_loyalty_stats(member_id, poin_didapat, total_belanja, tier_baru)
    
    return {
        "pesan": f"Berhasil menambah {poin_didapat} poin!",
        "poin_tambahan": poin_didapat,
        "tier_terkini": tier_baru
    }

@requires_permission("royalti")
def redeem_reward(auth_token: str, member_id: str, reward_cost: int, reward_name: str) -> bool:
    """Mengurangi poin saat member menukar hadiah dari katalog."""
    member = loyalty_model.get_member(member_id)
    if not member or not member.get("is_active"):
        raise ValueError("Member tidak valid")
        
    if member["points"] < reward_cost:
        raise ValueError(f"Poin tidak cukup! Butuh {reward_cost} poin, sisa poin: {member['points']}")
        
    # Lakukan pemotongan poin
    print(f"[SISTEM] {member['name']} menukarkan hadiah: {reward_name}")
    return loyalty_model.deduct_points(member_id, reward_cost)