"""
barang_sync.py
Semua operasi CRUD produk & kategori menggunakan SQLite (via ProductRepository
dan CategoryProductRepository dari database.py).

JSON (database_barang.json) hanya dipakai sebagai cache baca-cepat untuk
modul POS. Setiap kali data berubah di DB, cache JSON di-rebuild otomatis.
"""

import json
import os
from typing import Any

from database import (
    get_connection,
    ProductRepository,
    CategoryProductRepository,
)

# Path ke cache JSON produk (relatif dari root project)
ROOT_DIR    = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BARANG_FILE = os.path.join(ROOT_DIR, "database_barang.json")



# ─────────────────────────────────────────────────────────────────────────────
# KEY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _product_key(product_id: int) -> str:
    return f"PRD-{product_id}"


def _product_id_from_key(product_key: str) -> int | None:
    if isinstance(product_key, str) and product_key.startswith("PRD-"):
        try:
            return int(product_key.split("-", 1)[1])
        except ValueError:
            return None
    return None


# ─────────────────────────────────────────────────────────────────────────────
# JSON CACHE  (hanya untuk POS — jangan panggil langsung dari luar)
# ─────────────────────────────────────────────────────────────────────────────

def _load_json() -> dict[str, Any]:
    if not os.path.exists(BARANG_FILE):
        return {}
    with open(BARANG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(BARANG_FILE), exist_ok=True)
    with open(BARANG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def _row_to_cache(row: dict[str, Any]) -> dict[str, Any]:
    """Ubah baris SQLite → format cache JSON yang dipakai POS."""
    sell_price = float(row.get("sell_price", 0))
    return {
        "name":          row.get("product_name", row.get("name", "Unknown Product")),
        "sell_price":    sell_price,
        "buy_price":     float(row.get("buy_price", 0)),
        "stock":         int(row.get("stock", 0)),
        "stock_storage": int(row.get("stock_storage", 0)),
        "category":      row.get("category", "General") or "General",
        "sku":           row.get("sku", f"SKU-{row.get('id', '')}"),
        "brand":         row.get("brand", ""),
        "image":         row.get("image", "📦"),
        "low":           int(row.get("low", 5)),
        "description":   row.get("description", ""),
        "pricing":       row.get(
            "pricing",
            [{"unit": "piece", "price": sell_price, "qty": 1}],
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SYNC  — rebuild cache JSON dari seluruh isi tabel product
# ─────────────────────────────────────────────────────────────────────────────

def sync_json_from_db() -> dict[str, Any]:
    """
    Baca semua produk dari SQLite, tulis ulang cache JSON, dan kembalikan
    hasilnya sebagai dict.  Panggil ini sekali saat aplikasi pertama kali dibuka.
    """
    rows = ProductRepository.get_all()
    if not rows:
        return _load_json()     # kembalikan cache lama jika DB kosong

    data: dict[str, Any] = {}
    for row in rows:
        r = dict(row)
        data[_product_key(r["id"])] = _row_to_cache(r)

    _save_json(data)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# CRUD PRODUK
# ─────────────────────────────────────────────────────────────────────────────

def tambah_produk(
    product_name: str,
    sell_price: float,
    buy_price: float,
    category_id: int,
    stock: int,
    stock_storage: int,
    description: str = "",
) -> int:
    """
    [CREATE] Simpan produk baru ke SQLite.
    Cache JSON diperbarui otomatis.
    Kembalikan id produk baru.
    """
    new_id = ProductRepository.tambah({
        "product_name":  product_name,
        "sell_price":    sell_price,
        "buy_price":     buy_price,
        "category_id":   category_id,
        "stock":         stock,
        "stock_storage": stock_storage,
        "description":   description,
    })
    _update_cache_single(new_id)
    return new_id


def get_produk(product_id: int) -> dict | None:
    """
    [READ] Ambil satu produk berdasarkan ID dari SQLite.
    Kembalikan dict atau None jika tidak ditemukan.
    """
    row = ProductRepository.get_by_id(product_id)
    return dict(row) if row else None


def get_semua_produk() -> list[dict]:
    """
    [READ] Ambil semua produk dari SQLite (join kategori).
    Kembalikan list[dict].
    """
    return [dict(r) for r in ProductRepository.get_all()]


def get_produk_by_kategori(category_id: int) -> list[dict]:
    """
    [READ] Ambil produk berdasarkan kategori dari SQLite.
    """
    return [dict(r) for r in ProductRepository.get_by_category(category_id)]


def update_produk(
    product_id: int,
    product_name: str,
    sell_price: float,
    buy_price: float,
    category_id: int,
    stock: int,
    stock_storage: int,
    description: str = "",
) -> bool:
    """
    [UPDATE] Perbarui data produk di SQLite.
    Cache JSON diperbarui otomatis.
    Kembalikan True jika berhasil.
    """
    existing = ProductRepository.get_by_id(product_id)
    if not existing:
        return False

    ProductRepository.update(product_id, {
        "product_name":  product_name,
        "sell_price":    sell_price,
        "buy_price":     buy_price,
        "category_id":   category_id,
        "stock":         stock,
        "stock_storage": stock_storage,
        "description":   description,
    })
    _update_cache_single(product_id)
    return True


def hapus_produk(product_id: int) -> bool:
    """
    [DELETE] Hapus produk dari SQLite dan cache JSON.
    Kembalikan True jika baris ditemukan dan dihapus.
    """
    existing = ProductRepository.get_by_id(product_id)
    if not existing:
        return False

    ProductRepository.hapus(product_id)
    _delete_cache_single(product_id)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# CRUD KATEGORI
# ─────────────────────────────────────────────────────────────────────────────

def tambah_kategori(category: str) -> int:
    """
    [CREATE] Simpan kategori baru ke SQLite.
    Kembalikan id kategori baru.
    """
    return CategoryProductRepository.tambah(category)


def get_semua_kategori() -> list[dict]:
    """
    [READ] Ambil semua kategori dari SQLite.
    """
    return [dict(r) for r in CategoryProductRepository.get_all()]


def update_kategori(cat_id: int, new_name: str) -> bool:
    """
    [UPDATE] Ubah nama kategori di SQLite.
    Cache JSON diperbarui otomatis (ganti nama kategori di semua produk terkait).
    Kembalikan True jika baris ditemukan dan diperbarui.
    """
    old_row = CategoryProductRepository.get_by_id(cat_id)
    if not old_row:
        return False

    old_name = old_row["category"]
    result   = CategoryProductRepository.update(cat_id, new_name)
    if result:
        _sync_cache_category(old_name, new_name)
    return result


def hapus_kategori(cat_id: int) -> bool:
    """
    [DELETE] Hapus kategori dari SQLite.
    PERHATIAN: produk yang terhubung akan kehilangan kategori (FK constraint).
    Pastikan tidak ada produk aktif di kategori ini sebelum memanggil fungsi ini.
    Kembalikan True jika berhasil.
    """
    existing = CategoryProductRepository.get_by_id(cat_id)
    if not existing:
        return False

    CategoryProductRepository.hapus(cat_id)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# STOK
# ─────────────────────────────────────────────────────────────────────────────

def kurangi_stok(product_id: int, qty: int) -> bool:
    """
    [UPDATE STOK] Kurangi stok produk di SQLite setelah transaksi.
    Cache JSON diperbarui otomatis.
    Kembalikan False jika stok tidak cukup atau produk tidak ditemukan.
    """
    row = ProductRepository.get_by_id(product_id)
    if not row or row["stock"] < qty:
        return False

    ProductRepository.update_stock(product_id, qty)
    _update_cache_single(product_id)
    return True


def kurangi_stok_by_key(product_key: str, qty: int) -> bool:
    """
    Versi kurangi_stok yang menerima product_key (format "PRD-<id>").
    Dipakai oleh modul POS yang masih menggunakan key berbasis JSON.
    """
    product_id = _product_id_from_key(product_key)
    return False if product_id is None else kurangi_stok(product_id, qty)


# ─────────────────────────────────────────────────────────────────────────────
# CACHE HELPERS  (internal — tidak perlu dipanggil dari luar)
# ─────────────────────────────────────────────────────────────────────────────

def _update_cache_single(product_id: int) -> None:
    """Perbarui satu entri di cache JSON berdasarkan data terbaru di SQLite."""
    row = ProductRepository.get_by_id(product_id)
    if not row:
        return
    data = _load_json()
    data[_product_key(product_id)] = _row_to_cache(dict(row))
    _save_json(data)


def _delete_cache_single(product_id: int) -> None:
    """Hapus satu entri dari cache JSON."""
    data = _load_json()
    key  = _product_key(product_id)
    if key in data:
        del data[key]
        _save_json(data)


def _sync_cache_category(old_name: str, new_name: str) -> None:
    """Ganti nama kategori di semua entri cache JSON."""
    data    = _load_json()
    changed = False
    for product in data.values():
        if product.get("category") == old_name:
            product["category"] = new_name or "Uncategorized"
            changed = True
    if changed:
        _save_json(data)