# ─────────────────────────────────────────────────────────────────────────────
# data/state.py
#
# Global mutable application state (replaces React Context / POSContext).
# A single STATE singleton is imported wherever cart or online status is needed.
# ─────────────────────────────────────────────────────────────────────────────


class AppState:
    """
    Central mutable state for the POS session.

    Attributes
    ----------
    cart : list[dict]
        Each entry: {productId, productName, price, qty, unit, image}
    offline_queue : list[dict]
        Transactions saved locally while offline: {id, total}
    is_online : bool
        Current network status toggle.
    """

    def __init__(self) -> None:
        self.cart: list[dict] = []
        self.offline_queue: list[dict] = []
        self.is_online: bool = True

    # ── Cart operations ───────────────────────────────────────────────────────

    def add_to_cart(
        self,
        product_id: str,
        product_name: str,
        price: float,
        unit: str,
        image: str,
    ) -> None:
        """Add one unit of (product_id, unit) to the cart, or increment qty."""
        for item in self.cart:
            if item["productId"] == product_id and item["unit"] == unit:
                item["qty"] += 1
                return
        self.cart.append(
            {
                "productId":   product_id,
                "productName": product_name,
                "price":       price,
                "qty":         1,
                "unit":        unit,
                "image":       image,
            }
        )

    def remove_from_cart(self, product_id: str, unit: str) -> None:
        """Remove all cart entries matching (product_id, unit)."""
        self.cart = [
            i for i in self.cart
            if not (i["productId"] == product_id and i["unit"] == unit)
        ]

    def update_qty(self, product_id: str, unit: str, qty: int) -> None:
        """Set the quantity for a cart line; removes it if qty ≤ 0."""
        if qty <= 0:
            self.remove_from_cart(product_id, unit)
            return
        for item in self.cart:
            if item["productId"] == product_id and item["unit"] == unit:
                item["qty"] = qty
                return

    def clear_cart(self) -> None:
        self.cart.clear()

    def cart_total(self) -> float:
        """Return the sum of (price × qty) across all cart lines."""
        return sum(i["price"] * i["qty"] for i in self.cart)

    # ── Network / sync ────────────────────────────────────────────────────────

    def toggle_online(self) -> str | None:
        """
        Toggle the is_online flag.

        Returns a human-readable sync message if the queue was flushed,
        or None if we just went offline.
        """
        self.is_online = not self.is_online
        if self.is_online and self.offline_queue:
            count = len(self.offline_queue)
            self.offline_queue.clear()
            return f"Synced {count} offline transaction{'s' if count != 1 else ''}"
        return None


# Module-level singleton – import this everywhere:
#   from data.state import STATE
STATE = AppState()
