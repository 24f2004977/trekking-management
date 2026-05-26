from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, User, StaffProfile, Trek, Booking
from datetime import datetime
from sqlalchemy import func
from zoneinfo import ZoneInfo
import os

app = Flask(__name__)

# --- Configuration ---
db_url = os.environ.get("DATABASE_URL")

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///trekking_mgmt.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "mad1_project_secret_key")

db.init_app(app)

# --- Database Initialization & Admin Seeding ---
with app.app_context():
    db.create_all()
    admin_user = User.query.filter_by(role='Admin').first()
    if not admin_user:
        new_admin = User(
            username='admin',
            password='admin123',
            role='Admin',
            email='admin@trek.com'
        )
        db.session.add(new_admin)
        db.session.commit()
        print("Admin user created: username: admin, password: admin123")

# --- API ROUTES ---

@app.route('/api/treks')
def api_treks():
    treks = Trek.query.all()

    data = []
    for trek in treks:
        data.append({
            "id": trek.id,
            "name": trek.name,
            "location": trek.location,
            "difficulty": trek.difficulty,
            "duration": trek.duration,
            "price_per_person": trek.price_per_person,
            "available_slots": trek.available_slots,
            "total_slots": trek.total_slots,
            "status": trek.status
        })

    return jsonify(data)


@app.route('/api/bookings')
def api_bookings():
    if session.get('role') != 'Admin':
        return jsonify({"error": "Unauthorized"}), 403

    bookings = Booking.query.all()

    data = []
    for booking in bookings:
        data.append({
            "id": booking.id,
            "user_id": booking.user_id,
            "trek_id": booking.trek_id,
            "num_people": booking.num_people,
            "total_amount": booking.total_amount,
            "status": booking.status
        })

    return jsonify(data)


@app.route('/api/users')
def api_users():
    if session.get('role') != 'Admin':
        return jsonify({"error": "Unauthorized"}), 403

    users = User.query.all()

    data = []
    for user in users:
        data.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "status": user.status
        })

    return jsonify(data)        

# --- AUTHENTICATION ROUTES ---

