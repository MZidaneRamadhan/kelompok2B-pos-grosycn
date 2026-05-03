"""
models/supplier_model.py
Lapisan data untuk entitas Supplier.
Hanya tahu cara baca/tulis JSON — tidak ada logika bisnis di sini.
"""

import json
import uuid
import os
from config import SUPPLIER_FILE, DATA_DIR


def _ensure_file():
    """Pastikan file dan folder data sudah ada."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(SUPPLIER_FILE):
        with open(SUPPLIER_FILE, "w") as f:
            json.dump([], f)


def _load() -> list[dict]:
    _ensure_file()
    with open(SUPPLIER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: list[dict]) -> None:
    _ensure_file()
    with open(SUPPLIER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── CREATE ──────────────────────────────────────────────────

def create(supplier_name: str, email: str, phone: str,
           rating: float, source_data: str,
           category: str, address: str,
           place_id: str = "", lat: float = 0.0,
           lng: float = 0.0, distance_m: int = 0) -> str:
    """
    Simpan satu supplier baru ke JSON.
    Kembalikan supplier_id yang baru dibuat.
    """
    suppliers = _load()
    supplier_id = f"SUP-{str(uuid.uuid4())[:8].upper()}"
    suppliers.append({
        "id":           supplier_id,
        "supplierName": supplier_name,
        "email":        email,
        "phone":        phone,
        "rating":       rating,
        "sourceData":   source_data,
        "category":     category,
        "address":      address,
        "place_id":     place_id,
        "lat":          lat,
        "lng":          lng,
        "distance_m":   distance_m,
    })
    _save(suppliers)
    return supplier_id                  # -> str


# ── READ ────────────────────────────────────────────────────

def get_by_id(supplier_id: str) -> dict:
    """Ambil satu supplier berdasarkan ID."""
    for s in _load():
        if s["id"] == supplier_id:
            return s                    # -> dict
    return {}


def get_all() -> list[dict]:
    """Ambil semua supplier yang aktif."""
    return [s for s in _load() if s.get("is_active", True)]  # -> list[dict]


def get_by_category(category: str) -> list[dict]:
    """Ambil supplier berdasarkan kategori."""
    return [s for s in get_all() if s.get("category") == category]


def exists_by_place_id(place_id: str) -> bool:
    """Cek apakah supplier dengan place_id sudah tersimpan."""
    return any(s.get("place_id") == place_id for s in _load())


# ── UPDATE ──────────────────────────────────────────────────

def update(supplier_id: str, supplier_name: str, email: str,
           phone: str, rating: float) -> bool:
    """Update data supplier. Kembalikan True jika berhasil."""
    suppliers = _load()
    for s in suppliers:
        if s["id"] == supplier_id:
            s["supplierName"] = supplier_name
            s["email"]        = email
            s["phone"]        = phone
            s["rating"]       = rating
            _save(suppliers)
            return True                 # -> bool
    return False


# ── DELETE ──────────────────────────────────────────────────

def delete(supplier_id: str) -> bool:
    """Soft delete — tandai is_active = False."""
    suppliers = _load()
    for s in suppliers:
        if s["id"] == supplier_id:
            s["is_active"] = False
            _save(suppliers)
            return True                 # -> bool
    return False


def hard_delete(supplier_id: str) -> bool:
    """Hard delete — hapus dari JSON sepenuhnya."""
    suppliers = _load()
    filtered  = [s for s in suppliers if s["id"] != supplier_id]
    if len(filtered) == len(suppliers):
        return False
    _save(filtered)
    return True                         # -> bool
