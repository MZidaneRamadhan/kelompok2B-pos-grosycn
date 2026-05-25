"""
kasir.py
Semua operasi kasir (cart, pembayaran, transaksi) menggunakan SQLite.
Tidak ada lagi baca/tulis JSON untuk transaksi maupun stok produk.
"""

from datetime import datetime

from database import (
    get_connection,
    ProductRepository,
    TransactionRepository,
    TransactionItemRepository,
    MemberRepository,
    UserRepository,
)
from models.transaction import kurangi_stok

# ─────────────────────────────────────────────────────────────────────────────
# CART  (in-memory, per session)
# ─────────────────────────────────────────────────────────────────────────────
# Struktur: { "CART-<session_id>": [ {product_id, name, price, qty, subtotal}, ... ] }

_db_carts: dict[str, list[dict]] = {}


def _get_cart(session_id: str) -> list[dict]:
    cart_id = f"CART-{session_id}"
    return _db_carts.setdefault(cart_id, [])


def add_item_to_cart(session_id: str, product_id: int, quantity: int) -> str:
    """
    Tambah produk ke keranjang.
    product_id : INTEGER (id di tabel product)
    Kembalikan cart_id.
    """
    cart_id = f"CART-{session_id}"
    cart    = _db_carts.setdefault(cart_id, [])

    row = ProductRepository.get_by_id(product_id)
    if not row:
        print(f"Gagal: Produk ID {product_id} tidak ditemukan.")
        return cart_id

    product = dict(row)

    # Hitung qty yang sudah ada di keranjang
    existing_qty = next(
        (item["qty"] for item in cart if item["product_id"] == product_id), 0
    )
    total_requested = existing_qty + quantity

    if product["stock"] < total_requested:
        print(
            f"Gagal: Stok {product['product_name']} tidak cukup! "
            f"(Sisa: {product['stock']}, Di keranjang: {existing_qty})"
        )
        return cart_id

    # Update qty jika sudah ada, tambah baru jika belum
    for item in cart:
        if item["product_id"] == product_id:
            item["qty"]      += quantity
            item["subtotal"]  = item["qty"] * item["price"]
            return cart_id

    cart.append({
        "product_id":   product_id,
        "product_name": product["product_name"],
        "name":         product["product_name"],    # alias kompatibilitas
        "price":        product["sell_price"],
        "qty":          quantity,
        "subtotal":     product["sell_price"] * quantity,
    })
    return cart_id


def remove_item_from_cart(session_id: str, product_id: int) -> list[dict]:
    """Hapus satu produk dari keranjang. Kembalikan isi keranjang terbaru."""
    cart_id = f"CART-{session_id}"
    if cart_id in _db_carts:
        _db_carts[cart_id] = [
            item for item in _db_carts[cart_id]
            if item["product_id"] != product_id
        ]
        return _db_carts[cart_id]
    return []


def get_cart(session_id: str) -> list[dict]:
    """Ambil isi keranjang saat ini."""
    return _db_carts.get(f"CART-{session_id}", [])


def clear_cart(session_id: str) -> None:
    """Kosongkan keranjang setelah transaksi selesai."""
    _db_carts.pop(f"CART-{session_id}", None)


# ─────────────────────────────────────────────────────────────────────────────
# KALKULASI
# ─────────────────────────────────────────────────────────────────────────────

def calculate_subtotal(session_id: str) -> float:
    """Hitung subtotal keranjang (sebelum diskon & poin)."""
    cart = get_cart(session_id)
    return float(sum(item["subtotal"] for item in cart))


def apply_member_discount(subtotal: float, member_id: int) -> float:
    """
    Terapkan diskon member jika ada.
    Saat ini tabel member tidak menyimpan discount_rate, jadi dikembalikan
    subtotal asli. Tambahkan kolom discount_rate ke tabel member jika diperlukan.
    """
    row = MemberRepository.get_by_id(member_id)
    if not row:
        return subtotal
    discount_rate = dict(row).get("discount_rate", 0.0)
    return float(subtotal * (1 - discount_rate))


def process_payment(
    total_akhir: float,
    amount_paid: float,
    payment_method: str,
) -> dict:
    """
    Validasi pembayaran.
    Kembalikan dict { status, changes, method } atau { status, error }.
    """
    if amount_paid >= total_akhir:
        return {
            "status":  True,
            "changes": round(amount_paid - total_akhir, 2),
            "method":  payment_method,
        }
    return {
        "status": False,
        "changes": 0.0,
        "error": "Nominal pembayaran kurang!",
    }