@app.route('/')
def index():
    return redirect(url_for('auth/login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form.get('username')
        pwd = request.form.get('password')
        user = User.query.filter_by(username=uname, password=pwd).first()
        
        if user:
            if user.status == 'Blacklisted':
                flash("Your account is blacklisted. Contact Admin.")
                return redirect(url_for('login'))
            
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            
            if user.role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'Staff':
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash("Invalid Username or Password")
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form.get('username')
        email = request.form.get('email')
        pwd = request.form.get('password')
        contact = request.form.get('contact')
        emergency = request.form.get('emergency_contact')
        
        if User.query.filter_by(username=uname).first():
            flash("Username already exists!")
            return redirect(url_for('register'))
            
        new_user = User(
            username=uname, email=email, password=pwd, role='User', 
            contact_number=contact, emergency_contact=emergency
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Registration Successful! Please Login.")
        return redirect(url_for('login'))
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# --- ADMIN ROUTES ---

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'Admin': return redirect(url_for('login'))

    search_q = request.args.get('search', '')
    found_users = []
    
    if search_q:
        treks = Trek.query.filter((Trek.name.contains(search_q)) | (Trek.location.contains(search_q))).all()
        found_users = User.query.filter(User.username.contains(search_q)).all()
    else:
        treks = Trek.query.all()
    
    stats = {
        't_treks': Trek.query.count(),
        't_users': User.query.filter_by(role='User').count(),
        't_staff': User.query.filter_by(role='Staff').count(),
        't_bookings': Booking.query.count()
    }
    
    total_revenue = db.session.query(db.func.sum(Booking.total_amount)).filter(Booking.status == 'Booked').scalar() or 0

    return render_template('admin/admin_dashboard.html', total_revenue=total_revenue, treks=treks, found_users=found_users, **stats)

@app.route('/admin/add_staff', methods=['GET', 'POST'])
def add_staff():
    if session.get('role') != 'Admin': return redirect(url_for('login'))
    if request.method == 'POST':
        uname = request.form.get('username')
        pwd = request.form.get('password')
        name = request.form.get('name')
        contact = request.form.get('contact')
        bio = request.form.get('bio')
        
        if User.query.filter_by(username=uname).first():
            flash("Username already exists!")
            return redirect(url_for('add_staff'))
            
        new_user = User(username=uname, password=pwd, role='Staff')
        db.session.add(new_user)
        db.session.commit()
        
        new_profile = StaffProfile(user_id=new_user.id, name=name, contact_details=contact, bio=bio)
        db.session.add(new_profile)
        db.session.commit()
        
        flash("Staff Member Added Successfully!")
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/add_staff.html')

@app.route('/admin/manage_trekkers')
def manage_trekkers():
    if session.get('role') != 'Admin': return redirect(url_for('login'))
    trekkers = User.query.filter_by(role='User').all()
    return render_template('admin/manage_trekkers.html', trekkers=trekkers)

@app.route('/admin/manage_staff')
def manage_staff():
    if session.get('role') != 'Admin': return redirect(url_for('login'))
    staff_members = User.query.filter_by(role='Staff').all()
    return render_template('admin/manage_staff.html', staff_members=staff_members)

@app.route('/admin/blacklist/<int:user_id>')
def blacklist(user_id):
    if session.get('role') != 'Admin': return redirect(url_for('login'))
    user = User.query.get(user_id)
    if user:
        user.status = 'Blacklisted' if user.status == 'Active' else 'Active'
        db.session.commit()
        flash(f"Status updated for {user.username}")
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/admin/add_trek', methods=['GET', 'POST'])
def add_trek():
    if session.get('role') != 'Admin': return redirect(url_for('login'))
    staff_list = StaffProfile.query.all()
    if request.method == 'POST':
        s_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        e_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        if s_date > e_date:
            flash("Error: Start date cannot be after End date!")
            return redirect(url_for('add_trek'))

        new_trek = Trek(
            name=request.form.get('name'), location=request.form.get('location'),
            difficulty=request.form.get('difficulty'), duration=int(request.form.get('duration')),
            total_slots=int(request.form.get('slots')), available_slots=int(request.form.get('slots')),
            price_per_person=float(request.form.get('price')), description=request.form.get('description'),
            start_date=s_date, end_date=e_date, staff_id=request.form.get('staff_id'), status='Open'
        )
        db.session.add(new_trek)
        db.session.commit()
        flash("New Trek Created!")
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/add_trek.html', staff=staff_list)

@app.route('/admin/edit_trek/<int:trek_id>', methods=['GET', 'POST'])
def edit_trek(trek_id):
    if session.get('role') != 'Admin': return redirect(url_for('login'))
    trek = Trek.query.get(trek_id)
    staff_list = StaffProfile.query.all()
    if request.method == 'POST':
        trek.name = request.form.get('name')
        trek.location = request.form.get('location')
        trek.difficulty = request.form.get('difficulty')
        trek.duration = int(request.form.get('duration'))
        trek.total_slots = int(request.form.get('slots'))
        trek.price_per_person = float(request.form.get('price'))
        trek.staff_id = request.form.get('staff_id')
        trek.status = request.form.get('status')
        db.session.commit()
        flash("Trek updated successfully!")
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/edit_trek.html', trek=trek, staff=staff_list)

@app.route('/admin/delete_trek/<int:trek_id>')
def delete_trek(trek_id):
    if session.get('role') != 'Admin': return redirect(url_for('login'))
    trek = Trek.query.get(trek_id)
    if trek:
        db.session.delete(trek)
        db.session.commit()
        flash("Trek deleted!")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/all_bookings')
def all_bookings():
    if session.get('role') != 'Admin': return redirect(url_for('login'))
    bookings = Booking.query.all()
    return render_template('admin/all_bookings.html', bookings=bookings)

@app.route('/admin/reports')
def admin_reports():
    if session.get('role') != 'Admin':
        return redirect(url_for('login'))

    # Basic Data
    treks = Trek.query.all()
    bookings = Booking.query.all()
    staff_members = User.query.filter_by(role='Staff').all()

    # Revenue
    total_revenue = db.session.query(
        db.func.sum(Booking.total_amount)
    ).filter(
        Booking.status == 'Booked'
    ).scalar() or 0

    # Cancellation Analytics
    cancelled_bookings = Booking.query.filter_by(status='Cancelled').all()
    cancelled_count = len(cancelled_bookings)

    cancelled_revenue = 0
    for cb in cancelled_bookings:
        cancelled_revenue += cb.total_amount

    # Global Stats
    t_bookings = len(bookings)

    # Chart Data
    trek_names = []
    trek_booking_counts = []

    for trek in treks:
        trek_names.append(trek.name)

        count = Booking.query.filter_by(
            trek_id=trek.id,
            status='Booked'
        ).count()

        trek_booking_counts.append(count)

    booking_status_counts = {
        "Booked": Booking.query.filter_by(status='Booked').count(),
        "Pending": Booking.query.filter_by(status='Pending Payment').count(),
        "Cancelled": Booking.query.filter_by(status='Cancelled').count()
    }

    return render_template(
        'admin/admin_reports.html',
        treks=treks,
        bookings=bookings,
        staff_members=staff_members,
        total_revenue=total_revenue,
        cancelled_revenue=cancelled_revenue,
        cancelled_count=cancelled_count,
        t_bookings=t_bookings,
        trek_names=trek_names,
        trek_booking_counts=trek_booking_counts,
        booking_status_counts=booking_status_counts
    )   


# --- USER ROUTES ---

@app.route('/user_dashboard')
def user_dashboard():
    if session.get('role') != 'User': return redirect(url_for('login'))
    search = request.args.get('search')
    diff = request.args.get('difficulty')
    query = Trek.query
    
    if search:
        query = query.filter((Trek.name.contains(search)) | (Trek.location.contains(search)))
    if diff and diff != "All":
        query = query.filter_by(difficulty=diff)
    
    treks = query.all()
    user_bookings = Booking.query.filter_by(user_id=session['user_id']).all()
    
    return render_template('user/user_dashboard.html', treks=treks, user_bookings=user_bookings)

@app.route('/book_trek/<int:trek_id>', methods=['POST'])
def book_trek(trek_id):
    if session.get('role') != 'User':
        return redirect(url_for('login'))

    trek = Trek.query.get(trek_id)

    if not trek:
        flash("Trek not found.")
        return redirect(url_for('user_dashboard'))

    num_p = int(request.form.get('num_people', 1))
    user_id = session['user_id']
    target_booking_id = request.form.get('target_booking_id', 'new')

    if trek.status != 'Open':
        flash("This trek is not open for booking.")
        return redirect(url_for('user_dashboard'))

    if trek.available_slots < num_p:
        flash("Not enough slots available.")
        return redirect(url_for('user_dashboard'))

    amount = num_p * trek.price_per_person

    if target_booking_id == 'new':
        new_booking = Booking(
            user_id=user_id,
            trek_id=trek.id,
            num_people=num_p,
            total_amount=amount,
            status='Pending Payment'
        )
        db.session.add(new_booking)
        db.session.commit()

        b_id = new_booking.id
        is_new_flag = "true"

    else:
        existing_booking = Booking.query.filter_by(
            id=int(target_booking_id),
            user_id=user_id,
            trek_id=trek.id,
            status='Booked'
        ).first()

        if not existing_booking:
            flash("Invalid booking selected.")
            return redirect(url_for('user_dashboard'))

        b_id = existing_booking.id
        is_new_flag = "false"

    return redirect(url_for(
        'payment_page',
        booking_id=b_id,
        amount=amount,
        num_p=num_p,
        is_new=is_new_flag
    ))

@app.route('/payment')
def payment_page():
    if session.get('role') != 'User': return redirect(url_for('login'))
    
    b_id = request.args.get('booking_id')
    amount = request.args.get('amount')
    num_p = request.args.get('num_p')
    is_new = request.args.get('is_new')
    
    booking = Booking.query.get(b_id)

    if not booking or booking.user_id != session['user_id']:
        flash("Invalid booking.")
        return redirect(url_for('user_dashboard'))

    trek = Trek.query.get(booking.trek_id)

    extra_people = 0

    if is_new == "false":
        extra_people = int(num_p)
    
    return render_template('user/payment.html', booking=booking, trek=trek, amount=amount, num_p=num_p, is_new=is_new, extra_people=extra_people)

@app.route('/process_payment/<int:booking_id>', methods=['POST'])
def process_payment(booking_id):
    if session.get('role') != 'User':
        return redirect(url_for('login'))

    booking = Booking.query.get(booking_id)

    if not booking or booking.user_id != session['user_id']:
        flash("Invalid payment request.")
        return redirect(url_for('user_dashboard'))

    trek = Trek.query.get(booking.trek_id)

    if not trek:
        flash("Trek not found.")
        return redirect(url_for('user_dashboard'))

    num_p = int(request.form.get('num_p', 0))
    amount = float(request.form.get('amount', 0))
    is_new = request.form.get('is_new')

    db.session.refresh(trek)

    if trek.available_slots < num_p:
        flash("Sorry, slots are no longer available.")
        return redirect(url_for('user_dashboard'))

    if is_new == "true":
        if booking.status == 'Booked':
            flash("Payment already completed.")
            return redirect(url_for('my_bookings'))

        booking.status = 'Booked'

    else:
        if booking.status != 'Booked':
            flash("Existing booking not valid.")
            return redirect(url_for('user_dashboard'))

        booking.num_people += num_p
        booking.total_amount += amount

    trek.available_slots -= num_p

    db.session.commit()

    flash(f"Payment Successful! ₹{amount} received.")
    return redirect(url_for('my_bookings'))

@app.route('/my_bookings')
def my_bookings():
    if session.get('role') != 'User': return redirect(url_for('login'))
    bookings = Booking.query.filter_by(user_id=session['user_id']).all()
    return render_template('user/my_bookings.html', bookings=bookings)

@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    if session.get('role') != 'User': 
        return redirect(url_for('login'))
    
    booking = Booking.query.get(booking_id)
    cancel_count = int(request.form.get('cancel_count', 0))

    if booking and booking.user_id == session['user_id'] and booking.status == 'Booked':
        trek = Trek.query.get(booking.trek_id)

        price_per_person = booking.total_amount / booking.num_people

        trek.available_slots += cancel_count

        if cancel_count >= booking.num_people:
            booking.status = 'Cancelled'
            booking.num_people = 0
            booking.total_amount = 0
            flash(f"Full booking for {trek.name} has been cancelled.")
        
        else:
            # Sirf kuch log cancel ho rahe hain (Partial)
            booking.num_people -= cancel_count
            booking.total_amount -= (price_per_person * cancel_count)
            flash(f"{cancel_count} person(s) cancelled. Remaining {booking.num_people} are still booked.")
            # Status 'Booked' hi rahega kyunki baki log ja rahe hain

        booking.cancellation_reason = request.form.get('reason', 'Cancelled by User')
        db.session.commit()
    else:
        flash("Error: This booking cannot be cancelled.")
    return redirect(url_for('my_bookings'))  

@app.route('/trek_history')
def trek_history():
    if 'user_id' not in session or session.get('role') != 'User':
        flash("Please login first.")
        return redirect('/login')

    bookings = Booking.query.filter_by(user_id=session['user_id']).all()

    return render_template('user/trek_history.html', bookings=bookings) 

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session or session.get('role') != 'User':
        flash("Please login first.")
        return redirect('/login')

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user.email = request.form['email']
        user.contact_number = request.form['contact']
        user.emergency_contact = request.form['emergency_contact']

        db.session.commit()
        flash("Profile updated successfully!")
        return redirect('/edit_profile')

    return render_template('user/edit_profile.html', user=user)         


# --- STAFF ROUTES ---

@app.route('/staff_dashboard')
def staff_dashboard():
    if session.get('role') != 'Staff': return redirect(url_for('login'))
    staff = StaffProfile.query.filter_by(user_id=session['user_id']).first()
    if not staff: return "Staff Profile missing!", 404
    treks = Trek.query.filter_by(staff_id=staff.id).all()
    return render_template('staff/staff_dashboard.html', treks=treks, staff=staff)

@app.route('/staff/manage_trek/<int:trek_id>', methods=['GET', 'POST'])
def manage_trek(trek_id):
    if session.get('role') != 'Staff': return redirect(url_for('login'))
    
    staff = StaffProfile.query.filter_by(user_id=session['user_id']).first()
    trek = Trek.query.filter_by(
        id=trek_id,
        staff_id=staff.id
    ).first()

    if not trek:
        flash("Unauthorized access.")
        return redirect(url_for('staff_dashboard'))


    if request.method == 'POST':
        trek.status = request.form.get('status')
        trek.available_slots = int(request.form.get('available_slots'))
        db.session.commit()
        flash("Trek updated!")
        return redirect(url_for('staff_dashboard'))
    return render_template('staff/manage_trek.html', trek=trek)

@app.route('/staff/participants/<int:trek_id>')
def view_participants(trek_id):
    if session.get('role') != 'Staff': return redirect(url_for('login'))

    staff = StaffProfile.query.filter_by(user_id=session['user_id']).first()

    trek = Trek.query.filter_by(
        id=trek_id,
        staff_id=staff.id
    ).first()

    if not trek:
        flash("Unauthorized access.")
        return redirect(url_for('staff_dashboard'))

    bookings = Booking.query.filter_by(trek_id=trek_id).all()
    return render_template('staff/view_participants.html', trek=trek, bookings=bookings)


if __name__ == '__main__':
    app.run(debug=True)
