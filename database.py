import sqlite3
import os
import logging
from datetime import datetime
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
        
SCHEMA_SQL = """
-- ══════════════════════════════════════════
-- TABEL SUPPLIER / DISTRIBUTOR
-- ══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS supplier (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name            TEXT    NOT NULL,
    category        TEXT,
    alamat          TEXT,
    telepon         TEXT,
    email           TEXT,
    place_id        TEXT    UNIQUE,
    lat             REAL,
    lng             REAL,
    rating          REAL    DEFAULT 0,
    distance_m      REAL,
    catatan         TEXT,
    aktif           INTEGER DEFAULT 1,
    dibuat_pada     TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    diperbarui_pada TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
"""
SEED_KATEGORI = [
    ("Sembako",       "Bahan pokok kebutuhan sehari-hari"),
    ("Minyak Goreng", "Minyak goreng kemasan dan curah"),
    ("Minuman",       "Minuman kemasan, air mineral, dll"),
    ("Snack",         "Makanan ringan dan camilan kemasan"),
    ("Frozen Food",   "Produk makanan beku"),
]

def init_db() -> None:
    """Buat semua tabel, indeks, dan trigger. Isi data awal kategori."""
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        conn.executemany(
            "INSERT OR IGNORE INTO kategori (nama, deskripsi) VALUES (?, ?)",
            SEED_KATEGORI,
        )
    logger.info("✅ Database diinisialisasi: %s", DB_PATH)
    
class SupplierRepository:
    """CRUD untuk tabel supplier."""
 
    @staticmethod
    def get_all(aktif_only: bool = True) -> list:
        with get_connection() as conn:
            q = "SELECT * FROM supplier"
            if aktif_only:
                q += " WHERE aktif = 1"
            q += " ORDER BY nama"
            return conn.execute(q).fetchall()
 
    @staticmethod
    def get_by_id(supplier_id: int):
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM supplier WHERE id=?", (supplier_id,)
            ).fetchone()
 
    @staticmethod
    def upsert_dari_places(data: dict) -> int:
        """Insert atau update supplier dari hasil Google Places API."""
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO supplier
                   (nama, kategori, alamat, lat, lng, rating, total_reviews,
                    jarak_km, place_id)
                   VALUES (:nama, :kategori, :alamat, :lat, :lng, :rating,
                           :total_reviews, :jarak_km, :place_id)
                   ON CONFLICT(place_id) DO UPDATE SET
                       nama          = excluded.nama,
                       kategori      = excluded.kategori,
                       alamat        = excluded.alamat,
                       lat           = excluded.lat,
                       lng           = excluded.lng,
                       rating        = excluded.rating,
                       total_reviews = excluded.total_reviews,
                       jarak_km      = excluded.jarak_km,
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
                """INSERT INTO supplier
                   (nama, kategori, alamat, telepon, email, catatan)
                   VALUES (:nama, :kategori, :alamat, :telepon, :email, :catatan)""",
                data,
            )
            return cur.lastrowid
 
    @staticmethod
    def update(supplier_id: int, data: dict) -> None:
        data["id"] = supplier_id
        with get_connection() as conn:
            conn.execute(
                """UPDATE supplier SET
                   nama=:nama, kategori=:kategori, alamat=:alamat,
                   telepon=:telepon, email=:email, catatan=:catatan,
                   diperbarui_pada=datetime('now','localtime')
                   WHERE id=:id""",
                data,
            )
 
    @staticmethod
    def hapus(supplier_id: int, soft: bool = True) -> None:
        with get_connection() as conn:
            if soft:
                conn.execute(
                    "UPDATE supplier SET aktif=0 WHERE id=?", (supplier_id,)
                )
            else:
                conn.execute("DELETE FROM supplier WHERE id=?", (supplier_id,))