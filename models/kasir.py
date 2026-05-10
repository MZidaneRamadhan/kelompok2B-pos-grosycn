import json
import os
from datetime import datetime

from models.barang_sync import BARANG_FILE, deduct_db_stock_from_product_key

FILE_BARANG = BARANG_FILE
FILE_TRANSAKSI = 'database_transaksi.json'

def load_json(filename: str) -> dict:
    if not os.path.exists(filename):
        return {}
    with open(filename, 'r') as f:
        return json.load(f)

def save_json(filename: str, data: dict):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

db_carts = {} 
db_members = {"MBR-1": {"name": "Warung Kelontong Maju", "discount_rate": 0.05}}

def add_item_to_cart(session_id: str, product_id: str, quantity: int) -> str:
    cart_id = f"CART-{session_id}"
    db_products = load_json(FILE_BARANG)
    
    if cart_id not in db_carts:
        db_carts[cart_id] = []
        
    if product_id in db_products:
        product = db_products[product_id]
        
        existing_qty = 0
        for item in db_carts[cart_id]:
            if item["product_id"] == product_id:
                existing_qty = item["qty"]
                break

        total_requested_qty = existing_qty + quantity
        
        if product["stock"] >= total_requested_qty:
            item_exists = False
            
            for item in db_carts[cart_id]:
                if item["product_id"] == product_id:
                    item["qty"] += quantity
                    item["subtotal"] = item["qty"] * product["sell_price"]
                    item_exists = True
                    break
            
            if not item_exists:
                item = {
                    "product_id": product_id,
                    "name": product["name"],
                    "price": product["sell_price"],
                    "qty": quantity,
                    "subtotal": product["sell_price"] * quantity
                }
                db_carts[cart_id].append(item)
        else:
            print(f"Gagal: Stok {product['name']} tidak cukup! (Sisa: {product['stock']}, Di keranjang: {existing_qty})")
            
    return cart_id

def remove_item_from_cart(cart_id: str, product_id: str) -> list[dict]:
    if cart_id in db_carts:
        db_carts[cart_id] = [item for item in db_carts[cart_id] if item["product_id"] != product_id]
        return db_carts[cart_id]
    return []

def calculate_subtotal(cart_id: str) -> float:
    if cart_id not in db_carts:
        return 0.0
    total_kotor = sum(item["subtotal"] for item in db_carts[cart_id])
    return float(total_kotor)

def apply_member_discount(subtotal: float, member_id: str) -> float:
    if member_id in db_members:
        diskon = subtotal * db_members[member_id]["discount_rate"]
        return float(subtotal - diskon)
    return subtotal

def process_payment(cart_id: str, total_akhir: float, amount_paid: float, payment_method: str) -> dict:
    if amount_paid >= total_akhir:
        return {
            "status": True,
            "changes": amount_paid - total_akhir,
            "method": payment_method
        }
    return {"status": False, "changes": 0.0, "error": "Nominal pembayaran kurang!"}

def create_transaction(order_id: str, customer_name: str, payment_method: str, is_member: bool, items: list) -> str:
    transaction_id = f"TRX-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    db_products = load_json(FILE_BARANG)
    db_transactions = load_json(FILE_TRANSAKSI)
    
    for item in items:
        prod_id = item["product_id"]
        if prod_id in db_products:
            db_products[prod_id]["stock"] -= item["qty"]
            deduct_db_stock_from_product_key(prod_id, item["qty"])
            
    db_transactions[transaction_id] = {
        "order_id": order_id,
        "customer_name": customer_name,
        "payment_method": payment_method,
        "is_member": is_member,
        "items": items,
        "total_amount": sum(i['subtotal'] for i in items),
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "status": "COMPLETED"
    }
    
    save_json(FILE_BARANG, db_products)
    save_json(FILE_TRANSAKSI, db_transactions)
    
    return transaction_id

def get_transaction(transaction_id: str) -> dict:
    db_transactions = load_json(FILE_TRANSAKSI)
    return db_transactions.get(transaction_id, {})

def update_transaction(transaction_id: str, payment_method: str) -> bool:
    db_transactions = load_json(FILE_TRANSAKSI)
    
    if transaction_id in db_transactions and db_transactions[transaction_id]["status"] == "COMPLETED":
        db_transactions[transaction_id]["payment_method"] = payment_method
        save_json(FILE_TRANSAKSI, db_transactions)
        return True
        
    return False

def void_transaction(transaction_id: str) -> bool:
    db_transactions = load_json(FILE_TRANSAKSI)
    db_products = load_json(FILE_BARANG)
    
    if transaction_id in db_transactions:
        transaksi = db_transactions[transaction_id]
        
        if transaksi["status"] == "VOID":
            return False 
            
        for item in transaksi["items"]:
            prod_id = item["product_id"]
            if prod_id in db_products:
                db_products[prod_id]["stock"] += item["qty"] 
                
        transaksi["status"] = "VOID"
        
        save_json(FILE_BARANG, db_products)
        save_json(FILE_TRANSAKSI, db_transactions)
        
        return True
        
    return False