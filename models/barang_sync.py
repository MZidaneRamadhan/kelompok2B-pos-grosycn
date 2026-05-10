import json
import os
from typing import Any

from database import get_connection

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BARANG_FILE = os.path.join(ROOT_DIR, "database_barang.json")


def _product_key(product_id: int) -> str:
    return f"PRD-{product_id}"


def _product_id_from_key(product_key: str) -> int | None:
    if isinstance(product_key, str) and product_key.startswith("PRD-"):
        try:
            return int(product_key.split("-", 1)[1])
        except ValueError:
            return None
    return None


def load_json(filename: str = BARANG_FILE) -> dict[str, Any]:
    if not os.path.exists(filename):
        return {}
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename: str = BARANG_FILE, data: dict[str, Any] | None = None) -> None:
    if data is None:
        data = {}
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def _normalize_product_row(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": product.get("product_name", product.get("name", "Unknown Product")),
        "sell_price": float(product.get("sell_price", 0)),
        "buy_price": float(product.get("buy_price", 0)),
        "stock": int(product.get("stock", 0)),
        "stock_storage": int(product.get("stock_storage", 0)),
        "category": product.get("category", "General") or "General",
        "sku": product.get("sku", f"SKU-{product.get('id', '')}"),
        "brand": product.get("brand", ""),
        "image": product.get("image", "📦"),
        "low": int(product.get("low", 5)),
        "description": product.get("description", ""),
        "pricing": product.get(
            "pricing",
            [{"unit": "piece", "price": float(product.get("sell_price", 0)), "qty": 1}],
        ),
    }


def sync_json_from_db() -> dict[str, Any]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT p.id, p.product_name, p.sell_price, p.buy_price, p.stock, p.stock_storage, p.description, "
            "c.category AS category "
            "FROM product p "
            "LEFT JOIN category_product c ON p.category_id = c.id "
            "ORDER BY p.id ASC"
        ).fetchall()

    if not rows:
        return load_json()

    data: dict[str, Any] = {}
    for prod in rows:
        row = dict(prod)
        data[_product_key(row["id"])] = _normalize_product_row(row)

    save_json(data=data)
    return data


def update_json_product(product_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT p.id, p.product_name, p.sell_price, p.buy_price, p.stock, p.stock_storage, p.description, "
            "c.category AS category "
            "FROM product p "
            "LEFT JOIN category_product c ON p.category_id = c.id "
            "WHERE p.id = ?",
            (product_id,),
        ).fetchone()

    if not row:
        return False

    data = load_json()
    data[_product_key(product_id)] = _normalize_product_row(dict(row))
    save_json(data=data)
    return True


def delete_json_product(product_id: int) -> bool:
    data = load_json()
    key = _product_key(product_id)
    if key in data:
        del data[key]
        save_json(data=data)
        return True
    return False


def sync_json_category(old_name: str, new_name: str) -> bool:
    if not old_name:
        return False
    data = load_json()
    changed = False
    for product in data.values():
        if product.get("category") == old_name:
            product["category"] = new_name or "Uncategorized"
            changed = True
    if changed:
        save_json(data=data)
    return changed


def deduct_db_stock_from_product_key(product_key: str, qty: int) -> bool:
    product_id = _product_id_from_key(product_key)
    if product_id is None:
        return False

    with get_connection() as conn:
        row = conn.execute(
            "SELECT stock FROM product WHERE id = ?",
            (product_id,),
        ).fetchone()
        if not row or row[0] < qty:
            return False
        conn.execute(
            "UPDATE product SET stock = stock - ? WHERE id = ?",
            (qty, product_id),
        )
    return True
