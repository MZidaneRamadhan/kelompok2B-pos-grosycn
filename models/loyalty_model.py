# ─────────────────────────────────────────────────────────────────────────────
# models/loyalty_model.py
# Logika bisnis loyalty — semua data dari SQLite via MemberRepository.
# Tidak ada JSON, tidak ada file Path, tidak ada _load()/_save().
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime

from database import MemberRepository

# ── Konstanta ─────────────────────────────────────────────────────────────────

POINT_VALUE     = 100   # Nilai 1 poin dalam Rupiah
MAX_REDEEM_RATE = 0.20  # Maks 20% dari subtotal boleh dibayar pakai poin
POINT_EARN_RATE = 0.01  # 1% dari total belanja → dikonversi jadi poin

TIER_THRESHOLDS = {
    "Platinum": 750_000,
    "Gold":     250_000,
    "Silver":   100_000,
    "Bronze":   0,
}


# ── Tier ──────────────────────────────────────────────────────────────────────

def calculate_tier(spent: float) -> str:
    """Tentukan tier dari akumulasi total belanja."""
    if spent >= TIER_THRESHOLDS["Platinum"]: return "Platinum"
    if spent >= TIER_THRESHOLDS["Gold"]:     return "Gold"
    return "Silver" if spent >= TIER_THRESHOLDS["Silver"] else "Bronze"


# ── Poin ──────────────────────────────────────────────────────────────────────

def calculate_points_earned(total_belanja: float) -> int:
    """
    Hitung poin yang didapat dari transaksi.
    Rumus: 1% dari total belanja ÷ POINT_VALUE.
    Contoh: Rp 200.000 × 1% = Rp 2.000 → 2.000 ÷ 100 = 20 poin.
    """
    return int((total_belanja * POINT_EARN_RATE) / POINT_VALUE)


def calculate_max_redeem(subtotal: float, points_owned: int) -> dict:
    """
    Hitung batas maksimum penukaran poin untuk transaksi ini.
    Dibatasi oleh yang lebih kecil: 20% dari subtotal atau nilai semua poin.
    """
    max_from_rate   = subtotal * MAX_REDEEM_RATE
    max_from_points = points_owned * POINT_VALUE
    actual_discount = min(max_from_rate, max_from_points)
    actual_points   = int(actual_discount / POINT_VALUE)
    return {
        "max_points_usable":  actual_points,
        "max_discount_value": actual_points * POINT_VALUE,
        "point_value":        POINT_VALUE,
        "max_redeem_rate":    MAX_REDEEM_RATE,
    }


def apply_point_discount(subtotal: float, points_to_redeem: int, points_owned: int) -> dict:
    """
    Validasi dan hitung diskon dari penukaran poin.

    Returns dict:
        valid           : bool
        error           : str  (kosong jika valid)
        discount_amount : float
        points_used     : int
        final_subtotal  : float
    """
    if points_to_redeem <= 0:
        return {"valid": True, "error": "",
                "discount_amount": 0.0, "points_used": 0, "final_subtotal": subtotal}

    if points_to_redeem > points_owned:
        return {"valid": False,
                "error": f"Poin tidak cukup! Sisa poin: {points_owned}",
                "discount_amount": 0.0, "points_used": 0, "final_subtotal": subtotal}

    limit = calculate_max_redeem(subtotal, points_owned)
    if points_to_redeem > limit["max_points_usable"]:
        return {
            "valid": False,
            "error": (
                f"Maks poin yang bisa ditukar: {limit['max_points_usable']} poin "
                f"(= Rp{limit['max_discount_value']:,.0f}, batas 20% subtotal)"
            ),
            "discount_amount": 0.0, "points_used": 0, "final_subtotal": subtotal,
        }

    discount = points_to_redeem * POINT_VALUE
    return {
        "valid": True, "error": "",
        "discount_amount": float(discount),
        "points_used":     points_to_redeem,
        "final_subtotal":  subtotal - discount,
    }


# ── CRUD — semua via MemberRepository ────────────────────────────────────────

def create_member(name: str, email: str, phone: str) -> int:
    """[CREATE] Daftarkan member baru ke SQLite. Kembalikan ID integer."""
    return MemberRepository.tambah({
        "member_name": name,
        "email":       email,
        "phone":       phone,
        "total_point": 0,
    })


def get_member(member_id: int) -> dict:
    """[READ] Ambil data satu member berdasarkan ID integer."""
    row = MemberRepository.get_by_id(member_id)
    return _row_to_dict(row) if row else {}


def get_all_members() -> list[dict]:
    """[READ] Ambil semua member, diurutkan by nama."""
    rows = MemberRepository.get_all()
    return [_row_to_dict(r) for r in rows]


def find_member_by_contact(identifier: str) -> dict:
    """[READ] Cari member aktif berdasarkan No. HP atau email."""
    identifier = identifier.strip()
    row = MemberRepository.get_by_phone(identifier) or MemberRepository.get_by_email(identifier)
    return _row_to_dict(row) if row else {}


def update_member(member_id: int, name: str, email: str, phone: str) -> bool:
    """[UPDATE] Perbarui data kontak member."""
    MemberRepository.update(member_id, {
        "member_name": name,
        "email":       email,
        "phone":       phone,
    })
    return True


def update_loyalty_stats(
    member_id: int,
    points_added: int,
    points_used: int,
    spent_added: float,
    new_tier: str,          # Disimpan jika kolom tier tersedia
) -> bool:
    """
    [UPDATE] Dipanggil setelah transaksi COMPLETED.
    Net poin = earned - redeemed. Akumulasi spent juga diupdate.
    """
    net_points = points_added - points_used
    MemberRepository.update_point(member_id, net_points)
    MemberRepository.update_spent(member_id, spent_added)
    return True


def deduct_points(member_id: int, points_used: int) -> bool:
    """[UPDATE] Kurangi poin saat redeem hadiah langsung (bukan lewat transaksi)."""
    MemberRepository.update_point(member_id, -abs(points_used))
    return True


def delete_member(member_id: int) -> bool:
    """[DELETE] Hapus member dari database (hard delete)."""
    MemberRepository.hapus(member_id)
    return True


# ── Helper internal ───────────────────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    """
    Konversi sqlite3.Row → dict dengan key seragam yang dipakai di seluruh UI.
    Memetakan nama kolom SQLite ke nama yang dipakai di pos.py & loyalty.py.
    """
    d = dict(row)
    return {
        "id":     d.get("id"),
        "name":   d.get("member_name", ""),
        "email":  d.get("email", ""),
        "phone":  d.get("phone", ""),
        "tier":   d.get("tier", "Bronze"),
        "points": d.get("total_point", 0),
        "spent":  d.get("spent", 0.0),
        "visits": d.get("visits", 0),
        # Alias tambahan agar kompatibel dengan loyalty.py lama
        "member_name": d.get("member_name", ""),
        "total_point": d.get("total_point", 0),
    }