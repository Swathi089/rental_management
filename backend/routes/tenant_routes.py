from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from config.db import db
from bson import ObjectId
from datetime import datetime
import secrets


tenant_bp = Blueprint(
    "tenant",
    __name__,
    url_prefix="/api/tenants"
)


# Owner creates a tenant
@tenant_bp.route("/", methods=["POST"])
@jwt_required()
def create_tenant():

    claims = get_jwt()

    if claims["role"] != "OWNER":
        return {"message": "Only owners can create tenants"}, 403

    owner_id = get_jwt_identity()

    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")

    if not name or not email or not phone:
        return {
            "message": "Name, email and phone are required"
        }, 400

    existing_tenant = db.users.find_one({
        "email": email,
        "role": "TENANT"
    })

    if existing_tenant:
        return {
            "message": "A tenant with this email already exists"
        }, 400

    # Generate activation token
    activation_token = secrets.token_urlsafe(32)

    tenant = {
        "name": name,
        "email": email,
        "phone": phone,
        "role": "TENANT",
        "owner_id": owner_id,
        "activation_token": activation_token,
        "is_activated": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = db.users.insert_one(tenant)

    return {
        "message": "Tenant created successfully",
        "tenant_id": str(result.inserted_id),
        "activation_token": activation_token
    }, 201


# Owner views their tenants
@tenant_bp.route("/", methods=["GET"])
@jwt_required()
def get_owner_tenants():

    claims = get_jwt()

    if claims["role"] != "OWNER":
        return {
            "message": "Only owners can view tenants"
        }, 403

    owner_id = get_jwt_identity()

    tenants = list(
        db.users.find({
            "owner_id": owner_id,
            "role": "TENANT"
        })
    )

    result = []

    for tenant in tenants:
        result.append({
            "tenant_id": str(tenant["_id"]),
            "name": tenant["name"],
            "email": tenant["email"],
            "phone": tenant["phone"],
            "is_activated": tenant.get("is_activated", False),
            "created_at": tenant["created_at"].isoformat()
        })

    return {
        "message": "Tenants retrieved successfully",
        "tenants": result
    }, 200


# Owner assigns a tenant to a property
@tenant_bp.route("/<tenant_id>/assign-property", methods=["PUT"])
@jwt_required()
def assign_property_to_tenant(tenant_id):

    claims = get_jwt()

    if claims["role"] != "OWNER":
        return {
            "message": "Only owners can assign properties"
        }, 403

    owner_id = get_jwt_identity()

    data = request.get_json()

    property_id = data.get("property_id")
    due_day = data.get("due_day")

    if not property_id or due_day is None:
        return {
            "message": "property_id and due_day are required"
        }, 400

    if not ObjectId.is_valid(tenant_id):
        return {
            "message": "Invalid tenant ID"
        }, 400

    if not ObjectId.is_valid(property_id):
        return {
            "message": "Invalid property ID"
        }, 400

    try:
        due_day = int(due_day)
    except (ValueError, TypeError):
        return {
            "message": "due_day must be a number"
        }, 400

    if due_day < 1 or due_day > 28:
        return {
            "message": "due_day must be between 1 and 28"
        }, 400

    tenant = db.users.find_one({
        "_id": ObjectId(tenant_id),
        "owner_id": owner_id,
        "role": "TENANT"
    })

    if not tenant:
        return {
            "message": "Tenant not found under this owner"
        }, 404

    property_data = db.properties.find_one({
        "_id": ObjectId(property_id),
        "owner_id": owner_id
    })

    if not property_data:
        return {
            "message": "Property not found under this owner"
        }, 404

    # Prevent assigning a property to multiple tenants
    existing_tenant = db.users.find_one({
        "assigned_property_id": ObjectId(property_id),
        "role": "TENANT"
    })

    if existing_tenant and str(existing_tenant["_id"]) != tenant_id:
        return {
            "message": "This property is already assigned to another tenant"
        }, 400

    # Assign property to tenant
    db.users.update_one(
        {
            "_id": ObjectId(tenant_id)
        },
        {
            "$set": {
                "assigned_property_id": ObjectId(property_id),
                "due_day": due_day,
                "updated_at": datetime.utcnow()
            }
        }
    )

    # Update property
    db.properties.update_one(
        {
            "_id": ObjectId(property_id)
        },
        {
            "$set": {
                "tenant_id": ObjectId(tenant_id),
                "due_day": due_day,
                "status": "OCCUPIED",
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "message": "Tenant assigned to property successfully"
    }, 200


# Tenant views their assigned property
@tenant_bp.route("/my-property", methods=["GET"])
@jwt_required()
def get_my_property():

    claims = get_jwt()

    if claims["role"] != "TENANT":
        return {
            "message": "Only tenants can view their assigned property"
        }, 403

    tenant_id = get_jwt_identity()

    if not ObjectId.is_valid(tenant_id):
        return {
            "message": "Invalid tenant ID"
        }, 400

    tenant = db.users.find_one({
        "_id": ObjectId(tenant_id),
        "role": "TENANT"
    })

    if not tenant:
        return {
            "message": "Tenant not found"
        }, 404

    assigned_property_id = tenant.get("assigned_property_id")

    if not assigned_property_id:
        return {
            "message": "No property assigned to you"
        }, 404

    property_data = db.properties.find_one({
        "_id": assigned_property_id,
        "tenant_id": ObjectId(tenant_id)
    })

    if not property_data:
        return {
            "message": "Assigned property not found"
        }, 404

    return {
        "message": "Assigned property retrieved successfully",
        "property": {
            "property_id": str(property_data["_id"]),
            "title": property_data["title"],
            "description": property_data["description"],
            "property_type": property_data["property_type"],
            "address": property_data["address"],
            "city": property_data["city"],
            "bedrooms": property_data["bedrooms"],
            "bathrooms": property_data["bathrooms"],
            "area": property_data["area"],
            "rent": property_data["rent"],
            "deposit": property_data["deposit"],
            "due_day": property_data.get("due_day"),
            "amenities": property_data.get("amenities", []),
            "images": property_data.get("images", []),
            "status": property_data["status"]
        }
    }, 200


# Tenant sets their password for the first time
@tenant_bp.route("/set-password", methods=["POST"])
@jwt_required()
def set_tenant_password():

    claims = get_jwt()

    if claims["role"] != "TENANT":
        return {
            "message": "Only tenants can set a tenant password"
        }, 403

    tenant_id = get_jwt_identity()

    if not ObjectId.is_valid(tenant_id):
        return {
            "message": "Invalid tenant ID"
        }, 400

    data = request.get_json()

    if not data:
        return {
            "message": "Request body is required"
        }, 400

    password = data.get("password")

    if not password:
        return {
            "message": "Password is required"
        }, 400

    if len(password) < 6:
        return {
            "message": "Password must be at least 6 characters"
        }, 400

    from werkzeug.security import generate_password_hash

    password_hash = generate_password_hash(password)

    result = db.users.update_one(
        {
            "_id": ObjectId(tenant_id),
            "role": "TENANT"
        },
        {
            "$set": {
                "password": password_hash,
                "is_activated": True,
                "activation_token": None,
                "updated_at": datetime.utcnow()
            }
        }
    )

    if result.matched_count == 0:
        return {
            "message": "Tenant not found"
        }, 404

    return {
        "message": "Password set successfully"
    }, 200



# Tenant activates account and sets password
@tenant_bp.route("/activate", methods=["POST"])
def activate_tenant():

    data = request.get_json()

    if not data:
        return {
            "message": "Request body is required"
        }, 400

    activation_token = data.get("activation_token")
    password = data.get("password")

    if not activation_token or not password:
        return {
            "message": "activation_token and password are required"
        }, 400

    if len(password) < 6:
        return {
            "message": "Password must be at least 6 characters"
        }, 400

    tenant = db.users.find_one({
        "activation_token": activation_token,
        "role": "TENANT",
        "is_activated": False
    })

    if not tenant:
        return {
            "message": "Invalid or expired activation token"
        }, 400

    from werkzeug.security import generate_password_hash

    password_hash = generate_password_hash(password)

    db.users.update_one(
        {
            "_id": tenant["_id"]
        },
        {
            "$set": {
                "password": password_hash,
                "is_activated": True,
                "activation_token": None,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "message": "Tenant account activated successfully",
        "email": tenant["email"]
    }, 200



# Owner removes a tenant from their property
@tenant_bp.route("/<tenant_id>/remove-property", methods=["PUT"])
@jwt_required()
def remove_property_from_tenant(tenant_id):

    claims = get_jwt()

    if claims["role"] != "OWNER":
        return {
            "message": "Only owners can remove property assignments"
        }, 403

    owner_id = get_jwt_identity()

    if not ObjectId.is_valid(tenant_id):
        return {
            "message": "Invalid tenant ID"
        }, 400

    tenant = db.users.find_one({
        "_id": ObjectId(tenant_id),
        "owner_id": owner_id,
        "role": "TENANT"
    })

    if not tenant:
        return {
            "message": "Tenant not found under this owner"
        }, 404

    property_id = tenant.get("assigned_property_id")

    if not property_id:
        return {
            "message": "Tenant has no assigned property"
        }, 400

    # Remove property assignment from tenant
    db.users.update_one(
        {
            "_id": ObjectId(tenant_id)
        },
        {
            "$unset": {
                "assigned_property_id": "",
                "due_day": ""
            },
            "$set": {
                "updated_at": datetime.utcnow()
            }
        }
    )

    # Make property available again
    db.properties.update_one(
        {
            "_id": property_id,
            "owner_id": owner_id
        },
        {
            "$unset": {
                "tenant_id": "",
                "due_day": ""
            },
            "$set": {
                "status": "AVAILABLE",
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "message": "Tenant removed from property successfully"
    }, 200