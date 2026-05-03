from database import init_db, ProdukRepository, TransaksiRepository

# Di awal aplikasi
init_db()

# Contoh buat transaksi penjualan
TransaksiRepository.buat(
    tipe="keluar",
    items=[{"produk_id": 1, "jumlah": 10, "harga_satuan": 15000}],
    nama_pelanggan="Warung Bu Sari",
    diskon=5000,
)