# ─────────────────────────────────────────────────────────────────────────────
# data/store.py
#
# Read-only seed data: products, customers, transactions, rewards, chart data.
# ─────────────────────────────────────────────────────────────────────────────

PRODUCTS: list[dict] = [
    {
        "id": "P001", "name": "Copy Paper A4", "category": "Office Supplies",
        "brand": "Premium Office", "sku": "OFF-PAP-A4-001", "stock": 2500, "low": 500, "image": "📄",
        "pricing": [
            {"unit": "piece", "price": 4.50,  "qty": 1},
            {"unit": "pack",  "price": 48.00, "qty": 12},
            {"unit": "box",   "price": 180.00,"qty": 50},
        ],
    },
    {
        "id": "P002", "name": "Ballpoint Pens - Blue", "category": "Office Supplies",
        "brand": "WriteWell", "sku": "OFF-PEN-BLU-002", "stock": 1800, "low": 300, "image": "🖊️",
        "pricing": [
            {"unit": "piece", "price": 0.75, "qty": 1},
            {"unit": "pack",  "price": 8.00, "qty": 12},
            {"unit": "box",   "price": 35.00,"qty": 50},
        ],
    },
    {
        "id": "P003", "name": "Spiral Notebooks", "category": "Office Supplies",
        "brand": "NoteMaster", "sku": "OFF-NOT-SPI-003", "stock": 960, "low": 200, "image": "📓",
        "pricing": [
            {"unit": "piece", "price": 3.25,  "qty": 1},
            {"unit": "pack",  "price": 36.00, "qty": 12},
            {"unit": "box",   "price": 140.00,"qty": 48},
        ],
    },
    {
        "id": "P004", "name": "LED Light Bulbs 9W", "category": "Electronics",
        "brand": "BrightLife", "sku": "ELC-LED-9W-004", "stock": 720, "low": 150, "image": "💡",
        "pricing": [
            {"unit": "piece", "price": 5.50,  "qty": 1},
            {"unit": "pack",  "price": 28.00, "qty": 6},
            {"unit": "box",   "price": 110.00,"qty": 24},
        ],
    },
    {
        "id": "P005", "name": "AA Alkaline Batteries", "category": "Electronics",
        "brand": "PowerMax", "sku": "ELC-BAT-AA-005", "stock": 1440, "low": 300, "image": "🔋",
        "pricing": [
            {"unit": "piece", "price": 1.50, "qty": 1},
            {"unit": "pack",  "price": 16.00,"qty": 12},
            {"unit": "box",   "price": 60.00,"qty": 48},
        ],
    },
    {
        "id": "P006", "name": "Hand Sanitizer 500ml", "category": "Health & Safety",
        "brand": "SafeGuard", "sku": "HLT-SAN-500-006", "stock": 576, "low": 100, "image": "🧴",
        "pricing": [
            {"unit": "piece", "price": 4.75, "qty": 1},
            {"unit": "pack",  "price": 52.00,"qty": 12},
            {"unit": "box",   "price": 95.00,"qty": 24},
        ],
    },
    {
        "id": "P007", "name": "Disposable Face Masks", "category": "Health & Safety",
        "brand": "MedProtect", "sku": "HLT-MSK-DIS-007", "stock": 5000, "low": 1000, "image": "😷",
        "pricing": [
            {"unit": "piece", "price": 0.35,  "qty": 1},
            {"unit": "pack",  "price": 18.00, "qty": 50},
            {"unit": "box",   "price": 160.00,"qty": 500},
        ],
    },
    {
        "id": "P008", "name": "Trash Bags - Large", "category": "Cleaning Supplies",
        "brand": "CleanPro", "sku": "CLN-BAG-LRG-008", "stock": 2400, "low": 500, "image": "🗑️",
        "pricing": [
            {"unit": "piece", "price": 0.45, "qty": 1},
            {"unit": "pack",  "price": 22.00,"qty": 50},
            {"unit": "box",   "price": 85.00,"qty": 200},
        ],
    },
    {
        "id": "P009", "name": "Multipurpose Cleaner 1L", "category": "Cleaning Supplies",
        "brand": "SparkleClean", "sku": "CLN-MPU-1L-009", "stock": 672, "low": 120, "image": "🧽",
        "pricing": [
            {"unit": "piece", "price": 3.80, "qty": 1},
            {"unit": "pack",  "price": 42.00,"qty": 12},
            {"unit": "box",   "price": 80.00,"qty": 24},
        ],
    },
    {
        "id": "P010", "name": "Paper Towels Roll", "category": "Cleaning Supplies",
        "brand": "AbsorbMax", "sku": "CLN-TWL-ROL-010", "stock": 1152, "low": 240, "image": "🧻",
        "pricing": [
            {"unit": "piece", "price": 2.25, "qty": 1},
            {"unit": "pack",  "price": 24.00,"qty": 12},
            {"unit": "box",   "price": 90.00,"qty": 48},
        ],
    },
]

CUSTOMERS: list[dict] = [
    {"id": "C001", "name": "Sarah Johnson",   "email": "sarah.j@email.com",   "phone": "+1 (555) 123-4567", "points": 1250, "spent": 342.50, "visits": 28, "join": "2025-08-15", "tier": "Gold"},
    {"id": "C002", "name": "Michael Chen",    "email": "m.chen@email.com",     "phone": "+1 (555) 234-5678", "points": 890,  "spent": 267.80, "visits": 22, "join": "2025-09-22", "tier": "Silver"},
    {"id": "C003", "name": "Emily Rodriguez", "email": "emily.r@email.com",    "phone": "+1 (555) 345-6789", "points": 2100, "spent": 548.25, "visits": 45, "join": "2025-06-10", "tier": "Platinum"},
    {"id": "C004", "name": "David Kim",       "email": "d.kim@email.com",      "phone": "+1 (555) 456-7890", "points": 450,  "spent": 156.75, "visits": 12, "join": "2025-11-05", "tier": "Bronze"},
    {"id": "C005", "name": "Jessica Taylor",  "email": "j.taylor@email.com",   "phone": "+1 (555) 567-8901", "points": 1680, "spent": 425.90, "visits": 35, "join": "2025-07-18", "tier": "Gold"},
    {"id": "C006", "name": "Robert Martinez", "email": "r.martinez@email.com", "phone": "+1 (555) 678-9012", "points": 320,  "spent": 98.40,  "visits": 8,  "join": "2026-01-12", "tier": "Bronze"},
]

TRANSACTIONS: list[dict] = [
    {"id": "TXN-20260406-001", "date": "2026-04-06", "time": "09:15 AM", "total": 11.28, "payment": "card",   "status": "completed", "location": "Downtown Store", "customer": "C001"},
    {"id": "TXN-20260406-002", "date": "2026-04-06", "time": "09:42 AM", "total": 9.35,  "payment": "mobile", "status": "completed", "location": "Downtown Store", "customer": "C002"},
    {"id": "TXN-20260405-003", "date": "2026-04-05", "time": "02:30 PM", "total": 11.50, "payment": "card",   "status": "completed", "location": "Mall Location",  "customer": None},
    {"id": "TXN-20260405-004", "date": "2026-04-05", "time": "11:20 AM", "total": 14.85, "payment": "cash",   "status": "completed", "location": "Airport Store",  "customer": None},
    {"id": "TXN-20260404-005", "date": "2026-04-04", "time": "03:15 PM", "total": 8.53,  "payment": "mobile", "status": "completed", "location": "Downtown Store", "customer": "C003"},
    {"id": "TXN-20260403-006", "date": "2026-04-03", "time": "08:45 AM", "total": 8.53,  "payment": "card",   "status": "completed", "location": "Mall Location",  "customer": "C004"},
    {"id": "TXN-20260402-007", "date": "2026-04-02", "time": "01:20 PM", "total": 10.45, "payment": "cash",   "status": "refunded",  "location": "Downtown Store", "customer": None},
    {"id": "TXN-20260401-008", "date": "2026-04-01", "time": "10:30 AM", "total": 17.05, "payment": "card",   "status": "completed", "location": "Airport Store",  "customer": "C005"},
]

REVENUE_DATA: list[tuple[str, int, int]] = [
    ("Jan", 145000, 298),
    ("Feb", 162000, 325),
    ("Mar", 178000, 342),
    ("Apr", 156000, 305),
    ("May", 189000, 365),
    ("Jun", 195000, 378),
]

REWARDS: list[dict] = [
    {"id": "R001", "name": "Free Espresso",         "desc": "Redeem for one free espresso",        "cost": 200, "cat": "Free Item"},
    {"id": "R002", "name": "10% Off Next Purchase",  "desc": "10% off your entire next order",      "cost": 150, "cat": "Discount"},
    {"id": "R003", "name": "Free Pastry",            "desc": "Choose any pastry from our selection","cost": 250, "cat": "Free Item"},
    {"id": "R004", "name": "Buy One Get One",        "desc": "BOGO on any beverage",                "cost": 500, "cat": "Special Offer"},
]
