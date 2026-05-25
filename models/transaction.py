"""
transaction.py  (dulunya barang_sync.py)
Semua operasi CRUD produk & kategori langsung ke SQLite.
Tidak ada lagi cache JSON — database_barang.json dihapus dari alur ini.
"""

from database import (
    get_connection,
    ProductRepository,
    CategoryProductRepository,
)


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
    """[CREATE] Simpan produk baru ke SQLite. Kembalikan id produk baru."""
    return ProductRepository.tambah({
        "product_name":  product_name,
        "sell_price":    sell_price,
        "buy_price":     buy_price,
        "category_id":   category_id,
        "stock":         stock,
        "stock_storage": stock_storage,
        "description":   description,
    })


def get_produk(product_id: int) -> dict | None:
    """[READ] Ambil satu produk berdasarkan ID. Kembalikan dict atau None."""
    row = ProductRepository.get_by_id(product_id)
    return dict(row) if row else None


def get_semua_produk() -> list[dict]:
    """[READ] Ambil semua produk dari SQLite (join kategori)."""
    return [dict(r) for r in ProductRepository.get_all()]


def get_produk_by_kategori(category_id: int) -> list[dict]:
    """[READ] Ambil produk berdasarkan kategori."""
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
    """[UPDATE] Perbarui data produk di SQLite. Kembalikan True jika berhasil."""
    if not ProductRepository.get_by_id(product_id):
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
    return True


def hapus_produk(product_id: int) -> bool:
    """[DELETE] Hapus produk dari SQLite. Kembalikan True jika berhasil."""
    if not ProductRepository.get_by_id(product_id):
        return False
    ProductRepository.hapus(product_id)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# CRUD KATEGORI
# ─────────────────────────────────────────────────────────────────────────────

def tambah_kategori(category: str) -> int:
    """[CREATE] Simpan kategori baru ke SQLite. Kembalikan id kategori baru."""
    return CategoryProductRepository.tambah(category)


def get_semua_kategori() -> list[dict]:
    """[READ] Ambil semua kategori dari SQLite."""
    return [dict(r) for r in CategoryProductRepository.get_all()]


def update_kategori(cat_id: int, new_name: str) -> bool:
    """[UPDATE] Ubah nama kategori di SQLite. Kembalikan True jika berhasil."""
    if not CategoryProductRepository.get_by_id(cat_id):
        return False
    return CategoryProductRepository.update(cat_id, new_name)


def hapus_kategori(cat_id: int) -> bool:
    """
    [DELETE] Hapus kategori dari SQLite.
    Pastikan tidak ada produk aktif di kategori ini sebelum memanggil fungsi ini.
    """
    if not CategoryProductRepository.get_by_id(cat_id):
        return False
    CategoryProductRepository.hapus(cat_id)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# STOK
# ─────────────────────────────────────────────────────────────────────────────

def kurangi_stok(product_id: int, qty: int) -> bool:
    """
    [UPDATE STOK] Kurangi stok produk di SQLite setelah transaksi.
    Kembalikan False jika stok tidak cukup atau produk tidak ditemukan.
    """
    row = ProductRepository.get_by_id(product_id)
    if not row or row["stock"] < qty:
        return False
    ProductRepository.update_stock(product_id, qty)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — dipanggil dari kasir.py (backward-compat)
# ─────────────────────────────────────────────────────────────────────────────

def _update_cache_single(product_id: int) -> None:
    """
    Dulu dipakai untuk update cache JSON.
    Sekarang no-op — data langsung dibaca dari SQLite, tidak ada cache.
    Dipertahankan agar import di kasir.py tidak error.
    """
    pass