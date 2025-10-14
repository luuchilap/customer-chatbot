from typing import Any, Dict, List


def get_available_collections(db) -> List[str]:
    return db.list_collection_names()


def get_product_count(db) -> Dict[str, int]:
    return {"total_products": db.products.count_documents({})}


def search_products_by_name(db, name_field: str, name: str, limit: int = 10) -> List[Dict]:
    return list(db.products.find({name_field: {"$regex": name, "$options": "i"}}).limit(limit))


def get_product_by_id(db, object_id) -> Dict:
    result = db.products.find_one({"_id": object_id})
    return result if result else {"error": f"Product with ID {str(object_id)} not found"}


def get_product_categories(db) -> List[Dict]:
    return list(db['product-category'].find({}, {"_id": 0}))


