from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, \
    send_from_directory, abort, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from config import Config
from models import db, User, Category, Product, InventoryTransaction, Notification, \
    AuditLog, Supplier
from forms import *
from nlp_utils import SimpleNLP
from sms_service import get_sms_service
from report_generator import ReportGenerator
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import or_, and_, func, desc
import pandas as pd
import os
import json
from sqlalchemy import or_, and_, func, desc, case


# LoginUser wrapper


class LoginUser(UserMixin):
    def __init__(self, user):
        self.id = user.id
        self.username = user.username
        self.role = user.role
        self._user = user

    def is_active(self):
        return self._user.is_active

    @property
    def is_admin(self):
        return self.role == 'admin'


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure directories exist
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.config['REPORTS_FOLDER']).mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    # Initialize services
    sms_service = get_sms_service()
    report_gen = ReportGenerator(app.config)

    # Flask-Login setup
    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        u = User.query.get(int(user_id))
        if u:
            return LoginUser(u)
        return None

    # Context processor
    @app.context_processor
    def inject_globals():
        unread_count = 0
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(
                user_id=current_user.id,
                is_read=False
            ).count()

        return dict(
            current_user=current_user,
            unread_notifications=unread_count,
            now=datetime.utcnow()
        )

    # Helper function for audit logging
    def log_action(action, entity_type=None, entity_id=None, description=None):
        if current_user.is_authenticated:
            AuditLog.log(
                user_id=current_user.id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                description=description,
                ip=request.remote_addr,
                ua=request.user_agent.string[:255]
            )

    # ==================== AUTHENTICATION ROUTES ====================

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        form = RegistrationForm()

        if form.validate_on_submit():
            # Format phone number
            phone = form.phone.data
            if not phone.startswith('+'):
                if phone.startswith('0'):
                    phone = '+63' + phone[1:]
                else:
                    phone = '+63' + phone

            user = User(
                username=form.username.data,
                email=form.email.data,
                phone=phone,
                full_name=form.full_name.data,
                role='user',
                is_active=True
            )
            user.set_password(form.password.data)

            db.session.add(user)
            db.session.commit()

            log_action('register', 'user', user.id,
                       f'New user registered: {user.username}')

            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))

        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        form = LoginForm()

        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()

            if user and user.check_password(form.password.data):
                if not user.is_active:
                    flash(
                        'Your account has been deactivated. Please contact admin.', 'danger')
                    return redirect(url_for('login'))

                # Update last login
                user.last_login = datetime.utcnow()
                db.session.commit()

                # Log in user
                login_user(LoginUser(user), remember=form.remember_me.data)

                log_action('login', 'user', user.id, 'User logged in')

                flash(
                    f'Welcome back, {user.full_name or user.username}!', 'success')

                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))

            flash('Invalid username or password', 'danger')

        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        log_action('logout', 'user', current_user.id, 'User logged out')
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('login'))

    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        form = ForgotPasswordForm()

        if form.validate_on_submit():
            phone = form.phone.data

            # Format phone number
            if not phone.startswith('+'):
                if phone.startswith('0'):
                    phone = '+63' + phone[1:]
                else:
                    phone = '+63' + phone

            user = User.query.filter_by(phone=phone).first()

            if user:
                # Generate and send OTP
                otp = user.generate_otp()
                result = sms_service.send_otp(user.format_phone(), otp)

                if result.get('success'):
                    session['reset_user_id'] = user.id
                    flash('Verification code sent to your phone!', 'success')
                    return redirect(url_for('verify_otp'))
                else:
                    flash('Failed to send OTP. Please try again.', 'danger')
            else:
                # Don't reveal if phone exists
                flash(
                    'If this phone number is registered, you will receive an OTP.', 'info')

        return render_template('forgot_password.html', form=form)

    @app.route('/verify-otp', methods=['GET', 'POST'])
    def verify_otp():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if 'reset_user_id' not in session:
            flash('Invalid request. Please start password reset again.', 'warning')
            return redirect(url_for('forgot_password'))

        form = VerifyOTPForm()

        if form.validate_on_submit():
            user = User.query.get(session['reset_user_id'])

            if user and user.verify_otp(form.otp_code.data):
                session['otp_verified'] = True
                flash('Code verified! Please set your new password.', 'success')
                return redirect(url_for('reset_password'))
            else:
                flash('Invalid or expired code. Please try again.', 'danger')

        return render_template('verify_otp.html', form=form)

    @app.route('/reset-password', methods=['GET', 'POST'])
    def reset_password():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if not session.get('otp_verified') or 'reset_user_id' not in session:
            flash('Invalid request. Please verify OTP first.', 'warning')
            return redirect(url_for('forgot_password'))

        form = ResetPasswordForm()

        if form.validate_on_submit():
            user = User.query.get(session['reset_user_id'])

            if user:
                user.set_password(form.password.data)
                user.clear_otp()
                db.session.commit()

                # Clear session
                session.pop('reset_user_id', None)
                session.pop('otp_verified', None)

                log_action('password_reset', 'user',
                           user.id, 'Password reset via OTP')

                flash('Password reset successful! You can now log in.', 'success')
                return redirect(url_for('login'))

        return render_template('reset_password.html', form=form)

    # ==================== DASHBOARD ====================

    @app.route('/')
    @login_required
    def dashboard():
        # Statistics
        total_products = Product.query.filter_by(is_active=True).count()
        total_categories = Category.query.filter_by(is_active=True).count()
        total_suppliers = Supplier.query.filter_by(is_active=True).count()
        low_stock_count = Product.query.filter(
            Product.quantity <= Product.reorder_level,
            Product.is_active == True
        ).count()

        # Total inventory value
        products = Product.query.filter_by(is_active=True).all()
        total_value = sum(
            float(p.cost_price or 0) * (p.quantity or 0)
            for p in products
        )

        # Monthly transaction data (last 6 months)
        six_months_ago = datetime.utcnow() - timedelta(days=180)

        monthly_data = db.session.query(
            func.strftime(
                '%Y-%m', InventoryTransaction.created_at).label('month'),
            func.sum(
                case(
                    (InventoryTransaction.transaction_type == 'in',
                     InventoryTransaction.quantity),
                    else_=0
                )
            ).label('stock_in'),
            func.sum(
                case(
                    (InventoryTransaction.transaction_type == 'out',
                     InventoryTransaction.quantity),
                    else_=0
                )
            ).label('stock_out')
        ).filter(
            InventoryTransaction.created_at >= six_months_ago
        ).group_by('month').order_by('month').all()

        months = [row.month for row in monthly_data]
        stock_in = [int(row.stock_in or 0) for row in monthly_data]
        stock_out = [int(row.stock_out or 0) for row in monthly_data]

        # Top 5 low stock items
        low_stock_items = Product.query.filter(
            Product.is_active == True
        ).order_by(Product.quantity.asc()).limit(5).all()

        # Recent transactions
        recent_transactions = InventoryTransaction.query.order_by(
            InventoryTransaction.created_at.desc()
        ).limit(10).all()

        # Category distribution
        category_stats = db.session.query(
            Category.name,
            func.count(Product.id).label('count')
        ).join(Product).filter(
            Product.is_active == True
        ).group_by(Category.id).all()

        category_names = [stat.name for stat in category_stats]
        category_counts = [stat.count for stat in category_stats]

        return render_template(
            'dashboard.html',
            total_products=total_products,
            total_categories=total_categories,
            total_suppliers=total_suppliers,
            low_stock_count=low_stock_count,
            total_value=total_value,
            months=json.dumps(months),
            stock_in=json.dumps(stock_in),
            stock_out=json.dumps(stock_out),
            low_stock_items=low_stock_items,
            recent_transactions=recent_transactions,
            category_names=json.dumps(category_names),
            category_counts=json.dumps(category_counts)
        )

    # ==================== PRODUCTS ====================

    @app.route('/products')
    @login_required
    def products():
        page = request.args.get('page', 1, type=int)
        q = request.args.get('q', '').strip()
        category_id = request.args.get('category', 0, type=int)
        supplier_id = request.args.get('supplier', 0, type=int)
        stock_status = request.args.get('stock_status', '')
        sort_by = request.args.get('sort_by', 'newest')

        # Base query
        query = Product.query.filter_by(is_active=True)

        # Search filter
        if q:
            like_pattern = f"%{q}%"
            query = query.filter(
                or_(
                    Product.name.ilike(like_pattern),
                    Product.sku.ilike(like_pattern),
                    Product.barcode.ilike(like_pattern),
                    Product.description.ilike(like_pattern)
                )
            )

        # Category filter
        if category_id > 0:
            query = query.filter_by(category_id=category_id)

        # Supplier filter
        if supplier_id > 0:
            query = query.filter_by(supplier_id=supplier_id)

        # Stock status filter
        if stock_status == 'in_stock':
            query = query.filter(Product.quantity > Product.reorder_level)
        elif stock_status == 'low_stock':
            query = query.filter(
                Product.quantity <= Product.reorder_level,
                Product.quantity > 0
            )
        elif stock_status == 'out_of_stock':
            query = query.filter(Product.quantity == 0)

        # Sorting
        if sort_by == 'name_asc':
            query = query.order_by(Product.name.asc())
        elif sort_by == 'name_desc':
            query = query.order_by(Product.name.desc())
        elif sort_by == 'quantity_asc':
            query = query.order_by(Product.quantity.asc())
        elif sort_by == 'quantity_desc':
            query = query.order_by(Product.quantity.desc())
        elif sort_by == 'price_asc':
            query = query.order_by(Product.selling_price.asc())
        elif sort_by == 'price_desc':
            query = query.order_by(Product.selling_price.desc())
        elif sort_by == 'oldest':
            query = query.order_by(Product.created_at.asc())
        else:  # newest
            query = query.order_by(Product.created_at.desc())

        # Pagination
        pagination = query.paginate(
            page=page,
            per_page=Config.ITEMS_PER_PAGE,
            error_out=False
        )

        # NLP fallback if no results
        if pagination.total == 0 and q:
            all_products = Product.query.filter_by(is_active=True).all()
            docs = [f"{p.name} {p.description or ''}" for p in all_products]
            nlp = SimpleNLP(docs)
            matches = nlp.query(q, top_k=30)

            if matches:
                product_ids = [all_products[i].id for (_, _, i) in matches]
                query = Product.query.filter(Product.id.in_(product_ids))
                pagination = query.paginate(
                    page=page,
                    per_page=Config.ITEMS_PER_PAGE,
                    error_out=False
                )

        # Get categories and suppliers for filters
        categories = Category.query.filter_by(
            is_active=True).order_by(Category.name).all()
        suppliers = Supplier.query.filter_by(
            is_active=True).order_by(Supplier.name).all()

        return render_template('products.html',
                               pagination=pagination,
                               q=q,
                               category_id=category_id,
                               supplier_id=supplier_id,
                               stock_status=stock_status,
                               sort_by=sort_by,
                               categories=categories,
                               suppliers=suppliers
                               )

    @app.route('/products/new', methods=['GET', 'POST'])
    @login_required
    def product_new():
        form = ProductForm()

        # Setup choices
        categories = Category.query.filter_by(
            is_active=True).order_by(Category.name).all()
        suppliers = Supplier.query.filter_by(
            is_active=True).order_by(Supplier.name).all()
        form.category_id.choices = [
            (0, '--- Select Category ---')] + [(c.id, c.name) for c in categories]
        form.supplier_id.choices = [
            (0, '--- Select Supplier ---')] + [(s.id, s.name) for s in suppliers]

        if form.validate_on_submit():
            product = Product(
                sku=form.sku.data,
                name=form.name.data,
                description=form.description.data,
                barcode=form.barcode.data,
                category_id=form.category_id.data if form.category_id.data > 0 else None,
                supplier_id=form.supplier_id.data if form.supplier_id.data > 0 else None,
                cost_price=form.cost_price.data or 0,
                selling_price=form.selling_price.data or 0,
                currency=form.currency.data,
                quantity=form.quantity.data or 0,
                reorder_level=form.reorder_level.data or 5,
                reorder_quantity=form.reorder_quantity.data or 20,
                weight=form.weight.data,
                dimensions=form.dimensions.data,
                is_active=form.is_active.data,
                is_featured=form.is_featured.data
            )

            db.session.add(product)
            db.session.commit()

            # NLP category suggestion if not assigned
            if not product.category_id and categories:
                cats_map = {c.id: c.name for c in categories}
                nlp = SimpleNLP()
                suggested_cat_id, score = nlp.suggest_category(
                    f"{product.name} {product.description or ''}",
                    cats_map
                )

                if suggested_cat_id and score > 0.15:
                    flash(
                        f'💡 Suggested category: {cats_map[suggested_cat_id]} (confidence: {score:.0%})', 'info')

            log_action('create', 'product', product.id,
                       f'Created product: {product.name}')

            flash('Product created successfully!', 'success')
            return redirect(url_for('products'))

        return render_template('product_form.html', form=form, action='Create', product=None)

    @app.route('/products/<int:pid>/edit', methods=['GET', 'POST'])
    @login_required
    def product_edit(pid):
        product = Product.query.get_or_404(pid)
        form = ProductForm(obj=product)
        form.product_id = pid

        # Setup choices
        categories = Category.query.filter_by(
            is_active=True).order_by(Category.name).all()
        suppliers = Supplier.query.filter_by(
            is_active=True).order_by(Supplier.name).all()
        form.category_id.choices = [
            (0, '--- Select Category ---')] + [(c.id, c.name) for c in categories]
        form.supplier_id.choices = [
            (0, '--- Select Supplier ---')] + [(s.id, s.name) for s in suppliers]

        if request.method == 'GET':
            form.category_id.data = product.category_id or 0
            form.supplier_id.data = product.supplier_id or 0

        if form.validate_on_submit():
            product.sku = form.sku.data
            product.name = form.name.data
            product.description = form.description.data
            product.barcode = form.barcode.data
            product.category_id = form.category_id.data if form.category_id.data > 0 else None
            product.supplier_id = form.supplier_id.data if form.supplier_id.data > 0 else None
            product.cost_price = form.cost_price.data or 0
            product.selling_price = form.selling_price.data or 0
            product.currency = form.currency.data
            product.reorder_level = form.reorder_level.data or 5
            product.reorder_quantity = form.reorder_quantity.data or 20
            product.weight = form.weight.data
            product.dimensions = form.dimensions.data
            product.is_active = form.is_active.data
            product.is_featured = form.is_featured.data

            db.session.commit()

            log_action('update', 'product', product.id,
                       f'Updated product: {product.name}')

            flash('Product updated successfully!', 'success')
            return redirect(url_for('products'))

        return render_template('product_form.html', form=form, action='Edit', product=product)

    @app.route('/products/<int:pid>/adjust', methods=['GET', 'POST'])
    @login_required
    def product_adjust(pid):
        product = Product.query.get_or_404(pid)
        form = StockAdjustForm()

        if form.validate_on_submit():
            adjustment_type = form.adjustment_type.data
            delta = form.delta.data

            # Convert to positive/negative based on type
            if adjustment_type == 'out':
                delta = -abs(delta)
            elif adjustment_type == 'in':
                delta = abs(delta)

            product.adjust_stock(
                delta=delta,
                user_id=current_user.id,
                reference=form.reference.data,
                remarks=form.remarks.data
            )

            log_action('adjust_stock', 'product', product.id,
                       f'Adjusted stock by {delta}: {product.name}')

            flash(
                f'Stock adjusted! New quantity: {product.quantity}', 'success')
            return redirect(url_for('products'))

        # Get recent transactions
        recent_txns = InventoryTransaction.query.filter_by(
            product_id=pid
        ).order_by(InventoryTransaction.created_at.desc()).limit(10).all()

        return render_template('product_adjust.html',
                               product=product,
                               form=form,
                               recent_txns=recent_txns)

    @app.route('/products/<int:pid>/delete', methods=['POST'])
    @login_required
    def product_delete(pid):
        if not current_user.is_admin:
            flash('Only admins can delete products.', 'danger')
            return redirect(url_for('products'))

        product = Product.query.get_or_404(pid)
        product_name = product.name

        # Soft delete (set inactive)
        product.is_active = False
        db.session.commit()

        log_action('delete', 'product', product.id,
                   f'Deleted product: {product_name}')

        flash(f'Product "{product_name}" deleted.', 'warning')
        return redirect(url_for('products'))

    # ==================== CATEGORIES ====================

    @app.route('/categories')
    @login_required
    def categories():
        page = request.args.get('page', 1, type=int)
        q = request.args.get('q', '').strip()

        query = Category.query.filter_by(is_active=True)

        if q:
            like_pattern = f"%{q}%"
            query = query.filter(
                or_(
                    Category.name.ilike(like_pattern),
                    Category.description.ilike(like_pattern)
                )
            )

        pagination = query.order_by(Category.name).paginate(
            page=page,
            per_page=20,
            error_out=False
        )

        return render_template('categories.html', pagination=pagination, q=q)

    @app.route('/categories/new', methods=['GET', 'POST'])
    @login_required
    def category_new():
        form = CategoryForm()

        if form.validate_on_submit():
            category = Category(
                name=form.name.data,
                description=form.description.data,
                icon=form.icon.data or 'bi-box',
                color=form.color.data or '#007bff'
            )

            db.session.add(category)
            db.session.commit()

            log_action('create', 'category', category.id,
                       f'Created category: {category.name}')

            flash('Category created successfully!', 'success')
            return redirect(url_for('categories'))

        return render_template('category_form.html', form=form, action='Create')

    @app.route('/categories/<int:cid>/edit', methods=['GET', 'POST'])
    @login_required
    def category_edit(cid):
        category = Category.query.get_or_404(cid)
        form = CategoryForm(obj=category)

        if form.validate_on_submit():
            category.name = form.name.data
            category.description = form.description.data
            category.icon = form.icon.data or 'bi-box'
            category.color = form.color.data or '#007bff'

            db.session.commit()

            log_action('update', 'category', category.id,
                       f'Updated category: {category.name}')

            flash('Category updated successfully!', 'success')
            return redirect(url_for('categories'))

        return render_template('category_form.html', form=form, action='Edit', category=category)

    @app.route('/categories/<int:cid>/delete', methods=['POST'])
    @login_required
    def category_delete(cid):
        if not current_user.is_admin:
            flash('Only admins can delete categories.', 'danger')
            return redirect(url_for('categories'))

        category = Category.query.get_or_404(cid)

        # Check if has products
        if category.products.filter_by(is_active=True).count() > 0:
            flash(
                'Cannot delete category with active products. Reassign or delete products first.', 'danger')
            return redirect(url_for('categories'))

        category_name = category.name
        category.is_active = False
        db.session.commit()

        log_action('delete', 'category', category.id,
                   f'Deleted category: {category_name}')

        flash(f'Category "{category_name}" deleted.', 'warning')
        return redirect(url_for('categories'))

    # ==================== SUPPLIERS ====================

    @app.route('/suppliers')
    @login_required
    def suppliers():
        page = request.args.get('page', 1, type=int)
        q = request.args.get('q', '').strip()

        query = Supplier.query.filter_by(is_active=True)

        if q:
            like_pattern = f"%{q}%"
            query = query.filter(
                or_(
                    Supplier.name.ilike(like_pattern),
                    Supplier.contact_person.ilike(like_pattern),
                    Supplier.email.ilike(like_pattern)
                )
            )

        pagination = query.order_by(Supplier.name).paginate(
            page=page,
            per_page=15,
            error_out=False
        )

        return render_template('suppliers.html', pagination=pagination, q=q)

    @app.route('/suppliers/new', methods=['GET', 'POST'])
    @login_required
    def supplier_new():
        form = SupplierForm()

        if form.validate_on_submit():
            supplier = Supplier(
                name=form.name.data,
                contact_person=form.contact_person.data,
                email=form.email.data,
                phone=form.phone.data,
                address=form.address.data,
                website=form.website.data,
                credit_limit=form.credit_limit.data or 0,
                rating=form.rating.data or 5,
                is_active=form.is_active.data
            )

            db.session.add(supplier)
            db.session.commit()

            log_action('create', 'supplier', supplier.id,
                       f'Created supplier: {supplier.name}')

            flash('Supplier created successfully!', 'success')
            return redirect(url_for('suppliers'))

        return render_template('supplier_form.html', form=form, action='Create')

    @app.route('/suppliers/<int:sid>/edit', methods=['GET', 'POST'])
    @login_required
    def supplier_edit(sid):
        supplier = Supplier.query.get_or_404(sid)
        form = SupplierForm(obj=supplier)

        if form.validate_on_submit():
            supplier.name = form.name.data
            supplier.contact_person = form.contact_person.data
            supplier.email = form.email.data
            supplier.phone = form.phone.data
            supplier.address = form.address.data
            supplier.website = form.website.data
            supplier.credit_limit = form.credit_limit.data or 0
            supplier.rating = form.rating.data or 5
            supplier.is_active = form.is_active.data

            db.session.commit()

            log_action('update', 'supplier', supplier.id,
                       f'Updated supplier: {supplier.name}')

            flash('Supplier updated successfully!', 'success')
            return redirect(url_for('suppliers'))

        return render_template('supplier_form.html', form=form, action='Edit', supplier=supplier)

    @app.route('/suppliers/<int:sid>/delete', methods=['POST'])
    @login_required
    def supplier_delete(sid):
        if not current_user.is_admin:
            flash('Only admins can delete suppliers.', 'danger')
            return redirect(url_for('suppliers'))

        supplier = Supplier.query.get_or_404(sid)

        # Check if has products
        if supplier.products.filter_by(is_active=True).count() > 0:
            flash(
                'Cannot delete supplier with active products. Reassign or delete products first.', 'danger')
            return redirect(url_for('suppliers'))

        supplier_name = supplier.name
        supplier.is_active = False
        db.session.commit()

        log_action('delete', 'supplier', supplier.id,
                   f'Deleted supplier: {supplier_name}')

        flash(f'Supplier "{supplier_name}" deleted.', 'warning')
        return redirect(url_for('suppliers'))

    # ==================== USER SETTINGS ====================

    @app.route('/settings', methods=['GET', 'POST'])
    @login_required
    def settings():
        user = User.query.get(current_user.id)
        form = UserSettingsForm(obj=user)
        password_form = ChangePasswordForm()

        if form.validate_on_submit() and 'settings_submit' in request.form:
            user.full_name = form.full_name.data
            user.email = form.email.data
            user.phone = form.phone.data
            user.currency = form.currency.data
            user.enable_notifications = form.enable_notifications.data
            user.enable_email_alerts = form.enable_email_alerts.data
            user.enable_sms_alerts = form.enable_sms_alerts.data

            db.session.commit()

            log_action('update', 'user', user.id, 'Updated user settings')

            flash('Settings updated successfully!', 'success')
            return redirect(url_for('settings'))

        if password_form.validate_on_submit() and 'password_submit' in request.form:
            if user.check_password(password_form.current_password.data):
                user.set_password(password_form.new_password.data)
                db.session.commit()

                log_action('change_password', 'user',
                           user.id, 'Changed password')

                flash('Password changed successfully!', 'success')
                return redirect(url_for('settings'))
            else:
                flash('Current password is incorrect.', 'danger')

        return render_template('settings.html', form=form, password_form=password_form, user=user)

    # ==================== NOTIFICATIONS ====================

    @app.route('/notifications')
    @login_required
    def notifications():
        page = request.args.get('page', 1, type=int)

        pagination = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(Notification.created_at.desc()).paginate(
            page=page,
            per_page=20,
            error_out=False
        )

        return render_template('notifications.html', pagination=pagination)

    @app.route('/notifications/<int:nid>/read', methods=['POST'])
    @login_required
    def notification_read(nid):
        notification = Notification.query.get_or_404(nid)

        if notification.user_id != current_user.id:
            abort(403)

        notification.mark_as_read()

        return jsonify({'success': True})

    @app.route('/notifications/read-all', methods=['POST'])
    @login_required
    def notifications_read_all():
        Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).update({'is_read': True, 'read_at': datetime.utcnow()})

        db.session.commit()

        flash('All notifications marked as read.', 'success')
        return redirect(url_for('notifications'))

    # Continue to Part 4...
