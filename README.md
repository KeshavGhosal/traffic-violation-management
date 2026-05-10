# 🚦 Smart Traffic Violation Management System
### Python Flask + MySQL | Role-Based | Dark Theme UI

---

## 📁 Project Structure

```
traffic_system/
├── app.py                  ← Main Flask application
├── requirements.txt        ← Python dependencies
├── violations_log.csv      ← Auto-generated CSV log
└── templates/
    ├── login.html          ← Login page
    ├── register.html       ← Registration page
    ├── police_dashboard.html
    ├── user_dashboard.html
    └── analytics.html
```

---

## ⚙️ Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure MySQL
Edit `app.py` — update the `DB_CONFIG` block:
```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'YOUR_PASSWORD',   # ← your MySQL password
    'database': 'traffic_db'
}
```

### 3. Initialize the Database
Start the app once, then visit:
```
http://localhost:5000/setup
```
This creates the `traffic_db` database, tables, and two demo accounts.

### 4. Run the App
```bash
python app.py
```
Visit: `http://localhost:5000`

---

## 👤 Demo Accounts

| Role   | Username   | Password   |
|--------|------------|------------|
| Police | officer1   | police123  |
| User   | demo_user  | user123    |

---

## 🗄️ Database Schema

### `users` table
| Column     | Type         |
|------------|--------------|
| id         | INT PK AUTO  |
| username   | VARCHAR(50) UNIQUE |
| email      | VARCHAR(100) UNIQUE |
| password   | VARCHAR(255) — SHA256 hashed |
| role       | ENUM('user','police') |
| created_at | TIMESTAMP    |

### `fines` table
| Column         | Type         |
|----------------|--------------|
| id             | INT PK AUTO  |
| vehicle_number | VARCHAR(20)  |
| category       | VARCHAR(50)  |
| amount         | INT          |
| status         | ENUM('Pending','Paid','Overdue') |
| due_date       | DATE         |
| created_at     | TIMESTAMP    |

---

## 💰 Fine Ranges

| Violation               | Fine Range     |
|-------------------------|----------------|
| Helmet Violation        | ₹1,000–₹3,000  |
| Overspeeding            | ₹3,000–₹8,000  |
| Signal Jump             | ₹2,000–₹5,000  |
| Wrong Parking           | ₹500–₹1,500    |
| Drunk Driving           | ₹5,000–₹10,000 |
| Triple Riding           | ₹1,000–₹2,000  |
| No Seatbelt             | ₹500–₹1,500    |
| Using Mobile While Driving | ₹2,000–₹5,000 |

---

## 🚀 Features

- ✅ Role-based auth (Police / Citizen)
- ✅ Police: issue violations with auto-generated fines
- ✅ Police: mark overdue fines in bulk
- ✅ User: search by vehicle number + filter by category
- ✅ User: pay individual fines (AJAX, no page reload)
- ✅ Analytics: donut chart, bar chart, trend line
- ✅ CSV logging of all violations
- ✅ SHA-256 password hashing
- ✅ Dark, modern UI with responsive layout
