"""
Database seeding script with sample data
Run this after create_db.py
"""

from app import create_app
from models import db, User, Category, Product, Supplier
from datetime import datetime

def seed_database():
    app = create_app()
    
    with app.app_context():
        print("Seeding database with initial data...")
        
        # Check if data already exists
        if User.query.first():
            print("⚠ Database already contains data. Skipping seed...")
            return
        
        # 1. Create Admin User
        print("\n1. Creating users...")
        admin = User(
            username='admin',
            email='admin@inventory.com',
            phone='+639123456789',
            full_name='System Administrator',
            role='admin',
            is_active=True,
            is_verified=True
        )
        admin.set_password('admin123')  # Change this in production!
        db.session.add(admin)
        
        # Create additional users
        manager = User(
            username='manager',
            email='manager@inventory.com',
            phone='+639987654321',
            full_name='Store Manager',
            role='manager',
            is_active=True,
            is_verified=True
        )
        manager.set_password('manager123')
        db.session.add(manager)
        
        user = User(
            username='user',
            email='user@inventory.com',
            phone='+639111222333',
            full_name='Regular User',
            role='user',
            is_active=True,
            is_verified=True
        )
        user.set_password('user123')
        db.session.add(user)
        
        db.session.commit()
        print(f"✓ Created {User.query.count()} users")
        
        # 2. Create Categories
        print("\n2. Creating categories...")
        categories_data = [
            {
                'name': 'Electronics',
                'description': 'Electronic devices and accessories',
                'icon': 'bi-laptop',
                'color': '#007bff'
            },
            {
                'name': 'Office Supplies',
                'description': 'Stationery and office materials',
                'icon': 'bi-pencil',
                'color': '#28a745'
            },
            {
                'name': 'Furniture',
                'description': 'Office and home furniture',
                'icon': 'bi-house',
                'color': '#dc3545'
            },
            {
                'name': 'Food & Beverage',
                'description': 'Food items and drinks',
                'icon': 'bi-cup',
                'color': '#ffc107'
            },
            {
                'name': 'Clothing',
                'description': 'Apparel and accessories',
                'icon': 'bi-bag',
                'color': '#6f42c1'
            }
        ]
        
        categories = []
        for cat_data in categories_data:
            category = Category(**cat_data)
            db.session.add(category)
            categories.append(category)
        
        db.session.commit()
        print(f"✓ Created {Category.query.count()} categories")
        
        # 3. Create Suppliers
        print("\n3. Creating suppliers...")
        suppliers_data = [
            {
                'name': 'Tech Solutions Inc.',
                'contact_person': 'John Smith',
                'email': 'john@techsolutions.com',
                'phone': '+639201234567',
                'address': '123 Tech Street, Makati City',
                'website': 'https://techsolutions.com',
                'credit_limit': 500000.00,
                'rating': 5,
                'is_active': True
            },
            {
                'name': 'Office Depot Philippines',
                'contact_person': 'Maria Santos',
                'email': 'maria@officedepot.ph',
                'phone': '+639309876543',
                'address': '456 Business Ave, BGC',
                'website': 'https://officedepot.ph',
                'credit_limit': 300000.00,
                'rating': 4,
                'is_active': True
            },
            {
                'name': 'Global Furniture Corp',
                'contact_person': 'Robert Lee',
                'email': 'robert@globalfurniture.com',
                'phone': '+639401122334',
                'address': '789 Furniture Road, Quezon City',
                'credit_limit': 750000.00,
                'rating': 5,
                'is_active': True
            }
        ]
        
        suppliers = []
        for sup_data in suppliers_data:
            supplier = Supplier(**sup_data)
            db.session.add(supplier)
            suppliers.append(supplier)
        
        db.session.commit()
        print(f"✓ Created {Supplier.query.count()} suppliers")
        
        # 4. Create Products
        print("\n4. Creating products...")
        products_data = [
            # Electronics
            {
                'sku': 'ELEC-001',
                'barcode': '1234567890123',
                'name': 'Laptop Dell Inspiron 15',
                'description': '15.6" FHD, Intel i5, 8GB RAM, 256GB SSD',
                'category_id': categories[0].id,
                'supplier_id': suppliers[0].id,
                'cost_price': 25000.00,
                'selling_price': 35000.00,
                'quantity': 15,
                'reorder_level': 5,
                'reorder_quantity': 10,
                'weight': 2.5,
                'is_active': True,
                'is_featured': True
            },
            {
                'sku': 'ELEC-002',
                'barcode': '1234567890124',
                'name': 'Wireless Mouse Logitech',
                'description': 'Ergonomic wireless mouse with USB receiver',
                'category_id': categories[0].id,
                'supplier_id': suppliers[0].id,
                'cost_price': 500.00,
                'selling_price': 899.00,
                'quantity': 50,
                'reorder_level': 10,
                'reorder_quantity': 30,
                'weight': 0.1,
                'is_active': True
            },
            {
                'sku': 'ELEC-003',
                'barcode': '1234567890125',
                'name': 'USB Flash Drive 32GB',
                'description': 'High-speed USB 3.0 flash drive',
                'category_id': categories[0].id,
                'supplier_id': suppliers[0].id,
                'cost_price': 250.00,
                'selling_price': 450.00,
                'quantity': 100,
                'reorder_level': 20,
                'reorder_quantity': 50,
                'weight': 0.02,
                'is_active': True
            },
            
            # Office Supplies
            {
                'sku': 'OFF-001',
                'barcode': '2234567890123',
                'name': 'Ballpoint Pen (Box of 12)',
                'description': 'Blue ink, medium point',
                'category_id': categories[1].id,
                'supplier_id': suppliers[1].id,
                'cost_price': 50.00,
                'selling_price': 120.00,
                'quantity': 200,
                'reorder_level': 30,
                'reorder_quantity': 100,
                'weight': 0.15,
                'is_active': True
            },
            {
                'sku': 'OFF-002',
                'barcode': '2234567890124',
                'name': 'A4 Bond Paper (Ream)',
                'description': '500 sheets, 70gsm',
                'category_id': categories[1].id,
                'supplier_id': suppliers[1].id,
                'cost_price': 180.00,
                'selling_price': 250.00,
                'quantity': 80,
                'reorder_level': 15,
                'reorder_quantity': 40,
                'weight': 2.5,
                'is_active': True
            },
            {
                'sku': 'OFF-003',
                'barcode': '2234567890125',
                'name': 'Stapler Heavy Duty',
                'description': 'Metal stapler, 100-sheet capacity',
                'category_id': categories[1].id,
                'supplier_id': suppliers[1].id,
                'cost_price': 350.00,
                'selling_price': 599.00,
                'quantity': 25,
                'reorder_level': 8,
                'reorder_quantity': 20,
                'weight': 0.5,
                'is_active': True
            },
            
            # Furniture
            {
                'sku': 'FURN-001',
                'barcode': '3234567890123',
                'name': 'Office Chair Ergonomic',
                'description': 'Adjustable height, lumbar support, mesh back',
                'category_id': categories[2].id,
                'supplier_id': suppliers[2].id,
                'cost_price': 3500.00,
                'selling_price': 6500.00,
                'quantity': 12,
                'reorder_level': 5,
                'reorder_quantity': 10,
                'weight': 15.0,
                'dimensions': '60x60x110 cm',
                'is_active': True,
                'is_featured': True
            },
            {
                'sku': 'FURN-002',
                'barcode': '3234567890124',
                'name': 'Office Desk L-Shape',
                'description': 'Wooden desk with drawers',
                'category_id': categories[2].id,
                'supplier_id': suppliers[2].id,
                'cost_price': 8000.00,
                'selling_price': 12500.00,
                'quantity': 8,
                'reorder_level': 3,
                'reorder_quantity': 5,
                'weight': 45.0,
                'dimensions': '150x120x75 cm',
                'is_active': True
            },
            
            # Low Stock Items (for testing alerts)
            {
                'sku': 'ELEC-999',
                'barcode': '9999999999999',
                'name': 'HDMI Cable 2m',
                'description': 'High-speed HDMI cable',
                'category_id': categories[0].id,
                'supplier_id': suppliers[0].id,
                'cost_price': 150.00,
                'selling_price': 299.00,
                'quantity': 3,
                'reorder_level': 10,
                'reorder_quantity': 20,
                'weight': 0.2,
                'is_active': True
            },
            {
                'sku': 'OFF-999',
                'barcode': '9999999999998',
                'name': 'Correction Tape',
                'description': 'White correction tape 5mm',
                'category_id': categories[1].id,
                'supplier_id': suppliers[1].id,
                'cost_price': 25.00,
                'selling_price': 45.00,
                'quantity': 2,
                'reorder_level': 15,
                'reorder_quantity': 30,
                'weight': 0.05,
                'is_active': True
            }
        ]
        
        for prod_data in products_data:
            product = Product(**prod_data)
            db.session.add(product)
        
        db.session.commit()
        print(f"✓ Created {Product.query.count()} products")
        
        # Summary
        print("\n" + "="*60)
        print("DATABASE SEEDED SUCCESSFULLY!")
        print("="*60)
        print("\nDefault Login Credentials:")
        print("-" * 60)
        print(f"Admin    - Username: admin    | Password: admin123")
        print(f"Manager  - Username: manager  | Password: manager123")
        print(f"User     - Username: user     | Password: user123")
        print("-" * 60)
        print("\n⚠️  IMPORTANT: Change default passwords in production!")
        print("\nYou can now run the application with: python app.py")
        print("="*60 + "\n")

if __name__ == "__main__":
    seed_database()