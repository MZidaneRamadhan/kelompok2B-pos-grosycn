from kasir import (
    FILE_BARANG, 
    db_carts, 
    save_json, 
    load_json,
    add_item_to_cart, 
    calculate_subtotal, 
    apply_member_discount, 
    process_payment, 
    create_transaction
)

if __name__ == "__main__":
    dummy_products = {
        "PRD-1": {"name": "Minyak Goreng ", "sell_price": 35000, "stock": 100},
        "PRD-2": {"name": "Gula Pasir ", "sell_price": 15000, "stock": 50}
    }
    save_json(FILE_BARANG, dummy_products)
    

    SESSION_KASIR = "KASIR-001"
    MEMBER_ID = "MBR-1"

    cart_id = add_item_to_cart(SESSION_KASIR, "PRD-1", 2)
    cart_id = add_item_to_cart(SESSION_KASIR, "PRD-2", 3)
    for item in db_carts[cart_id]:
        print(f"{item['name']} x {item['qty']} = Rp {item['subtotal']}")
   
    subtotal = calculate_subtotal(cart_id)
    print(f"Subtotal Kotor\t\t: Rp {subtotal}")

    total_akhir = apply_member_discount(subtotal, MEMBER_ID)
    print(f"Total (Diskon Member)\t: Rp {total_akhir}")

    uang_pelanggan = 150000
    print(f"\nPEMBAYARAN (Uang Diterima: Rp {uang_pelanggan})")
    status_bayar = process_payment(cart_id, total_akhir, uang_pelanggan, "CASH")

    if status_bayar["status"]:
        trx_id = create_transaction(
            order_id=cart_id,
            customer_name="Warung Kelontong Maju",
            payment_method=status_bayar["method"],
            is_member=True,
            items=db_carts[cart_id]
        )
        del db_carts[cart_id]

    else:
        print(f"[GAGAL] {status_bayar['error']}")

    db_cek = load_json(FILE_BARANG)
    print(f"Sisa Minyak Goreng\t: {db_cek['PRD-1']['stock']} (Awal 100, Terjual 2)")
    print(f"Sisa Gula Pasir\t\t: {db_cek['PRD-2']['stock']} (Awal 50, Terjual 3)")
    
   