from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from config.db import db
from bson import ObjectId
from datetime import datetime, timedelta


rent_bp = Blueprint(
    "rent",
    __name__,
    url_prefix="/api/rent"
)


# =========================================================
# Create monthly rent record
# =========================================================

@rent_bp.route("/", methods=["POST"])
@jwt_required()
def create_rent_record():

    claims = get_jwt()

    if claims["role"] != "OWNER":
        return {
            "message": "Only owners can create rent records"
        }, 403

    owner_id = get_jwt_identity()

    data = request.get_json() or {}

    tenant_id = data.get("tenant_id")
    property_id = data.get("property_id")
    month = data.get("month")
    year = data.get("year")

    if not tenant_id or not property_id or not month or not year:
        return {
            "message": "tenant_id, property_id, month and year are required"
        }, 400

    # Validate tenant ID
    if not ObjectId.is_valid(tenant_id):
        return {
            "message": "Invalid tenant ID"
        }, 400

    # Validate property ID
    if not ObjectId.is_valid(property_id):
        return {
            "message": "Invalid property ID"
        }, 400

    # Convert month and year to integers
    try:
        month = int(month)
        year = int(year)
    except (ValueError, TypeError):
        return {
            "message": "month and year must be numbers"
        }, 400

    # Validate month
    if month < 1 or month > 12:
        return {
            "message": "month must be between 1 and 12"
        }, 400

    # -----------------------------------------------------
    # Check tenant belongs to owner
    # -----------------------------------------------------

    tenant = db.users.find_one({
        "_id": ObjectId(tenant_id),
        "owner_id": owner_id,
        "role": "TENANT"
    })

    if not tenant:
        return {
            "message": "Tenant not found under this owner"
        }, 404

    # Get due day from tenant assignment
    due_day = tenant.get("due_day")

    if due_day is None:
        return {
            "message": "Due day is not set for this tenant"
        }, 400

    try:
        due_day = int(due_day)
    except (ValueError, TypeError):
        return {
            "message": "Invalid due day"
        }, 400

    if due_day < 1 or due_day > 28:
        return {
            "message": "Due day must be between 1 and 28"
        }, 400

    # Create actual due date
    due_date = datetime(
        year,
        month,
        due_day
    )

    # -----------------------------------------------------
    # Check property belongs to owner
    # -----------------------------------------------------

    property_data = db.properties.find_one({
        "_id": ObjectId(property_id),
        "owner_id": owner_id
    })

    if not property_data:
        return {
            "message": "Property not found under this owner"
        }, 404

    # -----------------------------------------------------
    # Check tenant is assigned to this property
    # -----------------------------------------------------

    if tenant.get("assigned_property_id") != ObjectId(property_id):
        return {
            "message": "This tenant is not assigned to this property"
        }, 400

    # -----------------------------------------------------
    # Prevent duplicate monthly rent record
    # -----------------------------------------------------

    existing_record = db.rent_records.find_one({
        "tenant_id": ObjectId(tenant_id),
        "property_id": ObjectId(property_id),
        "month": month,
        "year": year
    })

    if existing_record:
        return {
            "message": "Rent record already exists for this month"
        }, 400

    # -----------------------------------------------------
    # Get current property rent
    # -----------------------------------------------------

    current_rent = property_data["rent"]

    # -----------------------------------------------------
    # Create rent record
    # -----------------------------------------------------

    now = datetime.utcnow()

    rent_record = {
        "tenant_id": ObjectId(tenant_id),
        "property_id": ObjectId(property_id),
        "owner_id": owner_id,
        "month": month,
        "year": year,
        "amount_due": current_rent,
        "amount_paid": 0,
        "status": "PENDING",
        "due_date": due_date,
        "payment_date": None,
        "transaction_id": None,
        "created_at": now,
        "updated_at": now
    }

    result = db.rent_records.insert_one(rent_record)

    return {
        "message": "Rent record created successfully",
        "rent_record_id": str(result.inserted_id),
        "month": month,
        "year": year,
        "amount_due": current_rent,
        "due_date": due_date.isoformat(),
        "status": "PENDING"
    }, 201


# =========================================================
# Owner views rent records
# =========================================================

@rent_bp.route("/owner", methods=["GET"])
@jwt_required()
def get_owner_rent_records():

    claims = get_jwt()

    if claims["role"] != "OWNER":
        return {
            "message": "Only owners can view rent records"
        }, 403

    owner_id = get_jwt_identity()

    records = list(
        db.rent_records.find({
            "owner_id": owner_id
        }).sort([
            ("year", -1),
            ("month", -1)
        ])
    )

    result = []

    for record in records:

        tenant = db.users.find_one({
            "_id": record["tenant_id"]
        })

        property_data = db.properties.find_one({
            "_id": record["property_id"]
        })

        result.append({
            "rent_record_id": str(record["_id"]),
            "tenant_id": str(record["tenant_id"]),
            "tenant_name": tenant["name"] if tenant else None,
            "property_id": str(record["property_id"]),
            "property_title": (
                property_data["title"]
                if property_data
                else None
            ),
            "month": record["month"],
            "year": record["year"],
            "amount_due": record["amount_due"],
            "amount_paid": record["amount_paid"],
            "status": record["status"],
            "due_date": (
                record["due_date"].isoformat()
                if record.get("due_date")
                else None
            ),
            "payment_date": (
                record["payment_date"].isoformat()
                if record.get("payment_date")
                else None
            ),
            "transaction_id": record.get("transaction_id"),
            "created_at": record["created_at"].isoformat()
        })

    return {
        "message": "Rent records retrieved successfully",
        "rent_records": result
    }, 200


