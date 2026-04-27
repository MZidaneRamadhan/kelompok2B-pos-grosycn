"""
config.py — Semua konfigurasi dan konstanta aplikasi GroSync
Ubah nilai di sini tanpa perlu menyentuh file lain.
"""

# ─────────────────────────────────────────
# API & LOKASI
# ─────────────────────────────────────────
API_KEY  = "GANTI_DENGAN_API_KEY_KAMU"
TOKO_LAT = -6.9175
TOKO_LNG = 107.6191

# ─────────────────────────────────────────
# GOOGLE PLACES API ENDPOINTS
# ─────────────────────────────────────────
PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
PLACES_TEXT_URL   = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAIL_URL = "https://maps.googleapis.com/maps/api/place/details/json"
PLACES_PHOTO_URL  = "https://maps.googleapis.com/maps/api/place/photo"

# ─────────────────────────────────────────
# KEYWORD MAP PER KATEGORI
# ─────────────────────────────────────────
KEYWORD_MAP: dict[str, list[str]] = {
    "Sembako":       ["distributor sembako", "grosir sembako",
                      "toko bahan makanan", "agen sembako",
                      "supplier beras"],
    "Minyak Goreng": ["distributor minyak goreng", "agen minyak goreng",
                      "grosir minyak", "distributor minyak kemasan"],
    "Minuman":       ["distributor minuman", "agen minuman kemasan",
                      "grosir minuman", "supplier air mineral"],
    "Snack":         ["distributor snack", "grosir makanan ringan",
                      "agen snack kemasan"],
    "Frozen Food":   ["distributor frozen food", "supplier makanan beku",
                      "grosir frozen food"],
}

# ─────────────────────────────────────────
# PALETTE WARNA UI
# ─────────────────────────────────────────
COLOR = {
    "purple":       "#5B5BD6",
    "purple_dark":  "#4747B8",
    "purple_light": "#EEEDFE",
    "bg":           "#F8F8FC",
    "white":        "#FFFFFF",
    "sidebar_bg":   "#1A1A2E",
    "sidebar_act":  "#5B5BD6",
    "text_pri":     "#11111A",
    "text_sec":     "#6E6E8A",
    "border":       "#E4E4EF",
    "success":      "#18A558",
    "success_bg":   "#E6F7EE",
    "warn":         "#F59E0B",
    "warn_bg":      "#FEF3C7",
    "danger":       "#DC2626",
    "danger_bg":    "#FEE2E2",
    "star":         "#F59E0B",
}

# ─────────────────────────────────────────
# PENGATURAN APLIKASI
# ─────────────────────────────────────────
APP_NAME       = "GroSync"
APP_VERSION    = "1.0.0"
# WINDOW_WIDTH   = 1280
# WINDOW_HEIGHT  = 800
# SIDEBAR_WIDTH  = 210
LOW_STOCK_THRESHOLD = 10
REQUEST_TIMEOUT     = 10     # detik
REQUEST_DELAY       = 0.3    # detik antar query

# ─────────────────────────────────────────
# PATH DATA
# ─────────────────────────────────────────
import os
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR      = os.path.join(BASE_DIR, "data")
SUPPLIER_FILE = os.path.join(DATA_DIR, "suppliers.json")
