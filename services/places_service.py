"""
services/places_service.py
Semua komunikasi ke Google Places API ada di sini.
Tidak tahu tentang UI (PyQt6) maupun penyimpanan data (JSON).
"""

import time
import requests
from config import (
    PLACES_NEARBY_URL, PLACES_TEXT_URL,
    PLACES_DETAIL_URL, PLACES_PHOTO_URL,
    KEYWORD_MAP, REQUEST_TIMEOUT, REQUEST_DELAY,
    TOKO_LAT, TOKO_LNG
)
from utils.helpers import haversine


class PlacesAPIError(Exception):
    """Exception khusus untuk error Google Places API."""
    pass


# ── FUNGSI INTERNAL ─────────────────────────────────────────

def _get(url: str, params: dict) -> dict:
    """
    Kirim GET request ke Places API.
    Raise PlacesAPIError jika terjadi masalah.
    """
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        data = resp.json()
    except requests.exceptions.ConnectionError:
        raise PlacesAPIError(
            "Tidak bisa terhubung ke internet.\n"
            "Periksa koneksi jaringan kamu."
        )
    except Exception as e:
        raise PlacesAPIError(f"Error request: {str(e)}")

    status = data.get("status")
    if status == "REQUEST_DENIED":
        raise PlacesAPIError(
            f"API Key ditolak!\n\n"
            f"Error: {data.get('error_message', '')}\n\n"
            f"Pastikan:\n"
            f"1. Places API sudah di-enable di Google Cloud Console\n"
            f"2. API Key sudah dimasukkan di config.py"
        )
    if status == "OVER_QUERY_LIMIT":
        raise PlacesAPIError("Quota API habis untuk hari ini.")

    return data


# ── NEARBY SEARCH ───────────────────────────────────────────

def nearby_search(api_key: str, lat: float, lng: float,
                  keyword: str, radius: int) -> list[dict]:
    """
    Cari tempat di sekitar koordinat dengan keyword tertentu.
    Ambil hingga 3 halaman (60 hasil maks).
    """
    results = []
    params  = {
        "location": f"{lat},{lng}",
        "radius":   radius,
        "keyword":  keyword,
        "language": "id",
        "key":      api_key,
    }

    for _ in range(3):                          # maks 3 halaman
        data = _get(PLACES_NEARBY_URL, params)
        results.extend(data.get("results", []))

        next_token = data.get("next_page_token")
        if not next_token:
            break
        time.sleep(2)                           # wajib tunggu 2 detik
        params = {"pagetoken": next_token, "key": api_key}

    return results                              # -> list[dict]


# ── TEXT SEARCH ─────────────────────────────────────────────

def text_search(api_key: str, query: str,
                lat: float, lng: float, radius: int) -> list[dict]:
    """
    Cari dengan query teks bebas — menangkap toko yang
    namanya tidak exact match keyword nearbySearch.
    """
    params = {
        "query":    query,
        "location": f"{lat},{lng}",
        "radius":   radius,
        "language": "id",
        "key":      api_key,
    }
    data = _get(PLACES_TEXT_URL, params)
    return data.get("results", [])              # -> list[dict]


# ── PLACE DETAIL ────────────────────────────────────────────

def get_detail(api_key: str, place_id: str) -> dict:
    """
    Ambil detail lengkap satu tempat: telepon, website,
    jam buka, foto, review.
    Panggil hanya saat user klik satu supplier — hemat quota.
    """
    params = {
        "place_id": place_id,
        "fields":   "name,formatted_phone_number,website,"
                    "opening_hours,rating,reviews,photos",
        "language": "id",
        "key":      api_key,
    }
    data = _get(PLACES_DETAIL_URL, params)
    return data.get("result", {})               # -> dict


# ── PHOTO URL ───────────────────────────────────────────────

def get_photo_url(api_key: str, photo_reference: str,
                  max_width: int = 400) -> str:
    """
    Buat URL foto supplier yang bisa langsung dipakai
    sebagai src gambar. Tidak melakukan request — hanya
    membuat URL-nya saja.
    """
    return (
        f"{PLACES_PHOTO_URL}"
        f"?photo_reference={photo_reference}"
        f"&maxwidth={max_width}"
        f"&key={api_key}"
    )


def get_photo_bytes(api_key: str, photo_reference: str,
                    max_width: int = 400) -> bytes | None:
    """
    Download foto sebagai bytes untuk ditampilkan di PyQt6
    tanpa perlu simpan ke disk.
    """
    url = get_photo_url(api_key, photo_reference, max_width)
    try:
        resp = requests.get(url, allow_redirects=True,
                            timeout=REQUEST_TIMEOUT)
        return resp.content if resp.status_code == 200 else None
    except Exception:
        return None


# ── MULTI-QUERY ORCHESTRATOR ────────────────────────────────

def search_suppliers(api_key: str, category: str,
                     lat: float, lng: float,
                     radius: int) -> list[dict]:
    """
    Jalankan multi-query untuk satu kategori:
    setiap keyword → nearbySearch + textSearch.
    Kembalikan list raw Places API result yang sudah deduplikasi.

    Ini adalah fungsi utama yang dipanggil oleh Controller.
    """
    keywords = KEYWORD_MAP.get(category, [f"distributor {category}"])
    seen_ids: set  = set()
    all_raw:  list = []

    for keyword in keywords:
        # NearbySearch
        for place in nearby_search(api_key, lat, lng, keyword, radius):
            pid = place.get("place_id")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                all_raw.append(place)

        # TextSearch — tangkap toko yang tidak match exact keyword
        for place in text_search(api_key, f"{keyword} dekat sini",
                                  lat, lng, radius):
            pid = place.get("place_id")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                all_raw.append(place)

        time.sleep(REQUEST_DELAY)

    return all_raw                              # -> list[dict]


# ── DIAGNOSTIC ──────────────────────────────────────────────

def diagnose(api_key: str, lat: float, lng: float) -> tuple[bool, str]:
    """
    Cek apakah API key valid dan Places API aktif.
    Kembalikan (True, pesan_ok) atau (False, pesan_error).
    """
    if api_key in {
        "GANTI_DENGAN_API_KEY_KAMU",
        "YOUR_GOOGLE_MAPS_API_KEY",
        "",
    }:
        return False, "API Key belum diisi di config.py"

    try:
        params = {
            "location": f"{lat},{lng}",
            "radius":   1000,
            "keyword":  "toko",
            "key":      api_key,
        }
        data   = _get(PLACES_NEARBY_URL, params)
        status = data.get("status")
        if status in ("OK", "ZERO_RESULTS"):
            return True, "API Key valid dan Places API aktif"
        return False, f"Status tidak terduga: {status}"
    except PlacesAPIError as e:
        return False, str(e)
