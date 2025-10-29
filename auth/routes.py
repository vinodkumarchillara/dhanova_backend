from flask import Blueprint, request, jsonify, session
from utils.db import db
from flask_bcrypt import Bcrypt

auth = Blueprint('auth', __name__)
bcrypt = Bcrypt()

# Use the 'resident' collection inside 'gated_community' database
residents_collection = db["resident"]

# ---------------- REGISTER ----------------
@auth.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    role = data.get("role", "resident")  # default role

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    if residents_collection.find_one({"username": username}):
        return jsonify({"message": "Username already exists"}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

    residents_collection.insert_one({
        "username": username,
        "password": hashed_pw,
        "role": role
    })

    return jsonify({"message": f"User '{username}' registered successfully as {role}!"}), 201


# ---------------- LOGIN ----------------
@auth.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = residents_collection.find_one({"username": username})
    if not user or not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"message": "Invalid username or password"}), 401

    session["user"] = {"username": user["username"], "role": user["role"]}
    return jsonify({"message": f"Welcome {username}!", "role": user["role"]}), 200


# ---------------- LOGOUT ----------------
@auth.route("/logout", methods=["POST"])
def logout():
    session.pop("user", None)
    return jsonify({"message": "Logged out successfully"}), 200


# ---------------- CHECK SESSION ----------------
@auth.route("/check-session", methods=["GET"])
def check_session():
    user = session.get("user")
    if not user:
        return jsonify({"message": "No active session"}), 401
    return jsonify({
        "username": user["username"],
        "role": user["role"],
        "message": "Session active"
    }), 200


# ---------------- ADMIN ONLY: VIEW ALL USERS ----------------
@auth.route("/users", methods=["GET"])
def get_all_users():
    user = session.get("user")
    if not user or user["role"] != "admin":
        return jsonify({"message": "Access denied! Admins only."}), 403

    users = list(residents_collection.find({}, {"_id": 0, "password": 0}))
    return jsonify({"users": users}), 200
