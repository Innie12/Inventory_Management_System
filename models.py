from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import phonenumbers

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True,
                         nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # Profile
    full_name = db.Column(db.String(150))
    avatar_url = db.Column(db.String(255))

    # Role & Status
    role = db.Column(db.String(20), default='user')  # admin, manager, user
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)

    # OTP for password reset
    otp_code = db.Column(db.String(6))
    otp_expires = db.Column(db.DateTime)

    # Preferences
    currency = db.Column(db.String(3), default='PHP')
    enable_notifications = db.Column(db.Boolean, default=True)
    enable_email_alerts = db.Column(db.Boolean, default=False)
    enable_sms_alerts = db.Column(db.Boolean, default=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    notifications = db.relationship(
        'Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_otp(self):
        """Generate 6-digit OTP valid for 10 minutes"""
        self.otp_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        self.otp_expires = datetime.utcnow() + timedelta(minutes=10)
        db.session.commit()
        return self.otp_code

    def verify_otp(self, code):
        """Verify OTP code"""
        if not self.otp_code or not self.otp_expires:
            return False
        if datetime.utcnow() > self.otp_expires:
            return False
        return self.otp_code == code

    def clear_otp(self):
        self.otp_code = None
        self.otp_expires = None
        db.session.commit()

    def format_phone(self):
        """Format phone number to E.164 format"""
        try:
            parsed = phonenumbers.parse(self.phone, "PH")
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except:
            return self.phone

    @property
    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f"<User {self.username}>"


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))  # Icon class name
    color = db.Column(db.String(7), default='#007bff')  # Hex color
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    products = db.relationship('Product', backref='category', lazy='dynamic')

    @property
    def product_count(self):
        return self.products.count()

    def __repr__(self):
        return f"<Category {self.name}>"


class Supplier(db.Model):
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    contact_person = db.Column(db.String(150))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    website = db.Column(db.String(255))

    # Financial
    credit_limit = db.Column(db.Numeric(12, 2), default=0)
    outstanding_balance = db.Column(db.Numeric(12, 2), default=0)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    rating = db.Column(db.Integer, default=5)  # 1-5 stars

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    products = db.relationship('Product', backref='supplier', lazy='dynamic')

    def __repr__(self):
        return f"<Supplier {self.name}>"


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(80), unique=True, nullable=False, index=True)
    barcode = db.Column(db.String(100), unique=True, index=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)

    # Categorization
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))

    # Pricing
    cost_price = db.Column(db.Numeric(12, 2), default=0)
    selling_price = db.Column(db.Numeric(12, 2), default=0)
    currency = db.Column(db.String(3), default='PHP')

    # Stock
    quantity = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=5)
    reorder_quantity = db.Column(db.Integer, default=20)

    # Physical attributes
    weight = db.Column(db.Numeric(10, 3))  # in kg
    dimensions = db.Column(db.String(50))  # LxWxH

    # Images
    image_url = db.Column(db.String(255))

    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    transactions = db.relationship('InventoryTransaction', backref='product', lazy='dynamic',
                                   cascade='all, delete-orphan')

    def adjust_stock(self, delta, user_id, reference=None, remarks=None):
        """Adjust stock and create transaction record"""
        old_qty = self.quantity or 0
        self.quantity = old_qty + int(delta)

        txn = InventoryTransaction(
            product_id=self.id,
            user_id=user_id,
            transaction_type='in' if int(delta) >= 0 else 'out',
            quantity=abs(int(delta)),
            quantity_before=old_qty,
            quantity_after=self.quantity,
            reference=reference,
            remarks=remarks
        )

        db.session.add(self)
        db.session.add(txn)

        # Check low stock and create notification
        if self.quantity <= self.reorder_level:
            self._create_low_stock_notification()

        db.session.commit()
        return txn

    def _create_low_stock_notification(self):
        """Create low stock notification for all admin users"""
        admins = User.query.filter_by(role='admin', is_active=True).all()
        for admin in admins:
            notif = Notification(
                user_id=admin.id,
                type='low_stock',
                title='Low Stock Alert',
                message=f'Product "{self.name}" (SKU: {self.sku}) is low on stock. Current: {self.quantity}, Reorder Level: {self.reorder_level}',
                link=f'/products/{self.id}/adjust'
            )
            db.session.add(notif)

    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.cost_price and self.selling_price and self.cost_price > 0:
            return ((self.selling_price - self.cost_price) / self.cost_price) * 100
        return 0

    @property
    def stock_value(self):
        """Calculate total stock value"""
        return float(self.quantity or 0) * float(self.cost_price or 0)

    @property
    def is_low_stock(self):
        return (self.quantity or 0) <= self.reorder_level

    def __repr__(self):
        return f"<Product {self.name}>"


class InventoryTransaction(db.Model):
    __tablename__ = 'inventory_transactions'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey(
        'products.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Transaction details
    transaction_type = db.Column(
        db.String(10), nullable=False)  # in/out/adjust
    quantity = db.Column(db.Integer, nullable=False)
    quantity_before = db.Column(db.Integer, default=0)
    quantity_after = db.Column(db.Integer, default=0)

    # References
    reference = db.Column(db.String(120))
    remarks = db.Column(db.Text)

    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationship
    user = db.relationship('User', backref='transactions')

    def __repr__(self):
        return f"<Transaction {self.transaction_type} {self.quantity}>"


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Notification details
    type = db.Column(db.String(50))  # low_stock, new_product, stock_out, etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255))

    # Status
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime)

    def mark_as_read(self):
        self.is_read = True
        self.read_at = datetime.utcnow()
        db.session.commit()

    def __repr__(self):
        return f"<Notification {self.title}>"


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Action details
    # create, update, delete, login, etc.
    action = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.String(50))  # product, category, user, etc.
    entity_id = db.Column(db.Integer)

    # Details
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))

    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @staticmethod
    def log(user_id, action, entity_type=None, entity_id=None, description=None, ip=None, ua=None):
        """Create audit log entry"""
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            ip_address=ip,
            user_agent=ua
        )
        db.session.add(log)
        db.session.commit()
        return log

    def __repr__(self):
        return f"<AuditLog {self.action}>"
