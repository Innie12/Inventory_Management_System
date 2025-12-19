# create_db.py
"""
Database creation script
Run this first to create all database tables
"""

from app import create_app
from models import db

def create_database():
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created successfully!")
        print("\nNext step: Run 'python seed_data.py' to populate initial data")

if __name__ == "__main__":
    create_database()
