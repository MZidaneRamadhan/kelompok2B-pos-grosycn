# ─────────────────────────────────────────────────────────────────────────────
# controllers/supplier_product_controller.py
# ─────────────────────────────────────────────────────────────────────────────

from models import supplier_product_model
from models import supplier_model


def link_supplier_to_product(supplier_id: int, product_id: int) -> int:
    """
    [CREATE] Hubungkan supplier ke product.
    Raise ValueError bila relasi sudah ada.
    Kembalikan link_id baru.
    """
    result = supplier_product_model.link(supplier_id, product_id)
    if result is None:
        raise ValueError("Supplier ini sudah terhubung ke product tersebut.")
    return result                               # -> int


def unlink_supplier_from_product(link_id: int) -> bool:
    """
    [DELETE] Lepas relasi berdasarkan link_id (PK supplier_product).
    """
    if not supplier_product_model.unlink(link_id):
        raise ValueError(f"Relasi ID {link_id} tidak ditemukan.")
    return True                                 # -> bool


def get_suppliers_for_product(product_id: int) -> list[dict]:
    """
    [READ] Ambil semua supplier aktif yang menyediakan product ini.
    Dipakai oleh SupplierProductDialog di StoragePage.
    """
    return supplier_product_model.get_suppliers_by_product(product_id)  # -> list[dict]


def get_all_suppliers_with_linked_flag(product_id: int) -> list[dict]:
    """
    [READ] Ambil SEMUA supplier aktif, dengan flag 'is_linked' (True/False)
    terhadap product_id yang diberikan.
    Dipakai saat memilih supplier baru dari dialog.
    """
    all_suppliers = supplier_model.get_all()
    linked_ids = {
        s["supplier_id"]
        for s in supplier_product_model.get_suppliers_by_product(product_id)
    }
    for s in all_suppliers:
        s["is_linked"] = s["id"] in linked_ids
    return all_suppliers                        # -> list[dict]