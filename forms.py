from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, SelectField, TextAreaField, \
    PasswordField, SubmitField, BooleanField, EmailField, TelField, HiddenField
from wtforms.validators import DataRequired, Optional, NumberRange, Email, Length, EqualTo, \
    ValidationError, Regexp
from models import User, Product
import phonenumbers

# Custom validators
def validate_phone(form, field):
    """Validate Philippine phone number"""
    try:
        parsed = phonenumbers.parse(field.data, "PH")
        if not phonenumbers.is_valid_number(parsed):
            raise ValidationError('Invalid Philippine phone number')
    except:
        raise ValidationError(
            'Invalid phone number format. Use +639XXXXXXXXX or 09XXXXXXXXX')


def validate_unique_username(form, field):
    """Check if username already exists"""
    if hasattr(form, 'user_id') and form.user_id:
        # Editing existing user
        user = User.query.filter(
            User.username == field.data, User.id != form.user_id).first()
    else:
        user = User.query.filter_by(username=field.data).first()

    if user:
        raise ValidationError('Username already taken')


def validate_unique_email(form, field):
    """Check if email already exists"""
    if hasattr(form, 'user_id') and form.user_id:
        user = User.query.filter(
            User.email == field.data, User.id != form.user_id).first()
    else:
        user = User.query.filter_by(email=field.data).first()

    if user:
        raise ValidationError('Email already registered')


def validate_unique_sku(form, field):
    """Check if SKU already exists"""
    if hasattr(form, 'product_id') and form.product_id:
        product = Product.query.filter(
            Product.sku == field.data, Product.id != form.product_id).first()
    else:
        product = Product.query.filter_by(sku=field.data).first()

    if product:
        raise ValidationError('SKU already exists')


# Authentication Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=80),
        Regexp('^[A-Za-z0-9_]+$',
               message='Username must contain only letters, numbers, and underscores'),
        validate_unique_username
    ])
    email = EmailField('Email', validators=[
                       DataRequired(), Email(), validate_unique_email])
    phone = TelField('Phone Number', validators=[
                     DataRequired(), validate_phone])
    full_name = StringField('Full Name', validators=[
                            DataRequired(), Length(max=150)])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')


class ForgotPasswordForm(FlaskForm):
    phone = TelField('Phone Number', validators=[DataRequired()])
    submit = SubmitField('Send OTP')


class VerifyOTPForm(FlaskForm):
    otp_code = StringField('Verification Code', validators=[
        DataRequired(),
        Length(min=6, max=6, message='OTP must be 6 digits')
    ])
    submit = SubmitField('Verify')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')


# User Management Forms
class UserForm(FlaskForm):
    user_id = HiddenField()
    username = StringField('Username', validators=[
                           DataRequired(), Length(max=80)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    phone = TelField('Phone Number', validators=[DataRequired()])
    full_name = StringField('Full Name', validators=[
                            DataRequired(), Length(max=150)])
    role = SelectField('Role', choices=[
        ('user', 'User'),
        ('manager', 'Manager'),
        ('admin', 'Admin')
    ])
    is_active = BooleanField('Active')
    submit = SubmitField('Save')


class UserSettingsForm(FlaskForm):
    full_name = StringField('Full Name', validators=[
                            Optional(), Length(max=150)])
    email = EmailField('Email', validators=[Optional(), Email()])
    phone = TelField('Phone Number', validators=[Optional()])
    currency = SelectField('Preferred Currency', choices=[
        ('PHP', 'Philippine Peso (₱)'),
        ('USD', 'US Dollar ($)'),
        ('EUR', 'Euro (€)'),
        ('JPY', 'Japanese Yen (¥)')
    ])
    enable_notifications = BooleanField('Enable Notifications')
    enable_email_alerts = BooleanField('Enable Email Alerts')
    enable_sms_alerts = BooleanField('Enable SMS Alerts')
    submit = SubmitField('Update Settings')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        'Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Change Password')


# Product & Inventory Forms
class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[
                       DataRequired(), Length(max=120)])
    description = TextAreaField('Description', validators=[Optional()])
    icon = StringField('Icon Class (e.g., bi-box)',
                       validators=[Optional(), Length(max=50)])
    color = StringField('Color (Hex)', validators=[Optional(), Length(max=7)])
    submit = SubmitField('Save')


