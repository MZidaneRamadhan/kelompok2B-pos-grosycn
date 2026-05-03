"""
controllers/barang_controller.py
CRUD untuk Category dan Product, serta manajemen stok.
Menggunakan SQLite via database.get_connection().
"""

import uuid
from database import get_connection

# --- Layanan Kategori (CRUD Category) ---

def create_category(category_name: str) -> int:
    """[CREATE] Menambahkan category baru, mengembalikan Category ID."""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO category_product (category) VALUES (?)",
            (category_name,)
        )
        return cur.lastrowid


def get_category(category_id: int) -> dict:
    """[READ] Menampilkan detail category berdasarkan Category ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM category_product WHERE id = ?", (category_id,)
        ).fetchone()
        return dict(row) if row else None


def get_all_categories() -> list:
    """[READ] Menampilkan semua category."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM category_product ORDER BY category"
        ).fetchall()
        return [dict(r) for r in rows]


def update_category(category_id: int, new_category_name: str) -> bool:
    """[UPDATE] Mengubah nama category."""
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE category_product SET category = ? WHERE id = ?",
            (new_category_name, category_id)
        )
        return cur.rowcount > 0


def delete_category(category_id: int) -> bool:
    """[DELETE] Menghapus category dari sistem."""
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM category_product WHERE id = ?", (category_id,)
        )
        return cur.rowcount > 0


# --- Layanan Informasi Produk (CRUD Product) ---

def create_product(product_name: str, sell_price: float, buy_price: float,
                   category_id: int, stock: int, stock_storage: int,
                   description: str) -> int:
    """[CREATE] Mendaftarkan product baru, mengembalikan Product ID."""
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO product
               (product_name, sell_price, buy_price,
                category_id, stock, stock_storage, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (product_name, sell_price, buy_price,
             category_id, stock, stock_storage, description)
        )
        return cur.lastrowid


def get_product(product_id: int) -> dict:
    """[READ] Mengambil detail product berdasarkan Product ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM product WHERE id = ?", (product_id,)
        ).fetchone()
        return dict(row) if row else None


def get_all_products() -> list:
    """[READ] Menampilkan semua product beserta nama category-nya."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT p.*, c.category AS category_name
               FROM product p
               LEFT JOIN category_product c ON p.category_id = c.id
               ORDER BY p.product_name"""
        ).fetchall()
        return [dict(r) for r in rows]


def update_product(product_id: int, product_name: str, sell_price: float,
                   buy_price: float, category_id: int,
                   description: str) -> bool:
    """[UPDATE] Memperbarui data product (tanpa mengubah stok)."""
    with get_connection() as conn:
        cur = conn.execute(
            """UPDATE product
               SET product_name=?, sell_price=?, buy_price=?,
                   category_id=?, description=?
               WHERE id=?""",
            (product_name, sell_price, buy_price,
             category_id, description, product_id)
        )
        return cur.rowcount > 0


def delete_product(product_id: int) -> bool:
    """[DELETE] Menghapus product dari katalog secara permanen."""
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM product WHERE id = ?", (product_id,)
        )
        return cur.rowcount > 0


# --- Layanan Manajemen Stok (Fisik) ---

def add_stock(product_id: int, quantity: int, location: str) -> int:
    """Menambah stok di lokasi tertentu (toko/gudang)."""
    col = "stock_storage" if location.lower() == "gudang" else "stock"
    with get_connection() as conn:
        conn.execute(
            f"UPDATE product SET {col} = {col} + ? WHERE id = ?",
            (quantity, product_id)
        )
        row = conn.execute(
            "SELECT stock, stock_storage FROM product WHERE id = ?",
            (product_id,)
        ).fetchone()
        return (row["stock"] + row["stock_storage"]) if row else -1


def deduct_stock(product_id: int, quantity: int, location: str) -> bool:
    """Mengurangi stok karena penjualan atau pemindahan."""
    col = "stock_storage" if location.lower() == "gudang" else "stock"
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT {col} FROM product WHERE id = ?", (product_id,)
        ).fetchone()
        if not row or row[0] < quantity:
            return False
        conn.execute(
            f"UPDATE product SET {col} = {col} - ? WHERE id = ?",
            (quantity, product_id)
        )
        return True


def check_low_stock(threshold: int) -> list:
    """Mengembalikan daftar Product ID yang stoknya di bawah threshold."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id FROM product WHERE stock <= ?", (threshold,)
        ).fetchall()
        return [r["id"] for r in rows]