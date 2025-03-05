from flask import Flask, request, jsonify
from .database import init_db, get_db, Item, User
from sqlalchemy.orm import Session
from datetime import timedelta
from .auth import authenticate_user, create_access_token, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES

app = Flask(__name__)

# Initialize database
init_db()

# Get database session
def get_session():
    for db in get_db():
        return db

# Authentication routes
@app.route("/api/register", methods=["POST"])
def register_user():
    data = request.json
    db = get_session()
    
    # Check if user exists
    existing_user = db.query(User).filter(
        (User.email == data["email"]) | (User.username == data["username"])
    ).first()
    
    if existing_user:
        return jsonify({"error": "Kullanıcı zaten kayıtlı"}), 400
    
    # Create new user
    hashed_password = get_password_hash(data["password"])
    db_user = User(
        email=data["email"],
        username=data["username"],
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return jsonify({"message": "Kullanıcı başarıyla oluşturuldu"})

@app.route("/api/login", methods=["POST"])
def login_for_access_token():
    data = request.json
    db = get_session()
    
    user = authenticate_user(db, data["username"], data["password"])
    if not user:
        return jsonify({"error": "Geçersiz kullanıcı adı veya şifre"}), 401
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return jsonify({"access_token": access_token, "token_type": "bearer", "username": user.username})

# Routes
@app.route("/api/items", methods=["GET"])
def get_items():
    db = get_session()
    items = db.query(Item).all()
    return jsonify([{"id": item.id, "name": item.name, "description": item.description} for item in items])

@app.route("/api/items", methods=["POST"])
def create_item():
    data = request.json
    db = get_session()
    item = Item(name=data["name"], description=data.get("description", ""))
    db.add(item)
    db.commit()
    db.refresh(item)
    return jsonify({"id": item.id, "name": item.name, "description": item.description})

@app.route("/api/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    db = get_session()
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        return jsonify({"error": "Item not found"}), 404
    return jsonify({"id": item.id, "name": item.name, "description": item.description})

if __name__ == "__main__":
    app.run(debug=True) 