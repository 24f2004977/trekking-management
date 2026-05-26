from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ---------------------------------------------------------
# 1. USER TABLE
# ---------------------------------------------------------
class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password = db.Column(db.String(120), nullable=False)
    contact_number = db.Column(db.String(15), nullable=True) # [NEW] User contact number
    emergency_contact = db.Column(db.String(15), nullable=True) # [NEW] Emergency contact number
    role = db.Column(db.String(20), nullable=False) # 'Admin', 'Staff', 'User'
    status = db.Column(db.String(20), default='Active') # 'Active', 'Blacklisted'
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # [NEW] History tracking ke liye

    bookings = db.relationship('Booking', backref='trekker', lazy=True, cascade="all, delete-orphan")
    staff_profile = db.relationship('StaffProfile', backref='user_account', uselist=False, cascade="all, delete-orphan")

# ---------------------------------------------------------
# 2. STAFF PROFILE TABLE
# ---------------------------------------------------------
class StaffProfile(db.Model):
    __tablename__ = 'staff_profile'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    contact_details = db.Column(db.String(15), nullable=False)
    status = db.Column(db.String(20), default='Available') 
    bio = db.Column(db.Text)
    
    assigned_treks = db.relationship('Trek', backref='leader', lazy=True)

# ---------------------------------------------------------
# 3. TREK TABLE
# ---------------------------------------------------------
class Trek(db.Model):
    __tablename__ = 'trek'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False) # 'Easy', 'Moderate', 'Hard'
    duration = db.Column(db.Integer, nullable=False) 
    total_slots = db.Column(db.Integer, nullable=False)
    available_slots = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Pending') # 'Open', 'Closed', 'Completed'
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff_profile.id'), nullable=True)
    
    price_per_person = db.Column(db.Float, default=0.0)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # [NEW] Sorting ke liye (Latest treks first)

    bookings = db.relationship('Booking', backref='trek_ref', lazy=True, cascade="all, delete-orphan")

# ---------------------------------------------------------
# 4. BOOKING TABLE (PRO VERSION)
# ---------------------------------------------------------
class Booking(db.Model):
    __tablename__ = 'booking'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey('trek.id'), nullable=False)
    
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Booked') # 'Booked', 'Cancelled', 'Completed'
    
    num_people = db.Column(db.Integer, default=1, nullable=False) 
    total_amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default='Pending') 
    
    # [NEW] FEEDBACK SYSTEM (Viva point: "Maintaining Trek History")
    rating = db.Column(db.Integer, nullable=True) # User 1-5 star rating de sake
    review = db.Column(db.Text, nullable=True) # User feedback likh sake
    
    # [NEW] CANCEL LOGIC
    cancellation_reason = db.Column(db.String(255), nullable=True) # Agar user cancel kare toh kyun kiya?

    special_requests = db.Column(db.Text)

    