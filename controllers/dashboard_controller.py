"""
controllers/dashboard_controller.py
Semua query agregat untuk DashboardPage.
Tidak ada data hardcode — semuanya dari SQLite via database.py.
"""

from database import get_connection


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — batas waktu dalam format string lokal yang disimpan di DB
# ─────────────────────────────────────────────────────────────────────────────

def _period_bounds(period: str) -> tuple[str, str, str]:
    """
    Kembalikan (cur_start, prev_start, prev_end) sebagai string
    "datetime('now', OFFSET)" yang aman dipakai di WHERE clause.

    Catatan: order_date disimpan sebagai TEXT lokal ("2024-06-01 14:30:00").
    Kita bandingkan langsung dengan strftime SQLite agar konsisten.
    """
    offsets = {
        "daily":    ("-1 day",   "-2 days",  "-1 day"),
        "weekly":   ("-7 days",  "-14 days", "-7 days"),
        "monthly":  ("-30 days", "-60 days", "-30 days"),
        "annually": ("-365 days","-730 days","-365 days"),
    }
    cur_off, prev_start_off, prev_end_off = offsets.get(period, offsets["monthly"])
    # Gunakan 'localtime' agar cocok dengan data yang disimpan
    def _dt(off):
        return f"strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime', '{off}')"
    return _dt(cur_off), _dt(prev_start_off), _dt(prev_end_off)


# ─────────────────────────────────────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────────────────────────────────────

def get_kpi(period: str = "monthly") -> dict:
    """
    Kembalikan 4 KPI utama + persentase perubahan vs periode sebelumnya.

    Return:
        {
            "total_revenue":    {"value": float, "change_pct": float},
            "total_orders":     {"value": int,   "change_pct": float},
            "active_members":   {"value": int,   "change_pct": float},
            "avg_order_value":  {"value": float, "change_pct": float},
        }
    """
    cur_start, prev_start, prev_end = _period_bounds(period)

    with get_connection() as conn:
        # ── Revenue & Orders periode ini ──────────────────────────────────────
        cur = conn.execute(
            f"""
            SELECT
                COALESCE(SUM(total), 0) AS revenue,
                COUNT(*)                AS orders
            FROM [transaction]
            WHERE order_date >= {cur_start}
            """
        ).fetchone()

        # ── Revenue & Orders periode sebelumnya ───────────────────────────────
        prev = conn.execute(
            f"""
            SELECT
                COALESCE(SUM(total), 0) AS revenue,
                COUNT(*)                AS orders
            FROM [transaction]
            WHERE order_date >= {prev_start}
              AND order_date <  {prev_end}
            """
        ).fetchone()

        # ── Active members periode ini ────────────────────────────────────────
        # Gunakan member_id jika ada; fallback ke customer_name untuk kompatibilitas
        cur_members = conn.execute(
            f"""
            SELECT COUNT(DISTINCT COALESCE(customer_name, '')) AS cnt
            FROM [transaction]
            WHERE is_member = 1
              AND order_date >= {cur_start}
            """
        ).fetchone()["cnt"]

        prev_members = conn.execute(
            f"""
            SELECT COUNT(DISTINCT COALESCE(customer_name, '')) AS cnt
            FROM [transaction]
            WHERE is_member = 1
              AND order_date >= {prev_start}
              AND order_date <  {prev_end}
            """
        ).fetchone()["cnt"]

    cur_revenue  = float(cur["revenue"])
    cur_orders   = int(cur["orders"])
    prev_revenue = float(prev["revenue"])
    prev_orders  = int(prev["orders"])

    def _pct(cur_val, prev_val) -> float:
        if prev_val == 0:
            return 100.0 if cur_val > 0 else 0.0
        return round((cur_val - prev_val) / prev_val * 100, 1)

    cur_avg  = cur_revenue  / cur_orders  if cur_orders  else 0.0
    prev_avg = prev_revenue / prev_orders if prev_orders else 0.0

    return {
        "total_revenue":   {"value": cur_revenue,  "change_pct": _pct(cur_revenue,  prev_revenue)},
        "total_orders":    {"value": cur_orders,   "change_pct": _pct(cur_orders,   prev_orders)},
        "active_members":  {"value": cur_members,  "change_pct": _pct(cur_members,  prev_members)},
        "avg_order_value": {"value": cur_avg,       "change_pct": _pct(cur_avg,      prev_avg)},
    }


# ─────────────────────────────────────────────────────────────────────────────
# REVENUE TREND  (bar chart per-bulan)
# ─────────────────────────────────────────────────────────────────────────────

