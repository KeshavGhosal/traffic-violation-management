from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import mysql.connector
import csv
import os
import random
from datetime import datetime, timedelta
from functools import wraps
import hashlib

app = Flask(__name__)
app.secret_key = 'traffic_secret_key_2024'

# ─── DB CONFIG ───────────────────────────────────────────────────────────────
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',        # ← change to your MySQL password
    'database': 'traffic_db'
}

CSV_FILE = 'violations_log.csv'

# ─── FINE RANGES ─────────────────────────────────────────────────────────────
FINE_RANGES = {
    'Helmet Violation':      (1000, 3000),
    'Overspeeding':          (3000, 8000),
    'Signal Jump':           (2000, 5000),
    'Wrong Parking':         (500,  1500),
    'Drunk Driving':         (5000, 10000),
    'Triple Riding':         (1000, 2000),
    'No Seatbelt':           (500,  1500),
    'Using Mobile While Driving': (2000, 5000),
}

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def police_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'police':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def log_to_csv(data):
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id','vehicle_number','category','amount','status','due_date','created_at'])
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hash_pw(request.form['password'])
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()
        db.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            if user['role'] == 'police':
                return redirect(url_for('police_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email    = request.form['email']
        password = hash_pw(request.form['password'])
        role     = request.form.get('role', 'user')
        db = get_db()
        cur = db.cursor()
        try:
            cur.execute("INSERT INTO users (username, email, password, role) VALUES (%s,%s,%s,%s)",
                        (username, email, password, role))
            db.commit()
            db.close()
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            db.close()
            return render_template('register.html', error='Username or email already exists')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── POLICE ───────────────────────────────────────────────────────────────────

@app.route('/police')
@police_required
def police_dashboard():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM fines ORDER BY created_at DESC LIMIT 20")
    recent = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS total FROM fines")
    total = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS paid FROM fines WHERE status='Paid'")
    paid = cur.fetchone()['paid']
    cur.execute("SELECT COUNT(*) AS pending FROM fines WHERE status='Pending'")
    pending = cur.fetchone()['pending']
    cur.execute("SELECT COUNT(*) AS overdue FROM fines WHERE status='Overdue'")
    overdue = cur.fetchone()['overdue']
    db.close()
    return render_template('police_dashboard.html',
        recent=recent, total=total, paid=paid,
        pending=pending, overdue=overdue,
        categories=list(FINE_RANGES.keys()))

@app.route('/police/add', methods=['POST'])
@police_required
def add_violation():
    vehicle  = request.form['vehicle_number'].upper().strip()
    category = request.form['category']
    lo, hi   = FINE_RANGES.get(category, (1000, 5000))
    amount   = random.randint(lo, hi)
    due_date = datetime.now() + timedelta(days=7)
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO fines (vehicle_number, category, amount, status, due_date) VALUES (%s,%s,%s,'Pending',%s)",
        (vehicle, category, amount, due_date.strftime('%Y-%m-%d'))
    )
    db.commit()
    fine_id = cur.lastrowid
    db.close()
    log_to_csv({'id': fine_id, 'vehicle_number': vehicle, 'category': category,
                'amount': amount, 'status': 'Pending',
                'due_date': due_date.strftime('%Y-%m-%d'),
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    flash(f'Violation added! Fine: ₹{amount:,}', 'success')
    return redirect(url_for('police_dashboard'))

@app.route('/police/update_overdue', methods=['POST'])
@police_required
def update_overdue():
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE fines SET status='Overdue' WHERE status='Pending' AND due_date < CURDATE()")
    db.commit()
    db.close()
    flash('Overdue statuses updated.', 'info')
    return redirect(url_for('police_dashboard'))

# ── USER ──────────────────────────────────────────────────────────────────────

@app.route('/user')
@login_required
def user_dashboard():
    return render_template('user_dashboard.html')

@app.route('/user/search', methods=['POST'])
@login_required
def search_violations():
    vehicle  = request.form['vehicle_number'].upper().strip()
    category = request.form.get('category', '')
    db = get_db()
    cur = db.cursor(dictionary=True)
    if category:
        cur.execute("SELECT * FROM fines WHERE vehicle_number=%s AND category=%s ORDER BY created_at DESC",
                    (vehicle, category))
    else:
        cur.execute("SELECT * FROM fines WHERE vehicle_number=%s ORDER BY created_at DESC", (vehicle,))
    fines = cur.fetchall()
    total_due = sum(f['amount'] for f in fines if f['status'] != 'Paid')
    db.close()
    return render_template('user_dashboard.html',
        fines=fines, vehicle=vehicle,
        total_due=total_due, searched=True,
        categories=list(FINE_RANGES.keys()),
        selected_category=category)

@app.route('/user/pay/<int:fine_id>', methods=['POST'])
@login_required
def pay_fine(fine_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE fines SET status='Paid' WHERE id=%s", (fine_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})

# ── ANALYTICS ─────────────────────────────────────────────────────────────────

@app.route('/analytics')
@login_required
def analytics():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT status, COUNT(*) as count, SUM(amount) as total FROM fines GROUP BY status")
    status_data = cur.fetchall()
    cur.execute("SELECT category, COUNT(*) as count FROM fines GROUP BY category ORDER BY count DESC")
    cat_data = cur.fetchall()
    cur.execute("SELECT DATE(created_at) as day, COUNT(*) as count FROM fines GROUP BY day ORDER BY day DESC LIMIT 14")
    daily = cur.fetchall()
    db.close()
    return render_template('analytics.html',
        status_data=status_data, cat_data=cat_data, daily=daily)

# ── INIT DB ───────────────────────────────────────────────────────────────────

@app.route('/setup')
def setup():
    """Run once to create tables and seed demo data."""
    try:
        conn = mysql.connector.connect(host=DB_CONFIG['host'],
                                       user=DB_CONFIG['user'],
                                       password=DB_CONFIG['password'])
        cur = conn.cursor()
        cur.execute("CREATE DATABASE IF NOT EXISTS traffic_db")
        cur.execute("USE traffic_db")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role ENUM('user','police') DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fines (
                id INT AUTO_INCREMENT PRIMARY KEY,
                vehicle_number VARCHAR(20) NOT NULL,
                category VARCHAR(50) NOT NULL,
                amount INT NOT NULL,
                status ENUM('Pending','Paid','Overdue') DEFAULT 'Pending',
                due_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Seed demo accounts
        admin_pw = hashlib.sha256(b'police123').hexdigest()
        user_pw  = hashlib.sha256(b'user123').hexdigest()
        cur.execute("INSERT IGNORE INTO users (username,email,password,role) VALUES ('officer1','officer@traffic.gov',%s,'police')", (admin_pw,))
        cur.execute("INSERT IGNORE INTO users (username,email,password,role) VALUES ('demo_user','user@demo.com',%s,'user')", (user_pw,))
        conn.commit()
        conn.close()
        return "<h2>✅ Database setup complete!</h2><p>Demo accounts:<br><b>Police:</b> officer1 / police123<br><b>User:</b> demo_user / user123</p><a href='/login'>Go to Login →</a>"
    except Exception as e:
        return f"<h2>❌ Error:</h2><pre>{e}</pre>"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
