from typing import Any, Dict, List, Optional


def get_top_k_products_by_price(db, name_field: str, k: int, order: str, category: Optional[str] = None) -> List[Dict]:
    query_filter: Dict[str, Any] = {}
    if category:
        query_filter[name_field] = {"$regex": category, "$options": "i"}
    sort_direction = -1 if order == "highest" else 1
    pipeline = [
        {"$match": query_filter},
        {"$addFields": {"numeric_price": {"$toDouble": "$price"}}},
        {"$sort": {"numeric_price": sort_direction}},
        {"$limit": k},
    ]
    return list(db.products.aggregate(pipeline))


def find_product_by_price_rank(db, name_field: str, rank: int, order: str, category: Optional[str] = None) -> Dict:
    query_filter: Dict[str, Any] = {}
    if category:
        query_filter[name_field] = {"$regex": category, "$options": "i"}
    sort_direction = -1 if order == "highest" else 1
    pipeline = [
        {"$match": query_filter},
        {"$addFields": {"numeric_price": {"$toDouble": "$price"}}},
        {"$sort": {"numeric_price": sort_direction}},
        {"$skip": max(0, rank - 1)},
        {"$limit": 1},
    ]
    results = list(db.products.aggregate(pipeline))
    return results[0] if results else {"message": f"Sorry, couldn't find a product at rank {rank}."}


def find_product_by_discount_rank(db, name_field: str, rank: int, order: str, category: Optional[str] = None) -> Dict:
    query_filter: Dict[str, Any] = {}
    if category:
        query_filter[name_field] = {"$regex": category, "$options": "i"}
    sort_direction = -1 if order == "highest" else 1
    pipeline = [
        {"$match": query_filter},
        {"$sort": {"discountPercentage": sort_direction}},
        {"$skip": max(0, rank - 1)},
        {"$limit": 1},
    ]
    results = list(db.products.aggregate(pipeline))
    return results[0] if results else {"message": f"Could not find a product at rank {rank} for discounts."}


def find_products_by_price_comparison(db, name_field: str, reference_product, comparison_type: str, limit: int) -> Dict:
    reference_price = reference_product["price"]
    reference_name = reference_product[name_field]
    query_filter: Dict[str, Any] = {}
    sort_order = None
    if comparison_type == "same":
        query_filter = {"price": reference_price, name_field: {"$ne": reference_name}}
    elif comparison_type == "lower":
        query_filter, sort_order = {"price": {"$lt": reference_price}}, [("price", -1)]
    elif comparison_type == "higher":
        query_filter, sort_order = {"price": {"$gt": reference_price}}, [("price", 1)]
    cursor = db.products.find(query_filter).limit(limit)
    if sort_order:
        cursor = cursor.sort(sort_order)
    return {
        "reference_product": {"name": reference_name, "price": reference_price},
        "comparison_type": comparison_type,
        "matching_products": list(cursor),
    }


def calculate_order_total(db, name_field: str, product_names: List[str]) -> Dict:
    total_cost = 0.0
    calculated_items: List[Dict[str, Any]] = []
    not_found_items: List[str] = []
    for name in product_names:
        product = db.products.find_one({name_field: {"$regex": name, "$options": "i"}})
        if product and "price" in product and "discountPercentage" in product:
            price = product["price"]
            discount = product["discountPercentage"]
            final_price = price * (1 - discount / 100)
            total_cost += final_price
            calculated_items.append({
                "name": product[name_field],
                "original_price": price,
                "discount_percentage": discount,
                "final_price": round(final_price, 2),
            })
        else:
            not_found_items.append(name)
    return {
        "total_cost": round(total_cost, 2),
        "calculated_items": calculated_items,
        "not_found_items": not_found_items,
    }


def get_product_prices_for_chart(db, name_field: str, product_names: List[str]) -> Dict:
    prices: List[Dict[str, Any]] = []
    not_found: List[str] = []
    for name in product_names:
        product = db.products.find_one({name_field: {"$regex": name, "$options": "i"}}, {"price": 1, name_field: 1})
        if product and "price" in product:
            prices.append({"name": product[name_field], "price": product["price"]})
        else:
            not_found.append(name)
    return {
        "type": "bar_chart",
        "data": {
            "labels": [item["name"] for item in prices],
            "datasets": [{"label": "Price", "data": [item["price"] for item in prices]}],
        },
        "not_found": not_found,
    }


def find_products_within_budget(db, name_field: str, budget: float, category: Optional[str], limit: int) -> Dict:
    query: Dict[str, Any] = {"price": {"$lte": float(budget)}}
    if category:
        query[name_field] = {"$regex": category, "$options": "i"}
    cursor = db.products.find(query).sort([("price", -1)]).limit(limit)
    results = list(cursor)
    if not results:
        return {"message": "No products found within the given budget."}
    return {"budget": float(budget), "results": results}


