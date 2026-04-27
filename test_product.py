from controllers.product_controller import *

# Test category
id1 = create_category("Minuman")
print("Buat category:", id1)
print("Ambil category:", get_category(id1))

# Test product
pid = create_product("Aqua 600ml", 3000, 2000, id1, 50, 100, "Air mineral")
print("Buat product:", pid)
print("Ambil product:", get_product(pid))

# Test stok
print("Tambah stok:", add_stock(pid, 10, "toko"))
print("Kurangi stok:", deduct_stock(pid, 5, "toko"))
print("Stok tipis:", check_low_stock(10))