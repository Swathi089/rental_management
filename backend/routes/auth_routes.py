from flask import Blueprint, request
from config.db import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

    if not name or not email or not password or not role:
        return {
            "message": "All fields are required"
        }, 400

    role = role.upper()

    if role not in ["OWNER", "TENANT", "ADMIN"]:
        return {
            "message": "Invalid role"
        }, 400

    existing_user = db.users.find_one({
        "email": email
    })

    if existing_user:
        return {
            "message": "Email already registered"
        }, 409

    hashed_password = generate_password_hash(password)

    user = {
        "name": name,
        "email": email,
        "password": hashed_password,
        "role": role
    }

    result = db.users.insert_one(user)

    return {
        "message": "User registered successfully",
        "user_id": str(result.inserted_id),
        "role": role
    }, 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return {
            "message": "Email and password are required"
        }, 400

    user = db.users.find_one({
        "email": email
    })

    if not user:
        return {
            "message": "Invalid email or password"
        }, 401

    if not check_password_hash(user["password"], password):
        return {
            "message": "Invalid email or password"
        }, 401

    access_token = create_access_token(
        identity=str(user["_id"]),
        additional_claims={
            "role": user["role"],
            "name": user["name"]
        }
    )

    return {
        "message": "Login successful",
        "access_token": access_token,
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }, 200