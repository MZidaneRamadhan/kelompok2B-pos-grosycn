import json
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/members.json")

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

# ── CRUD ──

def create_member(name: str, email: str, phone: str) -> str:
    """[CREATE] Simpan pelanggan baru dengan stats awal (0)."""
    members = _load()
    member_id = f"MBR-{str(uuid.uuid4())[:6].upper()}"
    
    members.append({
        "id": member_id,
        "name": name,
        "email": email,
        "phone": phone,
        "tier": "Bronze",       # Level awal default
        "points": 0,            # Poin awal
        "spent": 0.0,           # Total belanja
        "visits": 0,            # Jumlah transaksi/kunjungan
        "join": datetime.now().strftime('%Y-%m-%d'),
        "is_active": True       # Untuk soft-delete
    })
    
    _save(members)
    return member_id

def get_member(member_id: str) -> dict:
    """[READ] Ambil data satu pelanggan."""
    for m in _load():
        if m["id"] == member_id:
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
            m["name"] = name
            m["email"] = email
            m["phone"] = phone
            _save(members)
            return True
    return False

def update_loyalty_stats(member_id: str, points_added: int, spent_added: float, new_tier: str) -> bool:
    """[UPDATE] Menambah poin, belanja, kunjungan, dan update tier."""
    members = _load()
    for m in members:
        if m["id"] == member_id:
            m["points"] += points_added
            m["spent"] += spent_added
            m["visits"] += 1
            m["tier"] = new_tier
            _save(members)
            return True
    return False

def deduct_points(member_id: str, points_used: int) -> bool:
    """[UPDATE] Mengurangi poin saat klaim hadiah (Redeem)."""
    members = _load()
    for m in members:
        if m["id"] == member_id:
            m["points"] -= points_used
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