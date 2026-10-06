import os

from flask import Flask
from flask_cors import CORS

from flask_jwt_extended import (
    JWTManager,
    jwt_required,
    get_jwt_identity,
    get_jwt
)

from config.db import client
from routes.auth_routes import auth_bp
from routes.property_routes import property_bp
from routes.application_routes import application_bp
from routes.tenant_routes import tenant_bp
from routes.rent_routes import rent_bp
from routes.notification_routes import notification_bp

app = Flask(__name__)

# Enable CORS
CORS(app)

# JWT configuration
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
if not app.config["JWT_SECRET_KEY"]:
    raise RuntimeError("JWT_SECRET_KEY must be configured in the environment")

JWTManager(app)

# Register authentication routes
app.register_blueprint(auth_bp)
app.register_blueprint(property_bp)
app.register_blueprint(tenant_bp)
app.register_blueprint(rent_bp)
app.register_blueprint(notification_bp)



# Home route
@app.route("/")
def home():
    return {
        "message": "Rental Management API is running!"
    }


# MongoDB test route
@app.route("/test-db")
def test_db():
    try:
        client.admin.command("ping")

        return {
            "message": "MongoDB connected successfully!"
        }

    except Exception as e:
        return {
            "message": "MongoDB connection failed",
            "error": str(e)
        }, 500


# Protected test route
@app.route("/api/protected")
@jwt_required()
def protected():

    current_user_id = get_jwt_identity()
    claims = get_jwt()

    return {
        "message": "You are authorized!",
        "user_id": current_user_id,
        "role": claims["role"],
        "name": claims["name"]
    }


# Start Flask server
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )