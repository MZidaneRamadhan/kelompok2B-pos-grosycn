import uuid
from database.db_connection import read_json, write_json
from models.product import new_category, new_product

CATEGORY_FILE = "categories.json"
PRODUCT_FILE  = "products.json"

# --- Layanan Kategori (CRUD Category) ---

def create_category(category_name: str) -> int:
    """[CREATE] Menambahkan category barang baru dan mengembalikan Category ID."""
    categories = read_json(CATEGORY_FILE)
    new_id = max([c["id"] for c in categories], default=0) + 1
    categories.append(new_category(new_id, category_name))
    write_json(CATEGORY_FILE, categories)
    return new_id

def get_category(category_id: int) -> dict:
    """[READ] Menampilkan detail nama category berdasarkan Category ID."""
    categories = read_json(CATEGORY_FILE)
    for category in categories:
        if category["id"] == category_id:
            return category
    return None

def get_all_categories() -> list:
    """[READ] Menampilkan semua category."""
    return read_json(CATEGORY_FILE)

def update_category(category_id: int, new_category_name: str) -> bool:
    """[UPDATE] Mengubah nama category barang."""
    categories = read_json(CATEGORY_FILE)
    for category in categories:
        if category["id"] == category_id:
            category["name"] = new_category_name
            write_json(CATEGORY_FILE, categories)
            return True
    return False

def delete_category(category_id: int) -> bool:
    """[DELETE] Menghapus category barang dari sistem."""
    categories = read_json(CATEGORY_FILE)
    filtered = [category for category in categories if category["id"] != category_id]
    if len(filtered) == len(categories):
        return False  # category tidak ditemukan
    write_json(CATEGORY_FILE, filtered)
    return True


# --- Layanan Informasi Produk (CRUD Product) ---

def create_product(product_name: str, sell_price: float, buy_price: float,
                   category_id: int, stock: int, stock_storage: int,
                   description: str) -> str:
    """[CREATE] Mendaftarkan product baru ke katalog dan mengembalikan Product ID."""
    products = read_json(PRODUCT_FILE)
    product_id = "PRD-" + str(uuid.uuid4())[:8].upper()
    products.append(new_product(product_id, product_name, sell_price,
                                buy_price, category_id, stock,
                                stock_storage, description))
    write_json(PRODUCT_FILE, products)
    return product_id

def get_product(product_id: str) -> dict:
    """[READ] Mengambil seluruh detail informasi product berdasarkan Product ID."""
    products = read_json(PRODUCT_FILE)
    for product in products:
        if product["id"] == product_id:
            return product
    return None

def get_all_products() -> list:
    """[READ] Menampilkan semua product."""
    return read_json(PRODUCT_FILE)

def update_product(product_id: str, product_name: str, sell_price: float,
                   buy_price: float, category_id: int,
                   description: str) -> bool:
    """[UPDATE] Memperbarui data informasi product (tanpa mengubah stok fisik)."""
    products = read_json(PRODUCT_FILE)
    for product in products:
        if product["id"] == product_id:
            product["product_name"] = product_name
            product["sell_price"]   = sell_price
            product["buy_price"]    = buy_price
            product["category_id"]  = category_id
            product["description"]  = description
            write_json(PRODUCT_FILE, products)
            return True
    return False

def delete_product(product_id: str) -> bool:
    """[DELETE] Menghapus data product dari katalog secara permanen."""
    products = read_json(PRODUCT_FILE)
    filtered = [product for product in products if product["id"] != product_id]
    if len(filtered) == len(products):
        return False
    write_json(PRODUCT_FILE, filtered)
    return True


# --- Layanan Manajemen Stok (Fisik) ---

def add_stock(product_id: str, quantity: int, location: str) -> int:
    """Menambah jumlah fisik barang di lokasi tertentu (toko/gudang)."""
    products = read_json(PRODUCT_FILE)
    for product in products:
        if product["id"] == product_id:
            if location.lower() == "gudang":
                product["stock_storage"] += quantity
            else:
                product["stock"] += quantity
            write_json(PRODUCT_FILE, products)
            return product["stock"] + product["stock_storage"]
    return -1  # product tidak ditemukan

def deduct_stock(product_id: str, quantity: int, location: str) -> bool:
    """Mengurangi stok fisik karena penjualan atau pemindahan."""
    products = read_json(PRODUCT_FILE)
    for product in products:
        if product["id"] == product_id:
            if location.lower() == "gudang":
                if product["stock_storage"] < quantity:
                    return False  # stok tidak cukup
                product["stock_storage"] -= quantity
            else:
                if product["stock"] < quantity:
                    return False  # stok tidak cukup
                product["stock"] -= quantity
            write_json(PRODUCT_FILE, products)
            return True
    return False

def check_low_stock(threshold: int) -> list:
    """Mengembalikan daftar Product ID yang stoknya di bawah batas minimum."""
    products = read_json(PRODUCT_FILE)
    return [product["id"] for product in products if product["stock"] <= threshold]