# ─────────────────────────────────────────────────────────────────────────────
# TRANSAKSI
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_user_id(user_id: int) -> int:
    """
    Pastikan user_id benar-benar ada di tabel user.
    Jika tidak valid, ambil id user pertama yang ada di DB.
    Mencegah FK constraint error saat INSERT ke tabel transaction.
    """
    if user_id:
        row = UserRepository.get_by_id(user_id)
        if row:
            return user_id

    # Fallback: ambil user pertama yang ada
    rows = UserRepository.get_all()
    if rows:
        return rows[0]["id"]

    raise RuntimeError(
        "Tidak ada user di database! Pastikan minimal 1 user sudah dibuat."
    )

def _generate_order_id() -> str:
    """Buat order_id harian: ORD-<tanggal>-<nomor urut 3 digit>."""
    today = datetime.now().strftime("%Y%m%d")
    count = TransactionRepository.get_daily_count(today)
    return f"ORD-{today}-{count + 1:03d}"


def create_transaction(
    customer_name: str,
    payment_method: str,
    is_member: bool,
    user_id: int,
    items: list[dict],
    amount_paid: float = 0.0,
    total_override: float | None = None,
) -> int:
    """
    [CREATE] Simpan transaksi baru ke SQLite.

    items : list[dict] — setiap item wajib punya:
        product_id, product_name (atau name), price, qty (atau quantity), subtotal

    Kembalikan transaction_id (INTEGER primary key).
    """
    total = total_override if total_override is not None \
            else sum(i["subtotal"] for i in items)
    changes   = max(0.0, amount_paid - total)
    order_id  = _generate_order_id()
    now       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Simpan header transaksi
    safe_user_id = _resolve_user_id(user_id)

    trx_id = TransactionRepository.tambah({
        "order_id":       order_id,
        "order_date":     now,
        "customer_name":  customer_name or None,
        "user_id":        safe_user_id,
        "total":          total,
        "changes":        changes,
        "payment_method": payment_method,
        "is_member":      1 if is_member else 0,
    })

    # Normalise item keys (kompatibilitas nama lama)
    normalized = []
    for item in items:
        pid = item.get("product_id")
        normalized.append({
            "product_id":   int(pid) if pid is not None else 0,
            "product_name": item.get("product_name") or item.get("name", "-"),
            "price":        float(item.get("price", 0)),
            "quantity":     int(item.get("qty") or item.get("quantity", 1)),
            "subtotal":     float(item.get("subtotal", 0)),
        })

    # Simpan item transaksi
    TransactionItemRepository.tambah_bulk(trx_id, normalized)

    # Kurangi stok di SQLite + rebuild cache JSON
    for item in normalized:
        kurangi_stok(item["product_id"], item["quantity"])

    return trx_id


def get_transaction(trx_id: int) -> dict:
    """
    [READ] Ambil header + items transaksi berdasarkan id (INTEGER).
    Kembalikan dict lengkap atau {} jika tidak ditemukan.
    """
    row = TransactionRepository.get_by_id(trx_id)
    if not row:
        return {}

    trx   = dict(row)
    items = [dict(r) for r in TransactionItemRepository.get_by_transaction(trx_id)]
    trx["items"] = items
    return trx


def get_transaction_by_order_id(order_id: str) -> dict:
    """
    [READ] Cari transaksi berdasarkan order_id (string, misal 'ORD-20240601-001').
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM [transaction] WHERE order_id = ?", (order_id,)
        ).fetchone()
    if not row:
        return {}
    return get_transaction(row["id"])


def get_all_transactions() -> list[dict]:
    """
    [READ] Ambil semua transaksi (header saja, tanpa items) untuk tabel laporan.
    """
    return [dict(r) for r in TransactionRepository.get_all()]


def update_transaction(trx_id: int, payment_method: str) -> bool:
    """
    [UPDATE] Ubah metode pembayaran transaksi yang sudah COMPLETED.
    Kembalikan True jika berhasil.
    """
    row = TransactionRepository.get_by_id(trx_id)
    if not row:
        return False

    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE [transaction] SET payment_method = ? WHERE id = ?",
            (payment_method, trx_id),
        )
        return cur.rowcount > 0


def void_transaction(trx_id: int) -> bool:
    """
    [VOID] Batalkan transaksi:
    - Kembalikan stok semua item ke SQLite
    - Hapus transaksi dari DB (hard delete karena tidak ada kolom status)
 
    Kembalikan True jika berhasil, False jika transaksi tidak ditemukan.
    """
    row = TransactionRepository.get_by_id(trx_id)
    if not row:
        return False
 
    items = TransactionItemRepository.get_by_transaction(trx_id)
 
    # Kembalikan stok
    with get_connection() as conn:
        for item in items:
            conn.execute(
                "UPDATE product SET stock = stock + ? WHERE id = ?",
                (item["quantity"], item["product_id"]),
            )
 
    # Hapus transaksi (CASCADE akan hapus transaction_item juga)
    TransactionRepository.hapus(trx_id)
    return True
 