from typing import Dict, List
from bson import ObjectId


def get_user_by_name(db, customer_name: str) -> Dict:
    user_data = db.users.find_one({"name": {"$regex": customer_name, "$options": "i"}}, {"password": 0})
    return user_data if user_data else {"error": f"User '{customer_name}' not found."}


def get_user_order_history(db, user_id: str) -> List[Dict]:
    try:
        return list(db.orders.find({"userId": ObjectId(user_id)}))
    except Exception:
        return [{"error": f"Could not retrieve order history for user ID {user_id}."}]


