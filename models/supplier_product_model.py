# ─────────────────────────────────────────────────────────────────────────────
# models/supplier_product_model.py
# ─────────────────────────────────────────────────────────────────────────────

from database import get_connection   # sesuaikan dengan helper DB proyekmu


# ── CREATE ────────────────────────────────────────────────────────────────────

def link(supplier_id: int, product_id: int) -> int | None:
    """
    Hubungkan satu supplier dengan satu product.
    Kembalikan id baris baru, atau None bila sudah ada (duplicate).
    """
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT id FROM supplier_product WHERE supplier_id=? AND product_id=?",
            (supplier_id, product_id),
        )
        if cur.fetchone():
            return None                         # sudah terhubung

        cur = conn.execute(
            """
            INSERT INTO supplier_product (supplier_id, product_id)
            VALUES (?, ?)
            """,
            (supplier_id, product_id),
        )
        conn.commit()
        return cur.lastrowid                    # -> int


# ── READ ──────────────────────────────────────────────────────────────────────

def get_suppliers_by_product(product_id: int) -> list[dict]:
    """
    Ambil semua supplier yang menyediakan product_id tertentu.
    Kembalikan list dict dengan detail supplier.
    """
    with get_connection() as conn:
        conn.row_factory = _row_factory
        cur = conn.execute(
            """
            SELECT
                sp.id           AS link_id,
                sp.supplied_date,
                s.id            AS supplier_id,
                s.supplier_name,
                s.email,
                s.number        AS phone,
                s.rating,
                s.alamat        AS address,
                s.source_data
            FROM supplier_product sp
            JOIN supplier s ON s.id = sp.supplier_id
            WHERE sp.product_id = ?
              AND s.aktif = 1
            ORDER BY s.rating DESC, s.supplier_name
            """,
            (product_id,),
        )
        return cur.fetchall()                   # -> list[dict]


def get_products_by_supplier(supplier_id: int) -> list[dict]:
    """
    Ambil semua product yang dipasok oleh supplier_id tertentu.
    """
    with get_connection() as conn:
        conn.row_factory = _row_factory
        cur = conn.execute(
            """
            SELECT
                sp.id           AS link_id,
                sp.supplied_date,
                p.id            AS product_id,
                p.product_name,
                p.sell_price,
                p.buy_price,
                p.stock,
                p.stock_storage
            FROM supplier_product sp
            JOIN product p ON p.id = sp.product_id
            WHERE sp.supplier_id = ?
            ORDER BY p.product_name
            """,
            (supplier_id,),
        )
        return cur.fetchall()                   # -> list[dict]


def exists(supplier_id: int, product_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT 1 FROM supplier_product WHERE supplier_id=? AND product_id=?",
            (supplier_id, product_id),
        )
        return cur.fetchone() is not None


# ── DELETE ────────────────────────────────────────────────────────────────────

def unlink(link_id: int) -> bool:
    """Hapus satu baris relasi berdasarkan primary key."""
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM supplier_product WHERE id=?",
            (link_id,),
        )
        conn.commit()
        return cur.rowcount > 0


def unlink_by_pair(supplier_id: int, product_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM supplier_product WHERE supplier_id=? AND product_id=?",
            (supplier_id, product_id),
        )
        conn.commit()
        return cur.rowcount > 0


# ── Helper ────────────────────────────────────────────────────────────────────

def _row_factory(cursor, row):
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))