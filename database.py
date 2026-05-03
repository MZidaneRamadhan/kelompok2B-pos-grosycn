import sqlite3
import os
import logging
from contextlib import contextmanager
 
 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH  = os.path.join(DATA_DIR, "grosync.db")
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
 
@contextmanager
def get_connection():
    """Buka koneksi SQLite, commit otomatis, rollback jika error."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
 
 
# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────────────────────────────────────────
SCHEMA_SQL = """
-- ══════════════════════════════════════════
-- ROLE
-- ══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS role (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name   TEXT    NOT NULL UNIQUE
);
 
-- ══════════════════════════════════════════
-- USER
-- ══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS user (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    username    TEXT    NOT NULL UNIQUE,
    password    TEXT    NOT NULL,
    role_id     INTEGER NOT NULL,
    FOREIGN KEY (role_id) REFERENCES role(id)
);
 
-- ══════════════════════════════════════════
-- CATEGORY PRODUCT
-- ══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS category_product (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category    TEXT    NOT NULL UNIQUE
);
 
-- ══════════════════════════════════════════
-- PRODUCT
-- ══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS product (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name    TEXT    NOT NULL,
    sell_price      REAL    NOT NULL DEFAULT 0,
    buy_price       REAL    NOT NULL DEFAULT 0,
    category_id     INTEGER NOT NULL,
    stock           INTEGER NOT NULL DEFAULT 0,
    stock_storage   INTEGER NOT NULL DEFAULT 0,
    description     TEXT,
    FOREIGN KEY (category_id) REFERENCES category_product(id)
);
 
-- ══════════════════════════════════════════
-- MEMBER
-- ══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS member (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    member_name     TEXT    NOT NULL,
    email           TEXT,
    phone           TEXT,
    total_point     INTEGER NOT NULL DEFAULT 0
);
 
-- ══════════════════════════════════════════
-- TRANSACTION
-- ══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS "transaction" (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        TEXT    NOT NULL,          -- daily order ID, e.g. ORD-001
    order_date      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    customer_name   TEXT,
    user_id         INTEGER NOT NULL,
    total           REAL    NOT NULL DEFAULT 0,
    changes         REAL    NOT NULL DEFAULT 0,
    payment_method  TEXT    NOT NULL,          -- e.g. Cash, QRIS, Transfer
    is_member       INTEGER NOT NULL DEFAULT 0,-- 0 = false, 1 = true
    FOREIGN KEY (user_id) REFERENCES user(id)
);
 
-- ══════════════════════════════════════════
-- TRANSACTION ITEM
-- ══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS transaction_item (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id  INTEGER NOT NULL,
    product_id      INTEGER NOT NULL,
    product_name    TEXT    NOT NULL,
    price           REAL    NOT NULL DEFAULT 0,
    quantity        INTEGER NOT NULL DEFAULT 1,
    subtotal        REAL    NOT NULL DEFAULT 0,
    FOREIGN KEY (transaction_id) REFERENCES "transaction"(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id)     REFERENCES product(id)
);
 
