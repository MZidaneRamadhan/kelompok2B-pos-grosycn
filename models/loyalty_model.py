import uuid
from datetime import datetime
from pathlib import Path

from database import MemberRepository

DB_PATH = Path("data/members.json")
member_repo = MemberRepository()
# ── Tier thresholds (total spent) ──────────────────────────────────────────────
TIER_THRESHOLDS = {
    "Platinum": 750_000,
    "Gold":     250_000,
    "Silver":   100_000,
    "Bronze":   0,
}

# Maksimal poin yang bisa ditukar per transaksi (dalam rupiah diskon)
# 1 poin = Rp 100 diskon
POINT_VALUE      = 100        # Rp per 1 poin
MAX_REDEEM_RATE  = 0.20       # Maksimal 20% dari subtotal boleh dibayar pakai poin
POINT_EARN_RATE  = 0.01       # 1% dari total belanja → poin (1% belanja = poin, 1 poin = Rp 100)


def _load() -> list[dict]:
    """Baca semua data member dari file JSON."""
    if not DB_PATH.exists():
        return []
    with open(DB_PATH, "r") as f:
        return json.load(f)


def _save(data: list[dict]) -> None:
    """Tulis semua data member ke file JSON."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── Tier helpers ───────────────────────────────────────────────────────────────

def calculate_tier(total_spent: float) -> str:
    """Tentukan tier berdasarkan akumulasi total belanja."""
    if total_spent >= TIER_THRESHOLDS["Platinum"]: return "Platinum"
    if total_spent >= TIER_THRESHOLDS["Gold"]:     return "Gold"
    if total_spent >= TIER_THRESHOLDS["Silver"]:   return "Silver"
    return "Bronze"


def tier_next_threshold(tier: str) -> int | None:
    """Kembalikan threshold tier berikutnya, atau None jika sudah Platinum."""
    order = ["Bronze", "Silver", "Gold", "Platinum"]
    idx = order.index(tier)
    if idx + 1 >= len(order):
        return None
    next_tier = order[idx + 1]
    return TIER_THRESHOLDS[next_tier]


# ── Point helpers ──────────────────────────────────────────────────────────────

def calculate_points_earned(total_belanja: float) -> int:
    """
    Hitung poin yang didapat dari transaksi.
    Rumus: 1% dari total belanja, lalu dibagi POINT_VALUE.
    Contoh: Belanja Rp 200.000 → 1% = Rp 2.000 → 2.000 / 100 = 20 poin
    """
    return int((total_belanja * POINT_EARN_RATE) / POINT_VALUE)


def calculate_max_redeem(subtotal: float, points_owned: int) -> dict:
    """
    Hitung batas maksimum penukaran poin untuk diskon.

    Returns:
        max_points_usable  : Maks poin yang bisa ditukar (dibatasi 20% subtotal & stok poin)
        max_discount_value : Nilai diskon dalam rupiah
        point_value        : Nilai 1 poin dalam rupiah (konstan)
    """
    # Batas diskon: 20% dari subtotal
    max_discount_from_rate = subtotal * MAX_REDEEM_RATE

    # Nilai semua poin yang dimiliki member
    max_discount_from_points = points_owned * POINT_VALUE

    # Ambil yang lebih kecil
    actual_max_discount = min(max_discount_from_rate, max_discount_from_points)
    actual_max_points   = int(actual_max_discount / POINT_VALUE)

    return {
        "max_points_usable":  actual_max_points,
        "max_discount_value": actual_max_points * POINT_VALUE,
        "point_value":        POINT_VALUE,
        "max_redeem_rate":    MAX_REDEEM_RATE,
    }


def apply_point_discount(subtotal: float, points_to_redeem: int, points_owned: int) -> dict:
    """
    Validasi dan hitung diskon dari penukaran poin.

    Returns dict berisi:
        valid           : bool
        error           : str (jika tidak valid)
        discount_amount : float — nilai potongan harga
        points_used     : int   — poin yang benar-benar dipakai
        final_subtotal  : float — subtotal setelah diskon
    """
    if points_to_redeem <= 0:
        return {
            "valid": True, "error": "",
            "discount_amount": 0.0,
            "points_used": 0,
            "final_subtotal": subtotal,
        }

    if points_to_redeem > points_owned:
        return {"valid": False, "error": f"Poin tidak cukup! Sisa poin: {points_owned}",
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
        "points_used": points_to_redeem,
        "final_subtotal": subtotal - discount,
    }


# ── CRUD ───────────────────────────────────────────────────────────────────────

def create_member(name: str, email: str, phone: str) -> str:
    member_id = f"MBR-{str(uuid.uuid4())[:6].upper()}"
    members.append({
        "id":        member_id,
        "name":      name,
        "email":     email,
        "phone":     phone,
        "tier":      "Bronze",
        "points":    0,
        "spent":     0.0,
        "visits":    0,
        "join":      datetime.now().strftime('%Y-%m-%d'),
        "is_active": True,
    })
    _save(members)
    return member_id


def get_member(member_id: str) -> dict:
    """[READ] Ambil data satu pelanggan berdasarkan ID."""
    for m in _load():
        if m["id"] == member_id:
            return m
    return {}


def find_member_by_contact(identifier: str) -> dict:
    """[READ] Cari member berdasarkan nomor HP atau email."""
    identifier = identifier.strip()
    for m in _load():
        if m.get("is_active") and (m.get("phone") == identifier or m.get("email") == identifier):
            return m
    return {}


def get_all_members() -> list[dict]:
    """[READ] Ambil semua pelanggan."""
    return _load()


def update_member(member_id: str, name: str, email: str, phone: str) -> bool:
    """[UPDATE] Perbarui kontak pelanggan."""
    members = _load()
    for m in members:
        if m["id"] == member_id:
            m["name"]  = name
            m["email"] = email
            m["phone"] = phone
            _save(members)
            return True
    return False


def update_loyalty_stats(
    member_id: str,
    points_added: int,
    points_used: int,
    spent_added: float,
    new_tier: str,
) -> bool:
    """
    [UPDATE] Setelah transaksi selesai:
      - Tambah poin dari belanja
      - Kurangi poin yang ditukar (redeem)
      - Tambah akumulasi belanja & kunjungan
      - Update tier
    """
    members = _load()
    for m in members:
        if m["id"] == member_id:
            m["points"] = max(0, m["points"] + points_added - points_used)
            m["spent"]  += spent_added
            m["visits"] += 1
            m["tier"]   = new_tier
            _save(members)
            return True
    return False


def deduct_points(member_id: str, points_used: int) -> bool:
    """[UPDATE] Kurangi poin saat klaim hadiah (Redeem langsung)."""
    members = _load()
    for m in members:
        if m["id"] == member_id:
            m["points"] = max(0, m["points"] - points_used)
            _save(members)
            return True
    return False


def delete_member(member_id: str) -> bool:
    """[DELETE] Soft delete pelanggan."""
    members = _load()
    for m in members:
        if m["id"] == member_id:
            m["is_active"] = False
            _save(members)
            return True
    return False

def _row_to_dict(row) -> dict:
    """sqlite3.Row → dict dengan key seragam yang dipakai di UI."""
    d = dict(row)
    return {
        "id":     d.get("id"),
        "name":   d.get("member_name", ""),
        "email":  d.get("email", ""),
        "phone":  d.get("phone", ""),
        "tier":   d.get("tier", "Bronze"),
        "points": d.get("total_point", 0),
        "spent":  d.get("total_spent", 0.0),
        "visits": d.get("visits", 0),
    }
 