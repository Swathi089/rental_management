from flask import Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from config.db import db
from bson import ObjectId
from datetime import datetime, timedelta

notification_bp = Blueprint(
    "notification",
    __name__,
    url_prefix="/api/notifications"
)


# Get notifications for logged-in user
@notification_bp.route("/", methods=["GET"])
@jwt_required()
def get_notifications():

    user_id = get_jwt_identity()

    notifications = list(
        db.notifications.find(
            {"user_id": user_id}
        ).sort("created_at", -1)
    )

    result = []

    for notification in notifications:
        result.append({
            "notification_id": str(notification["_id"]),
            "title": notification["title"],
            "message": notification["message"],
            "type": notification["type"],
            "is_read": notification.get("is_read", False),
            "created_at": notification["created_at"].isoformat()
        })

    return {
        "message": "Notifications retrieved successfully",
        "notifications": result
    }, 200


# Mark a notification as read
@notification_bp.route("/<notification_id>/read", methods=["PUT"])
@jwt_required()
def mark_notification_read(notification_id):

    user_id = get_jwt_identity()

    if not ObjectId.is_valid(notification_id):
        return {
            "message": "Invalid notification ID"
        }, 400

    result = db.notifications.update_one(
        {
            "_id": ObjectId(notification_id),
            "user_id": user_id
        },
        {
            "$set": {
                "is_read": True,
                "updated_at": datetime.utcnow()
            }
        }
    )

    if result.matched_count == 0:
        return {
            "message": "Notification not found"
        }, 404

    return {
        "message": "Notification marked as read"
    }, 200

# =========================================================
# Create upcoming rent reminders
# =========================================================

@notification_bp.route("/create-rent-reminders", methods=["POST"])
@jwt_required()
def create_rent_reminders():

    claims = get_jwt()

    if claims["role"] != "OWNER":
        return {
            "message": "Only owners can create rent reminders"
        }, 403

    owner_id = get_jwt_identity()

    today = datetime.utcnow()
    reminder_limit = today + timedelta(days=5)

    rent_records = list(
        db.rent_records.find({
            "owner_id": owner_id,
            "status": "PENDING",
            "due_date": {
                "$gte": today,
                "$lte": reminder_limit
            }
        })
    )

    reminders_created = 0

    for rent_record in rent_records:

        tenant_id = rent_record["tenant_id"]

        existing_notification = db.notifications.find_one({
            "user_id": str(tenant_id),
            "type": "RENT_REMINDER",
            "rent_record_id": rent_record["_id"]
        })

        if existing_notification:
            continue

        tenant = db.users.find_one({
            "_id": tenant_id,
            "role": "TENANT"
        })

        if not tenant:
            continue

        due_date = rent_record["due_date"]

        notification = {
            "user_id": str(tenant_id),
            "title": "Rent Due Soon",
            "message": (
                f"Your rent of ₹{rent_record['amount_due']} "
                f"for {rent_record['month']}/{rent_record['year']} "
                f"is due on {due_date.strftime('%d %B %Y')}."
            ),
            "type": "RENT_REMINDER",
            "rent_record_id": rent_record["_id"],
            "property_id": rent_record["property_id"],
            "is_read": False,
            "created_at": today,
            "updated_at": today
        }

        db.notifications.insert_one(notification)

        reminders_created += 1

    return {
        "message": "Rent reminders created successfully",
        "reminders_created": reminders_created
    }, 200