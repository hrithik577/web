# config.py
import os

class Config:
    SECRET_KEY = 'your-secret-key'  # Change this in production
    SQLALCHEMY_DATABASE_URI = 'sqlite:///printportal.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'xlsx', 'png', 'jpg'}  # Added png and jpg