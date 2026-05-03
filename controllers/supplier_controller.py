from models import supplier
from services import places_service
from services.places_service import PlacesAPIError
from utils.helpers import haversine, safe_average, timestamp_now
from config import API_KEY, TOKO_LAT, TOKO_LNG

def create_supplier(supplier_name: str, email: str,
                    phone: str, rating: float,
                    category: str, address: str) -> str:
    """
    [CREATE] Validasi lalu simpan supplier baru (input manual).
    Kembalikan supplier_id.
    """
    if not supplier_name.strip():
        raise ValueError("Nama supplier tidak boleh kosong")
    if not (0.0 <= rating <= 5.0):
        raise ValueError("Rating harus antara 0.0 dan 5.0")
    if email and "@" not in email:
        raise ValueError("Format email tidak valid")

    return supplier.create(
        supplier_name=supplier_name,
        email=email,
        phone=phone,
        rating=rating,
        category=category,
        source_data="Input manual",
        address=address,
    )                                       # -> str


def get_supplier(supplier_id: str) -> dict:
    """
    [READ] Ambil detail satu supplier berdasarkan ID.
    """
    supplier = supplier.get_by_id(supplier_id)
    if not supplier:
        raise ValueError(f"supplier {supplier_id} tidak ditemukan")
    return supplier                         # -> dict


def get_all_suppliers() -> list[dict]:
    """
    [READ] Ambil semua supplier aktif untuk ditampilkan di tabel.
    """
    return supplier.get_all()         # -> list[dict]


def update_supplier(supplier_id: str, supplier_name: str,
                    email: str, phone: str, rating: float) -> bool:
    if not supplier_name.strip():
        raise ValueError("Nama supplier tidak boleh kosong")
    if not (0.0 <= rating <= 5.0):
        raise ValueError("Rating harus antara 0.0 dan 5.0")

    existing = supplier.get_by_id(supplier_id)
    if not existing:
        raise ValueError("supplier tidak ditemukan")

    return supplier.update(
        supplier_id, supplier_name, email, phone, rating
    )                                       # -> bool


def delete_supplier(supplier_id: str) -> bool:
    if not supplier.get_by_id(supplier_id):
        raise ValueError("supplier tidak ditemukan")
    return supplier.delete(supplier_id)  # -> bool

def scrape_and_save(category: str, radius: int,
                    min_rating: float) -> list[dict]:
    ok, msg = places_service.diagnose(API_KEY, TOKO_LAT, TOKO_LNG)
    if not ok:
        raise PlacesAPIError(msg)

    raw_places = places_service.search_suppliers(
        API_KEY, category, TOKO_LAT, TOKO_LNG, radius
    )

    processed = []
    for place in raw_places:
        rating = place.get("rating", 0)
        if rating < min_rating:
            continue

        loc      = place["geometry"]["location"]
        distance = haversine(TOKO_LAT, TOKO_LNG, loc["lat"], loc["lng"])
        place_id = place.get("place_id", "")

        supplier_dict = {
            "place_id":      place_id,
            "supplierName":  place.get("name", "-"),
            "address":       place.get("vicinity") or place.get("formatted_address", "-"),
            "rating":        rating,
            "total_reviews": place.get("user_ratings_total", 0),
            "is_open":       place.get("opening_hours", {}).get("open_now"),
            "distance_m":    round(distance),
            "phone":         "-",
            "category":      category,
            "sourceData":    f"Google Maps API — {category}",
            "lat":           loc["lat"],
            "lng":           loc["lng"],
        }

        if place_id and not supplier.exists_by_place_id(place_id):
            supplier.create(
                supplier_name=supplier_dict["supplierName"],
                email="",
                phone="-",  
                rating=rating,
                source_data=supplier_dict["sourceData"],
                category=category,
                address=supplier_dict["address"],
                place_id=place_id,
                lat=loc["lat"],
                lng=loc["lng"],
                distance_m=round(distance),
            )

        processed.append(supplier_dict)

    processed.sort(key=lambda x: (
        -(x["is_open"] or 0),
        -x["rating"],
        x["distance_m"],
    ))

    return processed                        # -> list[dict]


def get_supplier_detail_from_api(place_id: str) -> dict:
    return places_service.get_detail(API_KEY, place_id)  # -> dict


# ── STATISTIK untuk Stat Cards ───────────────────────────────

def get_stats() -> dict:
    suppliers = supplier.get_all()
    total     = len(suppliers)
    ratings   = [s["rating"] for s in suppliers if s.get("rating")]
    categories= set(s.get("category", "") for s in suppliers)

    return {
        "total":       total,
        "avg_rating":  round(safe_average(ratings), 1),
        "categories":  len(categories),
    }                                       # -> dict


# ── SEARCH & FILTER ─────────────────────────────────────────

def search_suppliers_local(keyword: str) -> list[dict]:
    keyword = keyword.lower().strip()
    if not keyword:
        return supplier.get_all()

    return [
        s for s in supplier.get_all()
        if keyword in s["supplierName"].lower()
        or keyword in s.get("address", "").lower()
    ]                                       # -> list[dict]