# ==================== AUDIT LOGS ====================

    @app.route('/audit-logs')
    @login_required
    def audit_logs():
        if not current_user.is_admin:
            flash('Access denied. Admin only.', 'danger')
            return redirect(url_for('dashboard'))

        page = request.args.get('page', 1, type=int)
        action = request.args.get('action', '')
        entity_type = request.args.get('entity_type', '')

        query = AuditLog.query

        if action:
            query = query.filter_by(action=action)

        if entity_type:
            query = query.filter_by(entity_type=entity_type)

        pagination = query.order_by(AuditLog.created_at.desc()).paginate(
            page=page,
            per_page=50,
            error_out=False
        )

        # Get unique actions and entity types for filters
        actions = db.session.query(AuditLog.action).distinct().all()
        entity_types = db.session.query(AuditLog.entity_type).distinct().all()

        return render_template('audit_logs.html',
                               pagination=pagination,
                               actions=[a[0] for a in actions if a[0]],
                               entity_types=[e[0]
                                             for e in entity_types if e[0]],
                               selected_action=action,
                               selected_entity_type=entity_type)

    # ==================== USERS MANAGEMENT ====================

    @app.route('/users')
    @login_required
    def users():
        if not current_user.is_admin:
            flash('Access denied. Admin only.', 'danger')
            return redirect(url_for('dashboard'))

        page = request.args.get('page', 1, type=int)
        q = request.args.get('q', '').strip()
        role_filter = request.args.get('role', '')

        query = User.query

        if q:
            like_pattern = f"%{q}%"
            query = query.filter(
                or_(
                    User.username.ilike(like_pattern),
                    User.email.ilike(like_pattern),
                    User.full_name.ilike(like_pattern)
                )
            )

        if role_filter:
            query = query.filter_by(role=role_filter)

        pagination = query.order_by(User.created_at.desc()).paginate(
            page=page,
            per_page=20,
            error_out=False
        )

        return render_template('users.html', pagination=pagination, q=q, role_filter=role_filter)

    @app.route('/users/<int:uid>/edit', methods=['GET', 'POST'])
    @login_required
    def user_edit(uid):
        if not current_user.is_admin:
            flash('Access denied. Admin only.', 'danger')
            return redirect(url_for('dashboard'))

        user = User.query.get_or_404(uid)
        form = UserForm(obj=user)
        form.user_id = uid

        if form.validate_on_submit():
            user.username = form.username.data
            user.email = form.email.data
            user.phone = form.phone.data
            user.full_name = form.full_name.data
            user.role = form.role.data
            user.is_active = form.is_active.data

            db.session.commit()

            log_action('update', 'user', user.id,
                       f'Updated user: {user.username}')

            flash('User updated successfully!', 'success')
            return redirect(url_for('users'))

        return render_template('user_form.html', form=form, user=user)

    @app.route('/users/<int:uid>/toggle-active', methods=['POST'])
    @login_required
    def user_toggle_active(uid):
        if not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        user = User.query.get_or_404(uid)

        if user.id == current_user.id:
            return jsonify({'success': False, 'error': 'Cannot deactivate yourself'}), 400

        user.is_active = not user.is_active
        db.session.commit()

        status = 'activated' if user.is_active else 'deactivated'
        log_action('toggle_active', 'user', user.id,
                   f'User {status}: {user.username}')

        return jsonify({'success': True, 'is_active': user.is_active})

    # ==================== REPORTS ====================

    @app.route('/reports')
    @login_required
    def reports():
        form = ReportForm()

        # Setup choices
        categories = Category.query.filter_by(
            is_active=True).order_by(Category.name).all()
        suppliers = Supplier.query.filter_by(
            is_active=True).order_by(Supplier.name).all()

        form.category_id.choices = [
            (0, '--- All Categories ---')] + [(c.id, c.name) for c in categories]
        form.supplier_id.choices = [
            (0, '--- All Suppliers ---')] + [(s.id, s.name) for s in suppliers]

        return render_template('reports.html', form=form)

    @app.route('/reports/generate', methods=['POST'])
    @login_required
    def generate_report():
        report_type = request.form.get('report_type')
        format_type = request.form.get('format', 'pdf')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        try:
            if report_type == 'inventory':
                products = Product.query.filter_by(
                    is_active=True).order_by(Product.name).all()

                if format_type == 'pdf':
                    filename = f'inventory_report_{timestamp}.pdf'
                    filepath = Path(app.config['REPORTS_FOLDER']) / filename
                    report_gen.generate_inventory_report(
                        products, str(filepath))

                    return send_from_directory(
                        app.config['REPORTS_FOLDER'],
                        filename,
                        as_attachment=True
                    )

                elif format_type == 'excel':
                    df = pd.DataFrame([{
                        'SKU': p.sku,
                        'Barcode': p.barcode or '',
                        'Name': p.name,
                        'Category': p.category.name if p.category else '',
                        'Supplier': p.supplier.name if p.supplier else '',
                        'Quantity': p.quantity,
                        'Cost Price': float(p.cost_price or 0),
                        'Selling Price': float(p.selling_price or 0),
                        'Currency': p.currency,
                        'Reorder Level': p.reorder_level,
                        'Stock Value': float(p.stock_value)
                    } for p in products])

                    filename = f'inventory_report_{timestamp}.xlsx'
                    filepath = Path(app.config['REPORTS_FOLDER']) / filename
                    df.to_excel(filepath, index=False, engine='openpyxl')

                    return send_from_directory(
                        app.config['REPORTS_FOLDER'],
                        filename,
                        as_attachment=True
                    )

            elif report_type == 'low_stock':
                products = Product.query.filter(
                    Product.quantity <= Product.reorder_level,
                    Product.is_active == True
                ).order_by(Product.quantity.asc()).all()

                if format_type == 'pdf':
                    filename = f'low_stock_report_{timestamp}.pdf'
                    filepath = Path(app.config['REPORTS_FOLDER']) / filename
                    report_gen.generate_low_stock_report(
                        products, str(filepath))

                    return send_from_directory(
                        app.config['REPORTS_FOLDER'],
                        filename,
                        as_attachment=True
                    )

            elif report_type == 'transactions':
                date_from = request.form.get('date_from')
                date_to = request.form.get('date_to')

                start_date = datetime.strptime(
                    date_from, '%Y-%m-%d') if date_from else datetime.now() - timedelta(days=30)
                end_date = datetime.strptime(
                    date_to, '%Y-%m-%d') if date_to else datetime.now()

                transactions = InventoryTransaction.query.filter(
                    InventoryTransaction.created_at >= start_date,
                    InventoryTransaction.created_at <= end_date
                ).order_by(InventoryTransaction.created_at.desc()).all()

                if format_type == 'pdf':
                    filename = f'transactions_report_{timestamp}.pdf'
                    filepath = Path(app.config['REPORTS_FOLDER']) / filename
                    report_gen.generate_transaction_report(
                        transactions, start_date, end_date, str(filepath))

                    return send_from_directory(
                        app.config['REPORTS_FOLDER'],
                        filename,
                        as_attachment=True
                    )

            flash('Report generated successfully!', 'success')

        except Exception as e:
            flash(f'Error generating report: {str(e)}', 'danger')

        return redirect(url_for('reports'))

    # ==================== API ENDPOINTS ====================

    @app.route('/api/dashboard-stats')
    @login_required
    def api_dashboard_stats():
        """Real-time dashboard statistics"""
        stats = {
            'total_products': Product.query.filter_by(is_active=True).count(),
            'total_categories': Category.query.filter_by(is_active=True).count(),
            'low_stock_count': Product.query.filter(
                Product.quantity <= Product.reorder_level,
                Product.is_active == True
            ).count(),
            'total_value': sum(
                float(p.cost_price or 0) * (p.quantity or 0)
                for p in Product.query.filter_by(is_active=True).all()
            )
        }
        return jsonify(stats)

    @app.route('/api/products/search')
    @login_required
    def api_product_search():
        """Quick product search for autocomplete"""
        q = request.args.get('q', '').strip()

        if not q or len(q) < 2:
            return jsonify([])

        products = Product.query.filter(
            Product.is_active == True,
            or_(
                Product.name.ilike(f'%{q}%'),
                Product.sku.ilike(f'%{q}%'),
                Product.barcode.ilike(f'%{q}%')
            )
        ).limit(10).all()

        results = [{
            'id': p.id,
            'sku': p.sku,
            'name': p.name,
            'quantity': p.quantity,
            'price': float(p.selling_price or 0)
        } for p in products]

        return jsonify(results)

    @app.route('/api/notifications/unread-count')
    @login_required
    def api_unread_notifications():
        """Get unread notification count"""
        count = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).count()

        return jsonify({'count': count})

    @app.route('/api/chart-data/<chart_type>')
    @login_required
    def api_chart_data(chart_type):
        """Get chart data for dashboard"""
        if chart_type == 'stock_movement':
            # Last 6 months stock movement
            six_months_ago = datetime.utcnow() - timedelta(days=180)
            data = db.session.query(
                func.strftime(
                    '%Y-%m', InventoryTransaction.created_at).label('month'),
                func.sum(
                    func.case(
                        (InventoryTransaction.transaction_type ==
                         'in', InventoryTransaction.quantity),
                        else_=0
                    )
                ).label('stock_in'),
                func.sum(
                    func.case(
                        (InventoryTransaction.transaction_type ==
                         'out', InventoryTransaction.quantity),
                        else_=0
                    )
                ).label('stock_out')
            ).filter(
                InventoryTransaction.created_at >= six_months_ago
            ).group_by('month').order_by('month').all()

            return jsonify({
                'labels': [row.month for row in data],
                'stock_in': [int(row.stock_in or 0) for row in data],
                'stock_out': [int(row.stock_out or 0) for row in data]
            })

        elif chart_type == 'category_distribution':
            data = db.session.query(
                Category.name,
                func.count(Product.id).label('count')
            ).join(Product).filter(
                Product.is_active == True
            ).group_by(Category.id).all()

            return jsonify({
                'labels': [row.name for row in data],
                'values': [row.count for row in data]
            })

        return jsonify({'error': 'Invalid chart type'}), 400

    # ==================== ERROR HANDLERS ====================

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    return app

# ==================== RUN APPLICATION ====================


if __name__ == "__main__":
    app = create_app()

    with app.app_context():
        db.create_all()

    app.run(debug=True, host='0.0.0.0', port=5000)