def get_revenue_trend(months: int = 6) -> list[dict]:
    """
    Revenue & jumlah order per bulan, N bulan ke belakang.

    Return: [{"month": "Jan", "revenue": 1500000, "orders": 42}, ...]
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                strftime('%m', order_date) AS mo,
                strftime('%Y', order_date) AS yr,
                COALESCE(SUM(total), 0)    AS revenue,
                COUNT(*)                   AS orders
            FROM [transaction]
            WHERE order_date >= strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime',
                                         ? || ' months')
            GROUP BY yr, mo
            ORDER BY yr, mo
            """,
            (f"-{months}",),
        ).fetchall()

    MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
                   "Jul", "Ags", "Sep", "Okt", "Nov", "Des"]

    return [
        {
            "month":   MONTH_NAMES[int(r["mo"])],
            "revenue": float(r["revenue"]),
            "orders":  int(r["orders"]),
        }
        for r in rows
    ]


# ─────────────────────────────────────────────────────────────────────────────
# SALES BY CATEGORY
# ─────────────────────────────────────────────────────────────────────────────

def get_sales_by_category() -> list[dict]:
    """
    Persentase penjualan per kategori produk (dari transaction_item).

    Return: [{"category": "Sembako", "pct": 35, "total": 1500000}, ...]
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                COALESCE(c.category, 'Lainnya') AS category,
                COALESCE(SUM(ti.subtotal), 0)   AS total
            FROM transaction_item ti
            JOIN product p
                ON ti.product_id = p.id
            LEFT JOIN category_product c
                ON p.category_id = c.id
            GROUP BY c.category
            ORDER BY total DESC
            """
        ).fetchall()

    if not rows:
        return []

    grand_total = sum(float(r["total"]) for r in rows) or 1.0
    return [
        {
            "category": r["category"],
            "total":    float(r["total"]),
            "pct":      round(float(r["total"]) / grand_total * 100),
        }
        for r in rows
    ]


# ─────────────────────────────────────────────────────────────────────────────
# RECENT TRANSACTIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_recent_transactions(limit: int = 5) -> list[dict]:
    """
    N transaksi terbaru.
    Pakai LEFT JOIN ke user agar transaksi tanpa user tetap muncul.

    Return:
        [{"order_id", "order_date", "customer_name", "total",
          "payment_method", "cashier"}, ...]
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                t.order_id,
                t.order_date,
                COALESCE(t.customer_name, 'Umum') AS customer_name,
                t.total,
                t.payment_method,
                COALESCE(u.name, 'System')         AS cashier
            FROM [transaction] t
            LEFT JOIN user u ON t.user_id = u.id
            ORDER BY t.order_date DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# TOP MEMBERS
# ─────────────────────────────────────────────────────────────────────────────

def get_top_members(limit: int = 5) -> list[dict]:
    """
    N member dengan total belanja tertinggi berdasarkan kolom total_spent
    di tabel member (diperbarui oleh loyalty_model).

    Fallback ke JOIN transaksi jika total_spent = 0 (data lama).

    Return:
        [{"member_name", "total_spent", "visit_count", "total_point"}, ...]
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                m.member_name,
                m.total_point,
                -- Prioritaskan kolom total_spent di tabel member;
                -- jika 0, hitung ulang dari transaksi sebagai fallback
                CASE
                    WHEN m.total_spent > 0 THEN m.total_spent
                    ELSE COALESCE(
                        (SELECT SUM(t.total)
                         FROM [transaction] t
                         WHERE t.customer_name = m.member_name
                           AND t.is_member = 1),
                        0
                    )
                END AS total_spent,
                COALESCE(
                    (SELECT COUNT(t.id)
                     FROM [transaction] t
                     WHERE t.customer_name = m.member_name
                       AND t.is_member = 1),
                    0
                ) AS visit_count
            FROM member m
            ORDER BY total_spent DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# STOCK ALERTS
# ─────────────────────────────────────────────────────────────────────────────

def get_low_stock(threshold: int = 10) -> list[dict]:
    """
    Produk dengan stock <= threshold, diurutkan dari yang paling sedikit.

    Return: [{"product_name", "stock", "stock_storage", "category"}, ...]
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                p.product_name,
                p.stock,
                p.stock_storage,
                COALESCE(c.category, 'Lainnya') AS category
            FROM product p
            LEFT JOIN category_product c ON p.category_id = c.id
            WHERE p.stock <= ?
            ORDER BY p.stock ASC
            LIMIT 10
            """,
            (threshold,),
        ).fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY — satu fungsi untuk semua data dashboard
# ─────────────────────────────────────────────────────────────────────────────

def get_dashboard_summary(period: str = "monthly") -> dict:
    """
    Ambil semua data dashboard sekaligus untuk mengurangi round-trip DB.

    Return:
        {
            "kpi":                  dict
            "revenue_trend":        list
            "sales_by_category":    list
            "recent_transactions":  list
            "top_members":          list
            "low_stock":            list
        }
    """
    return {
        "kpi":                  get_kpi(period),
        "revenue_trend":        get_revenue_trend(),
        "sales_by_category":    get_sales_by_category(),
        "recent_transactions":  get_recent_transactions(),
        "top_members":          get_top_members(),
        "low_stock":            get_low_stock(),
    }