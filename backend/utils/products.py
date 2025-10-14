from typing import Any


def detect_product_name_field(db) -> str:
    """Return the canonical product name field present in the collection.

    Prefer "name" if available; otherwise fall back to "title".
    """
    sample_product: Any = db.products.find_one(projection={"name": 1, "title": 1})
    return "name" if sample_product and "name" in sample_product else "title"