# =========================================================
# Tenant views their rent records
# =========================================================

@rent_bp.route("/my-rent", methods=["GET"])
@jwt_required()
def get_my_rent_records():

    claims = get_jwt()

    if claims["role"] != "TENANT":
        return {
            "message": "Only tenants can view their rent records"
        }, 403

    tenant_id = get_jwt_identity()

    if not ObjectId.is_valid(tenant_id):
        return {
            "message": "Invalid tenant ID"
        }, 400

    records = list(
        db.rent_records.find({
            "tenant_id": ObjectId(tenant_id)
        }).sort([
            ("year", -1),
            ("month", -1)
        ])
    )

    result = []

    for record in records:

        property_data = db.properties.find_one({
            "_id": record["property_id"]
        })

        result.append({
            "rent_record_id": str(record["_id"]),
            "property_id": str(record["property_id"]),
            "property_title": (
                property_data["title"]
                if property_data
                else None
            ),
            "month": record["month"],
            "year": record["year"],
            "amount_due": record["amount_due"],
            "amount_paid": record["amount_paid"],
            "status": record["status"],
            "due_date": (
                record["due_date"].isoformat()
                if record.get("due_date")
                else None
            ),
            "payment_date": (
                record["payment_date"].isoformat()
                if record.get("payment_date")
                else None
            ),
            "transaction_id": record.get("transaction_id"),
            "created_at": record["created_at"].isoformat()
        })

    return {
        "message": "Your rent records retrieved successfully",
        "rent_records": result
    }, 200


# =========================================================
# Tenant marks rent as paid
# =========================================================

@rent_bp.route("/<rent_record_id>/pay", methods=["PUT"])
@jwt_required()
def pay_rent(rent_record_id):

    claims = get_jwt()

    if claims["role"] != "TENANT":
        return {
            "message": "Only tenants can pay rent"
        }, 403

    tenant_id = get_jwt_identity()

    if not ObjectId.is_valid(rent_record_id):
        return {
            "message": "Invalid rent record ID"
        }, 400

    data = request.get_json() or {}

    transaction_id = data.get("transaction_id")

    if not transaction_id:
        return {
            "message": "transaction_id is required"
        }, 400

    # -----------------------------------------------------
    # Find rent record belonging to this tenant
    # -----------------------------------------------------

    rent_record = db.rent_records.find_one({
        "_id": ObjectId(rent_record_id),
        "tenant_id": ObjectId(tenant_id)
    })

    if not rent_record:
        return {
            "message": "Rent record not found"
        }, 404

    # -----------------------------------------------------
    # Prevent duplicate payment
    # -----------------------------------------------------

    if rent_record["status"] == "PAID":
        return {
            "message": "Rent is already paid"
        }, 400

    # -----------------------------------------------------
    # Get tenant details
    # -----------------------------------------------------

    tenant = db.users.find_one({
        "_id": ObjectId(tenant_id),
        "role": "TENANT"
    })

    if not tenant:
        return {
            "message": "Tenant not found"
        }, 404

    tenant_name = tenant["name"]

    # -----------------------------------------------------
    # Update rent record
    # -----------------------------------------------------

    payment_time = datetime.utcnow()

    update_result = db.rent_records.update_one(
        {
            "_id": ObjectId(rent_record_id),
            "tenant_id": ObjectId(tenant_id),
            "status": {
                "$ne": "PAID"
            }
        },
        {
            "$set": {
                "amount_paid": rent_record["amount_due"],
                "status": "PAID",
                "payment_date": payment_time,
                "transaction_id": transaction_id,
                "updated_at": payment_time
            }
        }
    )

    if update_result.modified_count == 0:
        return {
            "message": "Rent payment could not be completed"
        }, 400

    # -----------------------------------------------------
    # Create notification for owner
    # -----------------------------------------------------

    db.notifications.insert_one({
        "user_id": rent_record["owner_id"],
        "title": "Rent Payment Received",
        "message": (
            f"{tenant_name} has paid ₹"
            f"{rent_record['amount_due']} for "
            f"{rent_record['month']}/{rent_record['year']}."
        ),
        "type": "RENT_PAYMENT",
        "rent_record_id": ObjectId(rent_record_id),
        "tenant_id": ObjectId(tenant_id),
        "property_id": rent_record["property_id"],
        "is_read": False,
        "created_at": payment_time,
        "updated_at": payment_time
    })

    return {
        "message": "Rent paid successfully",
        "amount_paid": rent_record["amount_due"],
        "status": "PAID",
        "payment_date": payment_time.isoformat(),
        "transaction_id": transaction_id
    }, 200


# =========================================================
# Update overdue rent records
# =========================================================

@rent_bp.route("/update-overdue", methods=["PUT"])
@jwt_required()
def update_overdue_rent():

    claims = get_jwt()

    if claims["role"] != "OWNER":
        return {
            "message": "Only owners can update overdue rent"
        }, 403

    owner_id = get_jwt_identity()

    current_time = datetime.utcnow()

    result = db.rent_records.update_many(
        {
            "owner_id": owner_id,
            "status": "PENDING",
            "due_date": {
                "$lt": current_time
            }
        },
        {
            "$set": {
                "status": "OVERDUE",
                "updated_at": current_time
            }
        }
    )

    return {
        "message": "Overdue rent records updated successfully",
        "records_updated": result.modified_count
    }, 200


# =========================================================
# Create upcoming rent reminders
# =========================================================

