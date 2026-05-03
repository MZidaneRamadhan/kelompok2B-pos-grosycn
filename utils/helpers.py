"""
utils/helpers.py — Fungsi-fungsi pembantu umum yang dipakai di seluruh aplikasi.
Tidak bergantung pada PyQt6 atau module lain dari GroSync.
"""

import math
import re
from datetime import datetime


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Hitung jarak antara dua koordinat GPS dalam meter.
    Menggunakan formula Haversine.
    """
    R = 6371000
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a  = math.sin(dp/2)**2 + math.cos(p1) * math.cos(p2) * math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def format_distance(meters: int) -> str:
    """Konversi meter ke string yang mudah dibaca."""
    if meters < 1000:
        return f"{meters}m"
    return f"{meters / 1000:.1f}km"


def format_rupiah(amount: float) -> str:
    """Format angka ke format Rupiah Indonesia."""
    return f"Rp {amount:,.0f}".replace(",", ".")


def clean_price(raw: str) -> float:
    """
    Bersihkan string harga hasil scraping menjadi float.
    Contoh: 'Rp 12.500/kg' → 12500.0
    """
    digits = re.sub(r"[^\d]", "", raw)
    return float(digits) if digits else 0.0


def timestamp_now() -> str:
    """Kembalikan timestamp ISO format saat ini."""
    return datetime.now().isoformat()


def generate_order_id(prefix: str = "TXN") -> str:
    """Buat nomor order harian: TXN-20260412-001 (urutan dikelola controller)."""
    today = datetime.now().strftime("%Y%m%d")
    return f"{prefix}-{today}"


def truncate(text: str, max_len: int = 40) -> str:
    """Potong teks panjang dengan ellipsis."""
    return text if len(text) <= max_len else text[:max_len - 3] + "..."


def safe_average(values: list[float]) -> float:
    """Rata-rata aman — kembalikan 0.0 jika list kosong."""
    return sum(values) / len(values) if values else 0.0
