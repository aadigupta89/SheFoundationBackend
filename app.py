import json
import os
import uuid
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DATA_FILE = os.path.join(BASE_DIR, "content_store.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
CORS(app)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "shepower123"


def normalize_item(item):
    item = dict(item)
    item.setdefault("archived", False)
    item["archive_date"] = item.get("archive_date") or None
    return item


def initialize_store():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump({"gallery": [], "work": []}, file, indent=2)


def load_content():
    initialize_store()
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        content = json.load(file)
        for section in ("gallery", "work"):
            content.setdefault(section, [])
            content[section] = [normalize_item(item) for item in content[section]]
        return content


def save_content(content):
    normalized = {"gallery": [], "work": []}
    for section in ("gallery", "work"):
        normalized[section] = [normalize_item(item) for item in (content.get(section) or [])]
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(normalized, file, indent=2)


@app.route("/")
def home():
    return jsonify({
        "message": "ShePower Foundation Backend is Running",
        "status": "success"
    })


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "ShePower Foundation API"
    })


@app.route("/api/organization")
def organization():
    return jsonify({
        "name": "ShePower Foundation",
        "email": "foundationshepower@gmail.com",
        "phone": "+91 8809977171",
        "address": "G-01, Apex Green Apartment, Sector-8, Sonipat, Haryana - 131001",
        "ngo_darpan": "HR/2026/1132915",
        "cin": "U88900HR2026NPL147015",
        "udyam": "UDYAM-HR-18-0072570"
    })


@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return jsonify({
            "message": "Login successful",
            "token": "demo-admin-token"
        }), 200

    return jsonify({
        "message": "Invalid username or password"
    }), 401


@app.route("/api/content")
def get_content():
    content = load_content()
    return jsonify({
        "gallery": content.get("gallery", []),
        "work": content.get("work", [])
    })


@app.route("/api/content/<content_type>/archives")
def get_archived_content(content_type):
    section = (content_type or "gallery").strip().lower()
    if section not in {"gallery", "work"}:
        return jsonify({section: []})

    content = load_content()
    archived_items = [
        normalize_item(item)
        for item in content.get(section, [])
        if item.get("archived")
    ]
    return jsonify({section: archived_items})


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/api/admin/upload", methods=["POST"])
def admin_upload():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token != "demo-admin-token":
        return jsonify({"message": "Unauthorized"}), 401

    title = (request.form.get("title") or "").strip()
    note = (request.form.get("note") or "").strip()
    content_type = (request.form.get("type") or "gallery").strip().lower()
    archive_date = (request.form.get("archive_date") or "").strip()
    image_file = request.files.get("image")

    if not title or not note:
        return jsonify({"message": "Title and notes are required"}), 400

    if image_file is None or image_file.filename == "":
        return jsonify({"message": "Please upload an image"}), 400

    filename = secure_filename(image_file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    image_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    image_file.save(image_path)

    entry = {
        "id": str(uuid.uuid4()),
        "title": title,
        "note": note,
        "image_url": f"http://localhost:5000/uploads/{unique_name}",
        "created_at": datetime.utcnow().isoformat(),
        "archived": False,
        "archive_date": archive_date or None
    }

    content = load_content()
    if content_type == "work":
        content.setdefault("work", []).append(entry)
    else:
        content.setdefault("gallery", []).append(entry)

    save_content(content)

    return jsonify({
        "message": "Upload successful",
        "entry": entry
    }), 201


@app.route("/api/admin/content/<content_type>/<item_id>/archive", methods=["PATCH"])
def archive_content_item(content_type, item_id):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token != "demo-admin-token":
        return jsonify({"message": "Unauthorized"}), 401

    section = (content_type or "gallery").strip().lower()
    if section not in {"gallery", "work"}:
        return jsonify({"message": "Invalid content type"}), 400

    payload = request.get_json(silent=True) or {}
    archived = bool(payload.get("archived", True))
    archive_date = (payload.get("archive_date") or "").strip() or None

    content = load_content()
    items = content.get(section, [])
    item = next((entry for entry in items if entry.get("id") == item_id), None)
    if item is None:
        return jsonify({"message": "Item not found"}), 404

    item["archived"] = archived
    item["archive_date"] = archive_date if archived else None
    save_content(content)

    return jsonify({
        "message": "Item archived" if archived else "Item restored",
        "entry": normalize_item(item)
    }), 200


@app.route("/api/admin/content/<content_type>/<item_id>", methods=["DELETE"])
def delete_content_item(content_type, item_id):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token != "demo-admin-token":
        return jsonify({"message": "Unauthorized"}), 401

    section = (content_type or "gallery").strip().lower()
    if section not in {"gallery", "work"}:
        return jsonify({"message": "Invalid content type"}), 400

    content = load_content()
    items = content.get(section, [])
    filtered_items = [entry for entry in items if entry.get("id") != item_id]
    if len(filtered_items) == len(items):
        return jsonify({"message": "Item not found"}), 404

    content[section] = filtered_items
    save_content(content)

    return jsonify({"message": "Item deleted successfully"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
