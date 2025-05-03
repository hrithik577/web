# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    color_price = db.Column(db.Float, nullable=False)  # Price per page for color printing
    bw_price = db.Column(db.Float, nullable=False)  # Price per page for B&W printing
    files = db.relationship('FileRequest', backref='shop', lazy=True)
    users = db.relationship('User', backref='shop', lazy=True)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class FileRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    copies = db.Column(db.Integer, nullable=False)
    color = db.Column(db.Boolean, nullable=False)
    duplex = db.Column(db.Boolean, nullable=False)
    notes = db.Column(db.Text, nullable=True)  # Customer notes
    total_price = db.Column(db.Float, nullable=False)  # Total price for the request
    status = db.Column(db.String(20), default='pending')  # pending, printed, rejected
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # Timestamp
    num_pages = db.Column(db.Integer, nullable=False, default=1)  # Number of pages in the file
    scheduled_at = db.Column(db.DateTime, nullable=True)  # Scheduled date and time for printing
    queue_number = db.Column(db.String(2), nullable=False)  # Two-digit queue number
    request_group_id = db.Column(db.String(36), nullable=False)  # UUID to group files from the same request
    bill_generated = db.Column(db.Boolean, default=False)  # Flag to indicate if bill is generated