class SupplierForm(FlaskForm):
    name = StringField('Supplier Name', validators=[
                       DataRequired(), Length(max=200)])
    contact_person = StringField('Contact Person', validators=[
                                 Optional(), Length(max=150)])
    email = EmailField('Email', validators=[Optional(), Email()])
    phone = TelField('Phone', validators=[Optional()])
    address = TextAreaField('Address', validators=[Optional()])
    website = StringField('Website', validators=[Optional(), Length(max=255)])
    credit_limit = DecimalField(
        'Credit Limit', validators=[Optional()], places=2)
    rating = IntegerField(
        'Rating (1-5)', validators=[Optional(), NumberRange(min=1, max=5)])
    is_active = BooleanField('Active')
    submit = SubmitField('Save')


class ProductForm(FlaskForm):
    product_id = HiddenField()
    sku = StringField('SKU', validators=[DataRequired(), Length(max=80)])
    name = StringField('Product Name', validators=[
                       DataRequired(), Length(max=255)])
    description = TextAreaField('Description', validators=[Optional()])
    barcode = StringField('Barcode', validators=[Optional(), Length(max=100)])

    category_id = SelectField('Category', coerce=int, validators=[Optional()])
    supplier_id = SelectField('Supplier', coerce=int, validators=[Optional()])

    cost_price = DecimalField('Cost Price', validators=[Optional()], places=2)
    selling_price = DecimalField(
        'Selling Price', validators=[Optional()], places=2)
    currency = SelectField('Currency', choices=[
        ('PHP', 'PHP'),
        ('USD', 'USD'),
        ('EUR', 'EUR'),
        ('JPY', 'JPY')
    ])

    quantity = IntegerField('Initial Quantity', validators=[
                            Optional(), NumberRange(min=0)])
    reorder_level = IntegerField('Reorder Level', validators=[
                                 Optional(), NumberRange(min=0)])
    reorder_quantity = IntegerField('Reorder Quantity', validators=[
                                    Optional(), NumberRange(min=1)])

    weight = DecimalField('Weight (kg)', validators=[Optional()], places=3)
    dimensions = StringField('Dimensions (LxWxH)', validators=[
                             Optional(), Length(max=50)])

    is_active = BooleanField('Active')
    is_featured = BooleanField('Featured')

    submit = SubmitField('Save Product')


class StockAdjustForm(FlaskForm):
    delta = IntegerField('Quantity', validators=[DataRequired()])
    adjustment_type = SelectField('Type', choices=[
        ('in', 'Stock In (+)'),
        ('out', 'Stock Out (-)'),
        ('adjust', 'Adjustment')
    ])
    reference = StringField('Reference/Invoice No.',
                            validators=[Optional(), Length(max=120)])
    remarks = TextAreaField('Remarks/Notes', validators=[Optional()])
    submit = SubmitField('Adjust Stock')


class SearchForm(FlaskForm):
    q = StringField('Search', validators=[Optional()])
    category = SelectField('Category', coerce=int, validators=[Optional()])
    supplier = SelectField('Supplier', coerce=int, validators=[Optional()])
    stock_status = SelectField('Stock Status', choices=[
        ('', 'All'),
        ('in_stock', 'In Stock'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock')
    ])
    sort_by = SelectField('Sort By', choices=[
        ('name_asc', 'Name (A-Z)'),
        ('name_desc', 'Name (Z-A)'),
        ('quantity_asc', 'Quantity (Low-High)'),
        ('quantity_desc', 'Quantity (High-Low)'),
        ('price_asc', 'Price (Low-High)'),
        ('price_desc', 'Price (High-Low)'),
        ('newest', 'Newest First'),
        ('oldest', 'Oldest First')
    ])
    submit = SubmitField('Search')


# Report Forms
class ReportForm(FlaskForm):
    report_type = SelectField('Report Type', choices=[
        ('inventory', 'Complete Inventory'),
        ('low_stock', 'Low Stock Items'),
        ('transactions', 'Transaction History'),
        ('category', 'By Category'),
        ('supplier', 'By Supplier')
    ], validators=[DataRequired()])

    category_id = SelectField(
        'Category (for category report)', coerce=int, validators=[Optional()])
    supplier_id = SelectField(
        'Supplier (for supplier report)', coerce=int, validators=[Optional()])

    date_from = StringField('From Date', validators=[Optional()])
    date_to = StringField('To Date', validators=[Optional()])

    format = SelectField('Format', choices=[
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV')
    ])

    submit = SubmitField('Generate Report')
