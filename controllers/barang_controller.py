"""
controllers/barang_controller.py
CRUD untuk Category dan Product, serta manajemen stok.
Menggunakan SQLite via database.get_connection().
"""

import logging
from database import get_connection
from models.barang_sync import (
    delete_json_product,
    sync_json_category,
    sync_json_from_db,
    update_json_product,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Layanan Kategori (CRUD Category)
# ──────────────────────────────────────────────────────────────────────────────

def create_category(category_name: str) -> int:
    """[CREATE] Menambahkan category baru, mengembalikan Category ID."""
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO category_product (category) VALUES (?)",
                (category_name,),
            )
            return cur.lastrowid
    except Exception as e:
        logger.error(f"Error creating category '{category_name}': {e}")
        return 0


def get_category(category_id: int) -> dict | None:
    """[READ] Menampilkan detail category berdasarkan Category ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM category_product WHERE id = ?", (category_id,)
        ).fetchone()
        return dict(row) if row else None


def get_all_categories() -> list[dict]:
    """[READ] Menampilkan semua category."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM category_product ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_category(category_id: int, new_category_name: str) -> bool:
    """[UPDATE] Mengubah nama category. Mengembalikan True jika berhasil."""
    old_category = get_category(category_id)
    old_name = old_category["category"] if old_category else ""

    try:
        with get_connection() as conn:
            cur = conn.execute(
                "UPDATE category_product SET category = ? WHERE id = ?",
                (new_category_name, category_id),
            )
            success = cur.rowcount > 0
            if success:
                logger.info(f"Category {category_id} updated to '{new_category_name}'")
                if old_name and old_name != new_category_name:
                    sync_json_category(old_name, new_category_name)
            else:
                logger.warning(f"Category {category_id} not found for update")
            return success
    except Exception as e:
        logger.error(f"Error updating category {category_id} to '{new_category_name}': {e}")
        return False


def delete_category(category_id: int) -> bool:
    """[DELETE] Menghapus category dari sistem."""
    old_category = get_category(category_id)
    old_name = old_category["category"] if old_category else ""

    try:
        with get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM category_product WHERE id = ?", (category_id,)
            )
            success = cur.rowcount > 0
            if success:
                logger.info(f"Category {category_id} deleted")
                if old_name:
                    sync_json_category(old_name, "Uncategorized")
            else:
                logger.warning(f"Category {category_id} not found for deletion")
            return success
    except Exception as e:
        logger.error(f"Error deleting category {category_id}: {e}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Layanan Informasi Produk (CRUD Product)
# ──────────────────────────────────────────────────────────────────────────────

def create_product(
    product_name: str,
    sell_price: float,
    buy_price: float,
    category_id: int,
    stock: int,
    stock_storage: int,
    description: str,
) -> int:
    """[CREATE] Mendaftarkan product baru, mengembalikan Product ID."""
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO product
               (product_name, sell_price, buy_price,
                category_id, stock, stock_storage, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (product_name, sell_price, buy_price,
             category_id, stock, stock_storage, description),
        )
        product_id = cur.lastrowid

    update_json_product(product_id)
    return product_id


def get_product(product_id: int) -> dict | None:
    """[READ] Mengambil detail product berdasarkan Product ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM product WHERE id = ?", (product_id,) 
        ).fetchone()
        return dict(row) if row else None


def get_all_products() -> list[dict]:
    """[READ] Menampilkan semua product beserta nama category-nya."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT p.*, c.category AS category_name
               FROM product p
               LEFT JOIN category_product c ON p.category_id = c.id
               ORDER BY p.id ASC"""
        ).fetchall()
        return [dict(r) for r in rows]


def update_product(
    product_id: int,
    product_name: str,
    sell_price: float,
    buy_price: float,
    category_id: int,
    stock: int,
    stock_storage: int,
    description: str,
) -> bool:
    """[UPDATE] Memperbarui seluruh data product termasuk stok."""
    with get_connection() as conn:
        cur = conn.execute(
            """UPDATE product
               SET product_name=?, sell_price=?, buy_price=?,
                   category_id=?, stock=?, stock_storage=?, description=?
               WHERE id=?""",
            (product_name, sell_price, buy_price,
             category_id, stock, stock_storage, description, product_id),
        )
        success = cur.rowcount > 0

    if success:
        update_json_product(product_id)
    return success


def delete_product(product_id: int) -> bool:
    """[DELETE] Menghapus product dari katalog secara permanen."""
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM product WHERE id = ?", (product_id,)
        )
        success = cur.rowcount > 0

    if success:
        delete_json_product(product_id)
    return success


# ──────────────────────────────────────────────────────────────────────────────
# Layanan Manajemen Stok
# ──────────────────────────────────────────────────────────────────────────────

# Kolom yang valid — mencegah SQL injection dari parameter location
_VALID_LOCATION_COL = {"toko": "stock", "gudang": "stock_storage"}


def add_stock(product_id: int, quantity: int, location: str) -> int:
    """
    Menambah stok di lokasi tertentu ('toko' atau 'gudang').
    Mengembalikan total stok (toko + gudang) setelah penambahan, atau -1 jika gagal.
    """
    col = _VALID_LOCATION_COL.get(location.lower())
    if col is None:
        raise ValueError(f"Lokasi tidak valid: '{location}'. Gunakan 'toko' atau 'gudang'.")

    with get_connection() as conn:
        affected = conn.execute(
            f"UPDATE product SET {col} = {col} + ? WHERE id = ?",
            (quantity, product_id),
        ).rowcount

        if affected == 0:
            return -1  # product_id tidak ditemukan

        row = conn.execute(
            "SELECT stock, stock_storage FROM product WHERE id = ?",
            (product_id,),
        ).fetchone()

    update_json_product(product_id)
    return (row["stock"] + row["stock_storage"]) if row else -1


def deduct_stock(product_id: int, quantity: int, location: str) -> bool:
    """
    Mengurangi stok di lokasi tertentu ('toko' atau 'gudang').
    Mengembalikan False jika stok tidak mencukupi atau product tidak ditemukan.
    """
    col = _VALID_LOCATION_COL.get(location.lower())
    if col is None:
        raise ValueError(f"Lokasi tidak valid: '{location}'. Gunakan 'toko' atau 'gudang'.")

    with get_connection() as conn:
        row = conn.execute(
            f"SELECT {col} FROM product WHERE id = ?", (product_id,)
        ).fetchone()

        if not row or row[0] < quantity:
            return False

        conn.execute(
            f"UPDATE product SET {col} = {col} - ? WHERE id = ?",
            (quantity, product_id),
        )

    update_json_product(product_id)
    return True


def check_low_stock(threshold: int) -> list[dict]:
    """
    Mengembalikan daftar product (id + nama) yang stok tokonya di bawah threshold.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, product_name, stock FROM product WHERE stock <= ? ORDER BY id ASC",
            (threshold,),
        ).fetchall()
        return [dict(r) for r in rows]