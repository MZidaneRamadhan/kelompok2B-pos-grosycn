def new_category(id: int, name: str) -> dict:
    """Template struktur data category."""
    return {
        "id": id,
        "name": name
    }

def new_product(id: str, product_name: str, sell_price: float, buy_price: float,
                category_id: int, stock: int, stock_storage: int,
                description: str) -> dict:
    """Template struktur data product."""
    return {
        "id": id,
        "product_name": product_name,
        "sell_price": sell_price,
        "buy_price": buy_price,
        "category_id": category_id,
        "stock": stock,
        "stock_storage": stock_storage,
        "description": description
    }
