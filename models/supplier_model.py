"""
models/supplier_model.py
Lapisan data untuk entitas Supplier.
Membaca dan menulis ke SQLite via database.py — bukan JSON lagi.

Semua fungsi mempertahankan signature yang sama dengan versi JSON
sehingga supplier_controller.py tidak perlu diubah sama sekali.
"""

import sqlite3
from database import get_connection


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — ubah sqlite3.Row → dict biasa agar controller bisa akses by key
# ─────────────────────────────────────────────────────────────────────────────

def _row_to_dict(row: sqlite3.Row | None) -> dict:
    """Konversi sqlite3.Row ke dict. Return {} jika None."""
    if row is None:
        return {}
    return dict(row)


def _rows_to_list(rows: list) -> list[dict]:
    """Konversi list sqlite3.Row ke list[dict]."""
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────────────────────────────────────

def create(
    supplier_name: str,
    email: str,
    phone: str,
    rating: float,
    source_data: str,
    category: str,          # disimpan ke kolom source_data jika kosong
    address: str,
    place_id: str = "",
    lat: float = 0.0,
    lng: float = 0.0,
    distance_m: int = 0,
) -> int:
    """
    Simpan satu supplier baru ke SQLite.
    Kembalikan id INTEGER (primary key) yang baru dibuat.

    Catatan: kolom 'category' di model lama tidak ada di skema DB.
    Nilainya digabung ke source_data agar tidak hilang, atau diabaikan
    jika source_data sudah diisi.
    """
    final_source = source_data or category or "manual"
    final_place  = place_id if place_id else None   # simpan NULL jika kosong

    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO supplier
                (supplier_name, email, number, rating, source_data,
                 place_id, lat, lng, alamat)
            VALUES
                (:supplier_name, :email, :number, :rating, :source_data,
                 :place_id, :lat, :lng, :alamat)
            """,
            {
                "supplier_name": supplier_name,
                "email":         email or None,
                "number":        phone or None,
                "rating":        float(rating),
                "source_data":   final_source,
                "place_id":      final_place,
                "lat":           float(lat),
                "lng":           float(lng),
                "alamat":        address or None,
            },
        )
        return cur.lastrowid                            # -> int


# ─────────────────────────────────────────────────────────────────────────────
# READ
# ─────────────────────────────────────────────────────────────────────────────

def get_by_id(supplier_id) -> dict:
    """
    Ambil satu supplier berdasarkan ID (int atau str).
    Return {} jika tidak ditemukan — sama seperti versi JSON.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM supplier WHERE id = ?", (int(supplier_id),)
        ).fetchone()
    return _row_to_dict(row)


def get_all() -> list[dict]:
    """
    Ambil semua supplier yang aktif (aktif = 1).
    Kolom dikembalikan dalam format dict agar controller tidak perlu diubah.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM supplier WHERE aktif = 1 ORDER BY supplier_name"
        ).fetchall()
    return _rows_to_list(rows)


def get_by_category(category: str) -> list[dict]:
    """Ambil supplier berdasarkan source_data (pengganti kolom category)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM supplier WHERE source_data = ? AND aktif = 1",
            (category,),
        ).fetchall()
    return _rows_to_list(rows)


def exists_by_place_id(place_id: str) -> bool:
    """Cek apakah supplier dengan place_id sudah ada di DB."""
    if not place_id:
        return False
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM supplier WHERE place_id = ?", (place_id,)
        ).fetchone()
    return row is not None


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE
# ─────────────────────────────────────────────────────────────────────────────

def update(
    supplier_id,
    supplier_name: str,
    email: str,
    phone: str,
    rating: float,
) -> bool:
    """
    Update data supplier. Kembalikan True jika baris ditemukan & diupdate.
    Signature sama dengan versi JSON.
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE supplier
            SET supplier_name   = :supplier_name,
                email           = :email,
                number          = :number,
                rating          = :rating,
                diperbarui_pada = datetime('now','localtime')
            WHERE id = :id AND aktif = 1
            """,
            {
                "id":            int(supplier_id),
                "supplier_name": supplier_name,
                "email":         email or None,
                "number":        phone or None,
                "rating":        float(rating),
            },
        )
        return cur.rowcount > 0                         # -> bool


def upsert_from_scraping(
    supplier_name: str,
    email: str,
    phone: str,
    rating: float,
    source_data: str,
    place_id: str,
    lat: float,
    lng: float,
    address: str,
) -> int:
    """
    Insert atau update supplier dari hasil Google Places scraping.
    Gunakan ON CONFLICT(place_id) agar tidak duplikat.
    Kembalikan id supplier.
    """
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO supplier
                (supplier_name, email, number, rating, source_data,
                 place_id, lat, lng, alamat)
            VALUES
                (:supplier_name, :email, :number, :rating, :source_data,
                 :place_id, :lat, :lng, :alamat)
            ON CONFLICT(place_id) DO UPDATE SET
                supplier_name   = excluded.supplier_name,
                rating          = excluded.rating,
                alamat          = excluded.alamat,
                lat             = excluded.lat,
                lng             = excluded.lng,
                diperbarui_pada = datetime('now','localtime')
            """,
            {
                "supplier_name": supplier_name,
                "email":         email or None,
                "number":        phone or None,
                "rating":        float(rating),
                "source_data":   source_data or "google_places",
                "place_id":      place_id,
                "lat":           float(lat),
                "lng":           float(lng),
                "alamat":        address or None,
            },
        )
        row = conn.execute(
            "SELECT id FROM supplier WHERE place_id = ?", (place_id,)
        ).fetchone()
        return row["id"]                                # -> int


# ─────────────────────────────────────────────────────────────────────────────
# DELETE
# ─────────────────────────────────────────────────────────────────────────────

def delete(supplier_id) -> bool:
    """
    Soft delete — set aktif = 0.
    Kembalikan True jika baris ditemukan. Sama seperti versi JSON.
    """
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE supplier SET aktif = 0 WHERE id = ?", (int(supplier_id),)
        )
        return cur.rowcount > 0                         # -> bool


def hard_delete(supplier_id) -> bool:
    """Hard delete — hapus baris dari DB sepenuhnya."""
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM supplier WHERE id = ?", (int(supplier_id),)
        )
        return cur.rowcount > 0                         # -> bool


# ─────────────────────────────────────────────────────────────────────────────
# SEARCH (tambahan — dipakai oleh controller search_suppliers_local)
# ─────────────────────────────────────────────────────────────────────────────

def search(keyword: str) -> list[dict]:
    """Cari supplier berdasarkan nama atau alamat (LIKE, case-insensitive)."""
    pola = f"%{keyword}%"
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM supplier
            WHERE aktif = 1
              AND (supplier_name LIKE ? OR alamat LIKE ? OR email LIKE ?)
            ORDER BY supplier_name
            """,
            (pola, pola, pola),
        ).fetchall()
    return _rows_to_list(rows)