-- ══════════════════════════════════════════
-- SUPPLIER
-- ══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS supplier (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name   TEXT    NOT NULL,
    email           TEXT,
    number          TEXT,
    rating          REAL    DEFAULT 0,
    source_data     TEXT,                      -- e.g. 'manual' | 'scraping' | 'google_places'
    -- kolom tambahan untuk kebutuhan scraping
    place_id        TEXT    UNIQUE,
    lat             REAL,
    lng             REAL,
    alamat          TEXT,
    aktif           INTEGER DEFAULT 1,
    dibuat_pada     TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    diperbarui_pada TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
 
-- ══════════════════════════════════════════
-- SUPPLIER PRODUCT
-- ══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS supplier_product (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    supplied_date   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    supplier_id     INTEGER NOT NULL,
    product_id      INTEGER NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES supplier(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id)  REFERENCES product(id)  ON DELETE CASCADE
);
 
-- ══════════════════════════════════════════
-- INDEXES
-- ══════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_product_category      ON product(category_id);
CREATE INDEX IF NOT EXISTS idx_transaction_user       ON "transaction"(user_id);
CREATE INDEX IF NOT EXISTS idx_transaction_date       ON "transaction"(order_date);
CREATE INDEX IF NOT EXISTS idx_trx_item_transaction   ON transaction_item(transaction_id);
CREATE INDEX IF NOT EXISTS idx_trx_item_product       ON transaction_item(product_id);
CREATE INDEX IF NOT EXISTS idx_supplier_product_supp  ON supplier_product(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supplier_product_prod  ON supplier_product(product_id);
"""
 
# ─────────────────────────────────────────────────────────────────────────────
# SEED DATA
# ─────────────────────────────────────────────────────────────────────────────
SEED_ROLES = [
    ("Admin",),
    ("Kasir",),
    ("Owner",),
]
 
SEED_CATEGORIES = [
    ("Sembako",),
    ("Minyak Goreng",),
    ("Minuman",),
    ("Snack",),
    ("Frozen Food",),
]
 
 
def init_db() -> None:
    """Buat semua tabel, indeks, dan isi seed data awal."""
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        conn.executemany(
            "INSERT OR IGNORE INTO role (role_name) VALUES (?)",
            SEED_ROLES,
        )
        conn.executemany(
            "INSERT OR IGNORE INTO category_product (category) VALUES (?)",
            SEED_CATEGORIES,
        )
    logger.info("✅ Database diinisialisasi: %s", DB_PATH)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# REPOSITORIES
# ─────────────────────────────────────────────────────────────────────────────
 
class RoleRepository:
    @staticmethod
    def get_all() -> list:
        with get_connection() as conn:
            return conn.execute("SELECT * FROM role ORDER BY id").fetchall()
 
    @staticmethod
    def get_by_id(role_id: int):
        with get_connection() as conn:
            return conn.execute("SELECT * FROM role WHERE id=?", (role_id,)).fetchone()
 
 
class UserRepository:
    @staticmethod
    def get_all() -> list:
        with get_connection() as conn:
            return conn.execute(
                "SELECT u.*, r.role_name FROM user u JOIN role r ON u.role_id = r.id"
            ).fetchall()
 
    @staticmethod
    def get_by_id(user_id: int):
        with get_connection() as conn:
            return conn.execute("SELECT * FROM user WHERE id=?", (user_id,)).fetchone()
 
    @staticmethod
    def get_by_username(username: str):
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM user WHERE username=?", (username,)
            ).fetchone()
 
    @staticmethod
    def tambah(data: dict) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO user (name, username, password, role_id) "
                "VALUES (:name, :username, :password, :role_id)",
                data,
            )
            return cur.lastrowid
 
    @staticmethod
    def update(user_id: int, data: dict) -> None:
        data["id"] = user_id
        with get_connection() as conn:
            conn.execute(
                "UPDATE user SET name=:name, username=:username, "
                "password=:password, role_id=:role_id WHERE id=:id",
                data,
            )
 
    @staticmethod
    def hapus(user_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM user WHERE id=?", (user_id,))
 
 
class CategoryProductRepository:
    @staticmethod
    def get_all() -> list:
        with get_connection() as conn:
            return conn.execute("SELECT * FROM category_product ORDER BY category").fetchall()
 
    @staticmethod
    def get_by_id(cat_id: int):
        with get_connection() as conn:
            return conn.execute("SELECT * FROM category_product WHERE id=?", (cat_id,)).fetchone()
 
    @staticmethod
    def tambah(category: str) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO category_product (category) VALUES (?)", (category,)
            )
            return cur.lastrowid
 
    @staticmethod
    def update(cat_id: int, category: str) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE category_product SET category=? WHERE id=?", (category, cat_id)
            )
 
    @staticmethod
    def hapus(cat_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM category_product WHERE id=?", (cat_id,))
 
 
class ProductRepository:
    @staticmethod
    def get_all() -> list:
        with get_connection() as conn:
            return conn.execute(
                "SELECT p.*, c.category FROM product p "
                "JOIN category_product c ON p.category_id = c.id "
                "ORDER BY p.product_name"
            ).fetchall()
 
    @staticmethod
    def get_by_id(product_id: int):
        with get_connection() as conn:
            return conn.execute(
                "SELECT p.*, c.category FROM product p "
                "JOIN category_product c ON p.category_id = c.id "
                "WHERE p.id=?", (product_id,)
            ).fetchone()
 
    @staticmethod
    def get_by_category(cat_id: int) -> list:
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM product WHERE category_id=? ORDER BY product_name", (cat_id,)
            ).fetchall()
 
    @staticmethod
    def tambah(data: dict) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO product "
                "(product_name, sell_price, buy_price, category_id, stock, stock_storage, description) "
                "VALUES (:product_name, :sell_price, :buy_price, :category_id, :stock, :stock_storage, :description)",
                data,
            )
            return cur.lastrowid
 
    @staticmethod
    def update(product_id: int, data: dict) -> None:
        data["id"] = product_id
        with get_connection() as conn:
            conn.execute(
                "UPDATE product SET product_name=:product_name, sell_price=:sell_price, "
                "buy_price=:buy_price, category_id=:category_id, stock=:stock, "
                "stock_storage=:stock_storage, description=:description WHERE id=:id",
                data,
            )
 
    @staticmethod
    def update_stock(product_id: int, qty_sold: int) -> None:
        """Kurangi stok setelah transaksi."""
        with get_connection() as conn:
            conn.execute(
                "UPDATE product SET stock = stock - ? WHERE id=?", (qty_sold, product_id)
            )
 
    @staticmethod
    def hapus(product_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM product WHERE id=?", (product_id,))
 
 
class MemberRepository:
    @staticmethod
    def get_all() -> list:
        with get_connection() as conn:
            return conn.execute("SELECT * FROM member ORDER BY member_name").fetchall()
 
    @staticmethod
    def get_by_id(member_id: int):
        with get_connection() as conn:
            return conn.execute("SELECT * FROM member WHERE id=?", (member_id,)).fetchone()
 
    @staticmethod
    def get_by_phone(phone: str):
        with get_connection() as conn:
            return conn.execute("SELECT * FROM member WHERE phone=?", (phone,)).fetchone()
 
    @staticmethod
    def tambah(data: dict) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO member (member_name, email, phone, total_point) "
                "VALUES (:member_name, :email, :phone, :total_point)",
                data,
            )
            return cur.lastrowid
 
    @staticmethod
    def update_point(member_id: int, tambah_poin: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE member SET total_point = total_point + ? WHERE id=?",
                (tambah_poin, member_id),
            )
 
    @staticmethod
    def update(member_id: int, data: dict) -> None:
        data["id"] = member_id
        with get_connection() as conn:
            conn.execute(
                "UPDATE member SET member_name=:member_name, email=:email, "
                "phone=:phone WHERE id=:id",
                data,
            )
 
    @staticmethod
    def hapus(member_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM member WHERE id=?", (member_id,))
 
 
class TransactionRepository:
    @staticmethod
    def get_all() -> list:
        with get_connection() as conn:
            return conn.execute(
                "SELECT t.*, u.name AS cashier FROM [transaction] t "
                "JOIN user u ON t.user_id = u.id ORDER BY t.order_date DESC"
            ).fetchall()
 
    @staticmethod
    def get_by_id(trx_id: int):
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM [transaction] WHERE id=?", (trx_id,)
            ).fetchone()
 
    @staticmethod
    def get_daily_count(date_str: str) -> int:
        """Hitung jumlah transaksi pada tanggal tertentu (untuk order_id harian)."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM [transaction] WHERE order_date LIKE ?",
                (f"{date_str}%",),
            ).fetchone()
            return row["cnt"] if row else 0
 
    @staticmethod
    def tambah(data: dict) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO [transaction] "
                "(order_id, order_date, customer_name, user_id, total, changes, payment_method, is_member) "
                "VALUES (:order_id, :order_date, :customer_name, :user_id, :total, :changes, :payment_method, :is_member)",
                data,
            )
            return cur.lastrowid
 
    @staticmethod
    def hapus(trx_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM [transaction] WHERE id=?", (trx_id,))
 
 
class TransactionItemRepository:
    @staticmethod
    def get_by_transaction(trx_id: int) -> list:
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM transaction_item WHERE transaction_id=?", (trx_id,)
            ).fetchall()
 
    @staticmethod
    def tambah_bulk(trx_id: int, items: list[dict]) -> None:
        """Simpan banyak item sekaligus. Tiap dict harus punya: product_id, product_name, price, quantity, subtotal."""
        rows = [
            (trx_id, i["product_id"], i["product_name"], i["price"], i["quantity"], i["subtotal"])
            for i in items
        ]
        with get_connection() as conn:
            conn.executemany(
                "INSERT INTO transaction_item "
                "(transaction_id, product_id, product_name, price, quantity, subtotal) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
 
 
class SupplierRepository:
    @staticmethod
    def get_all(aktif_only: bool = True) -> list:
        with get_connection() as conn:
            q = "SELECT * FROM supplier"
            if aktif_only:
                q += " WHERE aktif = 1"
            q += " ORDER BY supplier_name"
            return conn.execute(q).fetchall()
 
    @staticmethod
    def get_by_id(supplier_id: int):
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM supplier WHERE id=?", (supplier_id,)
            ).fetchone()
 
    @staticmethod
    def upsert_dari_scraping(data: dict) -> int:
        """Insert atau update supplier dari hasil scraping (Google Places / sumber lain)."""
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO supplier
                   (supplier_name, email, number, rating, source_data, place_id, lat, lng, alamat)
                   VALUES (:supplier_name, :email, :number, :rating, :source_data,
                           :place_id, :lat, :lng, :alamat)
                   ON CONFLICT(place_id) DO UPDATE SET
                       supplier_name   = excluded.supplier_name,
                       rating          = excluded.rating,
                       alamat          = excluded.alamat,
                       lat             = excluded.lat,
                       lng             = excluded.lng,
                       diperbarui_pada = datetime('now','localtime')""",
                data,
            )
            row = conn.execute(
                "SELECT id FROM supplier WHERE place_id=?", (data["place_id"],)
            ).fetchone()
            return row["id"]
 
    @staticmethod
    def tambah(data: dict) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO supplier (supplier_name, email, number, rating, source_data) "
                "VALUES (:supplier_name, :email, :number, :rating, :source_data)",
                data,
            )
            return cur.lastrowid
 
    @staticmethod
    def update(supplier_id: int, data: dict) -> None:
        data["id"] = supplier_id
        with get_connection() as conn:
            conn.execute(
                "UPDATE supplier SET supplier_name=:supplier_name, email=:email, "
                "number=:number, rating=:rating, source_data=:source_data, "
                "diperbarui_pada=datetime('now','localtime') WHERE id=:id",
                data,
            )
 
    @staticmethod
    def hapus(supplier_id: int, soft: bool = True) -> None:
        with get_connection() as conn:
            if soft:
                conn.execute("UPDATE supplier SET aktif=0 WHERE id=?", (supplier_id,))
            else:
                conn.execute("DELETE FROM supplier WHERE id=?", (supplier_id,))
 
 
class SupplierProductRepository:
    @staticmethod
    def get_by_supplier(supplier_id: int) -> list:
        with get_connection() as conn:
            return conn.execute(
                "SELECT sp.*, p.product_name FROM supplier_product sp "
                "JOIN product p ON sp.product_id = p.id "
                "WHERE sp.supplier_id=? ORDER BY sp.supplied_date DESC",
                (supplier_id,),
            ).fetchall()
 
    @staticmethod
    def get_by_product(product_id: int) -> list:
        with get_connection() as conn:
            return conn.execute(
                "SELECT sp.*, s.supplier_name FROM supplier_product sp "
                "JOIN supplier s ON sp.supplier_id = s.id "
                "WHERE sp.product_id=? ORDER BY sp.supplied_date DESC",
                (product_id,),
            ).fetchall()
 
    @staticmethod
    def tambah(data: dict) -> int:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO supplier_product (supplied_date, supplier_id, product_id) "
                "VALUES (:supplied_date, :supplier_id, :product_id)",
                data,
            )
            return cur.lastrowid
 
    @staticmethod
    def hapus(sp_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM supplier_product WHERE id=?", (sp_id,))
 
 
# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()