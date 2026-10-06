from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from config.db import db
from bson import ObjectId
from datetime import datetime

application_bp = Blueprint(
    "application",
    __name__,
    url_prefix="/api/applications"
)


# Tenant applies for a property
@application_bp.route("/", methods=["POST"])
@jwt_required()
def apply_for_property():

    claims = get_jwt()

    if claims["role"] != "TENANT":
        return {"message": "Only tenants can apply for properties"}, 403

    tenant_id = get_jwt_identity()

    data = request.get_json()

    property_id = data.get("property_id")

    if not property_id:
        return {"message": "property_id is required"}, 400

    if not ObjectId.is_valid(property_id):
        return {"message": "Invalid property ID"}, 400

    property_data = db.properties.find_one({
        "_id": ObjectId(property_id),
        "status": "AVAILABLE"
    })

    if not property_data:
        return {"message": "Property not available"}, 404

    existing_application = db.rental_applications.find_one({
        "property_id": ObjectId(property_id),
        "tenant_id": ObjectId(tenant_id),
        "status": "PENDING"
    })

    if existing_application:
        return {"message": "You have already applied for this property"}, 400

    application = {
        "property_id": ObjectId(property_id),
        "tenant_id": ObjectId(tenant_id),
        "owner_id": property_data["owner_id"],
        "rent": property_data["rent"],
        "deposit": property_data["deposit"],
        "status": "PENDING",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = db.rental_applications.insert_one(application)

    return {
        "message": "Rental application submitted successfully",
        "application_id": str(result.inserted_id)
    }, 201


# Owner views rental applications
@application_bp.route("/owner", methods=["GET"])
@jwt_required()
def get_owner_applications():

    claims = get_jwt()

    if claims["role"] != "OWNER":
        return {"message": "Only owners can view applications"}, 403

    owner_id = get_jwt_identity()
    applications = list(
        db.rental_applications.find({
            "owner_id": owner_id
        }).sort("created_at", -1)
    )

    result = []

    for application in applications:
        result.append({
            "application_id": str(application["_id"]),
            "property_id": str(application["property_id"]),
            "tenant_id": str(application["tenant_id"]),
            "rent": application["rent"],
            "deposit": application["deposit"],
            "status": application["status"],
            "created_at": application["created_at"].isoformat(),
            "updated_at": application["updated_at"].isoformat()
        })

    return {
        "message": "Applications retrieved successfully",
        "applications": result
    }, 200


# Owner approves rental application
@application_bp.route("/<application_id>/approve", methods=["PUT"])
@jwt_required()
def approve_application(application_id):

    claims = get_jwt()

    if claims["role"] != "OWNER":
        return {"message": "Only owners can approve applications"}, 403

    owner_id = get_jwt_identity()

    if not ObjectId.is_valid(application_id):
        return {"message": "Invalid application ID"}, 400

    application = db.rental_applications.find_one({
        "_id": ObjectId(application_id),
        "owner_id": owner_id,
        "status": "PENDING"
    })

    if not application:
        return {"message": "Pending application not found"}, 404

    db.rental_applications.update_one(
        {"_id": ObjectId(application_id)},
        {
            "$set": {
                "status": "APPROVED",
                "updated_at": datetime.utcnow()
            }
        }
    )

    db.properties.update_one(
        {"_id": application["property_id"]},
        {
            "$set": {
                "status": "RENTED",
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "message": "Rental application approved successfully"
    }, 200