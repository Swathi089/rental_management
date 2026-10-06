from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from config.db import db
from bson import ObjectId
from datetime import datetime

property_bp = Blueprint(
    "property",
    __name__,
    url_prefix="/api/properties"
)


# =========================================================
# ADD PROPERTY
# =========================================================

@property_bp.route("/", methods=["POST"])
@jwt_required()
def add_property():

    claims = get_jwt()

    if claims["role"] != "OWNER":
        return {"message": "Only owners can add properties"}, 403

    data = request.get_json()

    required_fields = [
        "title",
        "description",
        "property_type",
        "address",
        "city",
        "bedrooms",
        "bathrooms",
        "area",
        "rent",
        "deposit"
    ]

    for field in required_fields:
        if field not in data:
            return {"message": f"{field} is required"}, 400

    property_data = {
        "owner_id": get_jwt_identity(),
        "title": data["title"],
        "description": data["description"],
        "property_type": data["property_type"],
        "address": data["address"],
        "city": data["city"],
        "bedrooms": data["bedrooms"],
        "bathrooms": data["bathrooms"],
        "area": data["area"],
        "rent": data["rent"],
        "deposit": data["deposit"],
        "images": data.get("images", []),
        "amenities": data.get("amenities", []),
        "status": "AVAILABLE",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = db.properties.insert_one(property_data)

    return {
        "message": "Property added successfully",
        "property_id": str(result.inserted_id)
    }, 201


# =========================================================
# GET OWNER'S PROPERTIES
# =========================================================

@property_bp.route("/owner", methods=["GET"])
@jwt_required()
def get_owner_properties():

    claims = get_jwt()

    if claims["role"] != "OWNER":
        return {
            "message": "Only owners can view their properties"
        }, 403

    owner_id = get_jwt_identity()

    properties = list(
        db.properties.find({
            "owner_id": owner_id
        })
    )

    result = []

    for property in properties:

        result.append({
            "property_id": str(property["_id"]),
            "title": property.get("title"),
            "description": property.get("description"),
            "property_type": property.get("property_type"),
            "address": property.get("address"),
            "city": property.get("city"),
            "bedrooms": property.get("bedrooms"),
            "bathrooms": property.get("bathrooms"),
            "area": property.get("area"),
            "rent": property.get("rent"),
            "deposit": property.get("deposit"),
            "images": property.get("images", []),
            "amenities": property.get("amenities", []),
            "status": property.get("status"),
            "created_at": (
                property["created_at"].isoformat()
                if property.get("created_at")
                else None
            ),
            "updated_at": (
                property["updated_at"].isoformat()
                if property.get("updated_at")
                else None
            )
        })

    return {
        "message": "Properties retrieved successfully",
        "properties": result
    }, 200


# =========================================================
# EDIT PROPERTY
# =========================================================

@property_bp.route("/<property_id>", methods=["PUT"])
@jwt_required()
def edit_property(property_id):

    claims = get_jwt()

    if claims["role"] != "OWNER":
        return {"message": "Only owners can edit properties"}, 403

    owner_id = get_jwt_identity()

    try:
        property_object_id = ObjectId(property_id)
    except Exception:
        return {"message": "Invalid property ID"}, 400

    property_data = db.properties.find_one({
        "_id": property_object_id,
        "owner_id": owner_id
    })

    if not property_data:
        return {
            "message": "Property not found or not owned by you"
        }, 404

    data = request.get_json()

    allowed_fields = [
        "title",
        "description",
        "property_type",
        "address",
        "city",
        "bedrooms",
        "bathrooms",
        "area",
        "deposit",
        "images",
        "amenities",
        "status"
    ]

    update_data = {}

    for field in allowed_fields:
        if field in data:
            update_data[field] = data[field]

    update_data["updated_at"] = datetime.utcnow()

    db.properties.update_one(
        {
            "_id": property_object_id,
            "owner_id": owner_id
        },
        {
            "$set": update_data
        }
    )

    return {
        "message": "Property updated successfully"
    }, 200


# =========================================================
# CHANGE RENT
# =========================================================

@property_bp.route("/<property_id>/rent", methods=["PUT"])
@jwt_required()
def change_rent(property_id):

    claims = get_jwt()

    if claims["role"] != "OWNER":
        return {"message": "Only owners can change rent"}, 403

    owner_id = get_jwt_identity()

    try:
        property_object_id = ObjectId(property_id)
    except Exception:
        return {"message": "Invalid property ID"}, 400

    property_data = db.properties.find_one({
        "_id": property_object_id,
        "owner_id": owner_id
    })

    if not property_data:
        return {
            "message": "Property not found or not owned by you"
        }, 404

    data = request.get_json()

    if "new_rent" not in data:
        return {"message": "new_rent is required"}, 400

    new_rent = data["new_rent"]
    old_rent = property_data["rent"]

    if new_rent == old_rent:
        return {
            "message": "New rent is same as current rent"
        }, 400

    db.properties.update_one(
        {
            "_id": property_object_id,
            "owner_id": owner_id
        },
        {
            "$set": {
                "rent": new_rent,
                "updated_at": datetime.utcnow()
            }
        }
    )

    rent_history = {
        "property_id": property_id,
        "old_rent": old_rent,
        "new_rent": new_rent,
        "effective_from": datetime.utcnow(),
        "changed_by": owner_id,
        "created_at": datetime.utcnow()
    }

    db.rent_history.insert_one(rent_history)

    return {
        "message": "Rent updated successfully",
        "old_rent": old_rent,
        "new_rent": new_rent
    }, 200


# =========================================================
# GET RENT HISTORY
# =========================================================

@property_bp.route("/<property_id>/rent-history", methods=["GET"])
@jwt_required()
def get_rent_history(property_id):

    claims = get_jwt()

    if claims["role"] != "OWNER":
        return {
            "message": "Only owners can view rent history"
        }, 403

    owner_id = get_jwt_identity()

    try:
        property_object_id = ObjectId(property_id)
    except Exception:
        return {"message": "Invalid property ID"}, 400

    property_data = db.properties.find_one({
        "_id": property_object_id,
        "owner_id": owner_id
    })

    if not property_data:
        return {
            "message": "Property not found or not owned by you"
        }, 404

    history = list(
        db.rent_history.find({
            "property_id": property_id,
            "changed_by": owner_id
        }).sort("created_at", 1)
    )

    result = []

    for record in history:

        result.append({
            "history_id": str(record["_id"]),
            "property_id": record.get("property_id"),
            "old_rent": record.get("old_rent"),
            "new_rent": record.get("new_rent"),
            "effective_from": (
                record["effective_from"].isoformat()
                if record.get("effective_from")
                else None
            ),
            "changed_by": record.get("changed_by"),
            "created_at": (
                record["created_at"].isoformat()
                if record.get("created_at")
                else None
            )
        })

    return {
        "message": "Rent history retrieved successfully",
        "current_rent": property_data["rent"],
        "rent_history": result
    }, 200


# =========================================================
# GET AVAILABLE PROPERTIES
# =========================================================
# NOTE:
# This is kept for now because it already exists in your
# backend. Later we should remove this marketplace-style
# functionality because your app is a private rental manager.

@property_bp.route("/", methods=["GET"])
@jwt_required()
def get_available_properties():

    claims = get_jwt()

    if claims["role"] != "TENANT":
        return {
            "message": "Only tenants can search properties"
        }, 403

    query = {
        "status": "AVAILABLE"
    }

    city = request.args.get("city")
    property_type = request.args.get("property_type")
    min_rent = request.args.get("min_rent")
    max_rent = request.args.get("max_rent")
    bedrooms = request.args.get("bedrooms")

    if city:
        query["city"] = city

    if property_type:
        query["property_type"] = property_type

    if min_rent:
        query["rent"] = {
            "$gte": float(min_rent)
        }

    if max_rent:
        if "rent" in query:
            query["rent"]["$lte"] = float(max_rent)
        else:
            query["rent"] = {
                "$lte": float(max_rent)
            }

    if bedrooms:
        query["bedrooms"] = int(bedrooms)

    properties = list(
        db.properties.find(query)
    )

    result = []

    for property in properties:

        result.append({
            "property_id": str(property["_id"]),
            "title": property["title"],
            "description": property["description"],
            "property_type": property["property_type"],
            "address": property["address"],
            "city": property["city"],
            "bedrooms": property["bedrooms"],
            "bathrooms": property["bathrooms"],
            "area": property["area"],
            "rent": property["rent"],
            "deposit": property["deposit"],
            "images": property.get("images", []),
            "amenities": property.get("amenities", []),
            "status": property["status"]
        })

    return {
        "message": "Available properties retrieved successfully",
        "properties": result
    }, 200