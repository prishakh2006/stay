# 🏨 LuxeStay – Hotel Reservation System (College DBMS Project)

A beginner-friendly, fully-documented **Hotel Reservation Management System** built with **MySQL 8**, **Python + Flask**, and vanilla **HTML/CSS/JavaScript**.

---

## 📌 Project Overview
- **Domain:** Hotel Room Reservation & Billing (designed for a 30-room hotel).
- **Core Goal:** Provide a clean, robust DBMS demonstration implementing **3rd Normal Form (3NF)**, **Triggers for double-booking prevention**, **Concurrency control via Row-Level Locking (`FOR UPDATE`)**, and **Derived Billing calculations**.
- **No Complex Frameworks & No Login System:** Pure, readable Python and SQL that you can explain effortlessly in a college viva or project demonstration.

---

## 🛠️ Technology Stack
| Layer | Technology | Details |
|---|---|---|
| **Database** | MySQL 8.0 | 6 Tables in 3NF, Foreign Keys, Indexes, BEFORE Triggers |
| **Backend** | Python 3 + Flask | `mysql-connector-python` (100% Parameterized queries) |
| **Frontend** | HTML5, CSS3, Vanilla JS | Clean responsive layout, client-side date validation, no React |

---

## 🗂️ Project Directory Structure

```text
hotel_reservation_dbms_complete/
│
├── schema.sql                   # MySQL 8 schema (6 tables in 3NF + indexes + triggers)
├── sample_data.sql              # Sample data for 2026 (5 customers, rooms, staff, stays, payments)
├── queries.sql                  # 4 core business and reporting queries
├── README.md                    # Complete setup and viva documentation
│
└── hotel_reservation_dbms/      # Flask Web Application Directory
    ├── app.py                   # Flask backend routes, transactions & DB connection
    ├── schema.sql               # Working copy of schema
    ├── sample_data.sql          # Working copy of sample data
    ├── queries.sql              # Working copy of queries
    ├── requirements.txt         # Python dependencies (Flask, mysql-connector-python)
    ├── README.md                # Application README
    │
    ├── static/
    │   ├── style.css            # Custom CSS styling (modern, responsive)
    │   └── script.js            # Vanilla JS date validation
    │
    ├── templates/
    │   ├── base.html            # Shared base template with navbar & flash alerts
    │   ├── index.html           # Home page: hotel overview + room search by dates
    │   ├── rooms.html           # Room catalogue with floor, capacity, and rates
    │   ├── book.html            # Reservation booking form (trigger error handling)
    │   ├── customers.html       # Customer list, search bar & new customer form
    │   ├── history.html         # Customer booking history & calculated stay totals
    │   └── payments.html        # Occupancy report, payment recording & billing table
    │
    └── tests/
        └── test_system.py       # Automated test suite verifying all checks & routes
```

---

## 🏛️ Database Design (Step 1)

The database schema strictly adheres to **3rd Normal Form (3NF)**:
1. **1NF:** All attributes are atomic (no repeating groups, each column has a single value).
2. **2NF:** In 1NF and every non-prime attribute is fully functionally dependent on the entire primary key (no partial dependencies).
3. **3NF:** In 2NF and there are no transitive dependencies (non-key columns depend only on primary keys).

### The 6 Tables

```text
+-------------------+        +-------------------+
|     Customer      |        |     RoomType      |
+-------------------+        +-------------------+
| customer_id (PK)  |        | type_id (PK)      |
| name              |        | type_name         |
| phone             |        | capacity          |
| email (UNIQUE)    |        | price_per_night   |
+--------+----------+        +---------+---------+
         |                             |
         |                             |
         |         +-------------------+
         |         |
         |  +------+------------+
         |  |       Room        |
         |  +-------------------+
         |  | room_id (PK)      |
         |  | room_no (UNIQUE)  |
         |  | floor             |
         |  | type_id (FK)      |
         |  +------+------------+
         |         |
         +----+    |    +-------------------+
              |    |    |       Staff       |
              |    |    +-------------------+
              |    |    | staff_id (PK)     |
              |    |    | name              |
              |    |    | role              |
              |    |    | phone             |
              |    |    +---------+---------+
              |    |              |
              v    v              v
        +-------------------------------+
        |          Reservation          |
        +-------------------------------+
        | reservation_id (PK)           |
        | customer_id (FK)              |
        | room_id (FK)                  |
        | staff_id (FK)                 |
        | check_in (DATE)               |
        | check_out (DATE)              |
        | status (ENUM)                 |
        +---------------+---------------+
                        |
                        v
        +-------------------------------+
        |            Payment            |
        +-------------------------------+
        | payment_id (PK)               |
        | reservation_id (FK)           |
        | amount                        |
        | mode (ENUM: Cash, Card, UPI)  |
        | pay_date (DATE)               |
        +-------------------------------+
```

### Key DBMS Rules Enforced
1. **Derived Bill Total:** The bill total is **NOT stored** in `Reservation`. It is computed dynamically as:
   $$\text{Bill Total} = \text{DATEDIFF}(\text{check\_out}, \text{check\_in}) \times \text{price\_per\_night}$$
   *Viva explanation:* Storing a computed total introduces data redundancy and anomaly risk if room rates or dates change.
2. **Payment Flexibility:** Multiple payments (e.g., initial deposit + final settlement) can link to a single reservation.
3. **Security / Privacy:** Card numbers are never stored in the database.
4. **Performance Indexes:**
   - `Reservation(customer_id)`: Accelerates customer booking history queries.
   - `Reservation(room_id, check_in, check_out)`: Speeds up availability checks and overlap validations.

### Overlap Detection Triggers
Two triggers (`before_reservation_insert` and `before_reservation_update`) reject any new reservation where the room is already booked for overlapping dates:
- **Interval Overlap Condition:**
  ```sql
  NEW.check_in < existing.check_out AND NEW.check_out > existing.check_in
  ```
- **Error Raised:**
  ```sql
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Room already booked for these dates';
  ```

### Concurrency Control (Row-Level Locking)
In the backend (`app.py`), reservations are inserted inside a database transaction:
```python
conn.start_transaction()
# 1. Lock the room row to serialize concurrent booking attempts
cursor.execute("SELECT room_id FROM Room WHERE room_id = %s FOR UPDATE", (room_id,))
# 2. Insert reservation (trigger performs overlap validation)
cursor.execute("INSERT INTO Reservation (...) VALUES (...)")
conn.commit()
```
*Viva explanation:* `SELECT ... FOR UPDATE` acquires an exclusive row lock on the physical room row. If two staff members attempt to book the exact same room at the exact same instant, the second transaction is paused until the first finishes, avoiding race conditions.

---

## 📊 Sample Data Summary (2026)
- **Customers:** Priya Nair, Arjun Mehta, Sana Khan, Rahul Iyer, Meera Das
- **Room Types:** Standard (cap 2, ₹2000), Deluxe (cap 3, ₹3500), Suite (cap 4, ₹6000)
- **Core Rooms:** 101 & 102 (Standard), 201 & 202 (Deluxe), 301 (Suite)
- **Staff:** Kavya (Receptionist), Vikram (Manager)
- **Reservations & Payments:**
  - Priya Nair: 3 stays (Room 201 @ ₹7,000, Room 101 @ ₹6,000, Room 301 @ ₹12,000 = **₹25,000 total**)
  - Arjun Mehta: Room 201 for 3 nights = ₹10,500 (Paid ₹10,500 Cash)

---

## 🔍 The 4 SQL Queries (`queries.sql`)

### Query 1: Rooms free for a date range
```sql
SET @check_in = '2026-10-20';
SET @check_out = '2026-10-23';

SELECT rm.room_no, rt.type_name, rt.capacity, rt.price_per_night
FROM Room rm
JOIN RoomType rt ON rm.type_id = rt.type_id
WHERE NOT EXISTS (
    SELECT 1 FROM Reservation r
    WHERE r.room_id = rm.room_id
      AND r.status = 'Booked'
      AND @check_in < r.check_out
      AND @check_out > r.check_in
)
ORDER BY rm.room_no;
```

### Query 2: Customer booking history (Priya Nair)
```sql
SET @customer_name = 'Priya Nair';

SELECT 
    c.name AS customer_name,
    r.reservation_id,
    rm.room_no,
    rt.type_name,
    r.check_in,
    r.check_out,
    DATEDIFF(r.check_out, r.check_in) AS nights,
    rt.price_per_night,
    (DATEDIFF(r.check_out, r.check_in) * rt.price_per_night) AS stay_total,
    r.status
FROM Customer c
JOIN Reservation r ON c.customer_id = r.customer_id
JOIN Room rm ON r.room_id = rm.room_id
JOIN RoomType rt ON rm.type_id = rt.type_id
WHERE c.name = @customer_name
ORDER BY r.check_in;
```

### Query 3: Reservations with pending payments
```sql
SELECT 
    r.reservation_id,
    c.name AS customer_name,
    rm.room_no,
    r.check_in,
    r.check_out,
    (DATEDIFF(r.check_out, r.check_in) * rt.price_per_night) AS bill_total,
    COALESCE(SUM(p.amount), 0) AS total_paid,
    ((DATEDIFF(r.check_out, r.check_in) * rt.price_per_night) - COALESCE(SUM(p.amount), 0)) AS pending_amount
FROM Reservation r
JOIN Customer c ON r.customer_id = c.customer_id
JOIN Room rm ON r.room_id = rm.room_id
JOIN RoomType rt ON rm.type_id = rt.type_id
LEFT JOIN Payment p ON r.reservation_id = p.reservation_id
WHERE r.status <> 'Cancelled'
GROUP BY r.reservation_id, c.name, rm.room_no, r.check_in, r.check_out, rt.price_per_night
HAVING pending_amount > 0
ORDER BY r.check_in;
```

### Query 4: Occupancy on a given date
```sql
SET @target_date = '2026-10-20';

SELECT 
    COUNT(DISTINCT r.room_id) AS rooms_occupied,
    (SELECT COUNT(*) FROM Room) AS total_rooms,
    ROUND((COUNT(DISTINCT r.room_id) / (SELECT COUNT(*) FROM Room)) * 100, 2) AS occupancy_percentage
FROM Reservation r
WHERE r.status = 'Booked'
  AND r.check_in <= @target_date
  AND r.check_out > @target_date;
```

---

## ✅ Actual Verification Outputs (Step 1 Verification Checks)

### Check 1: Free rooms for 20-23 Oct 2026 are 202 and 301
**Command:**
```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -pPrisha@20 -e "USE hotel_reservation; SET @check_in = '2026-10-20'; SET @check_out = '2026-10-23'; SELECT rm.room_no, rt.type_name, rt.capacity, rt.price_per_night FROM Room rm JOIN RoomType rt ON rm.type_id = rt.type_id WHERE NOT EXISTS (SELECT 1 FROM Reservation r WHERE r.room_id = rm.room_id AND r.status = 'Booked' AND @check_in < r.check_out AND @check_out > r.check_in) ORDER BY rm.room_no;"
```
**Actual Output:**
```text
room_no    type_name    capacity    price_per_night
202        Deluxe       3           3500.00
301        Suite        4           6000.00
```
*(Exact match: Rooms 202 and 301 are free!)*

---

### Check 2: Booking room 201 for 20-21 Oct fails with the trigger message
**Command:**
```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -pPrisha@20 -e "USE hotel_reservation; INSERT INTO Reservation (customer_id, room_id, staff_id, check_in, check_out, status) VALUES (1, 3, 1, '2026-10-20', '2026-10-21', 'Booked');"
```
**Actual Output:**
```text
ERROR 1644 (45000) at line 1: Room already booked for these dates
```
*(Exact match: Trigger fires with SQLSTATE 45000 and custom error message!)*

---

### Check 3: Priya's history shows 3 stays totalling Rs 25,000
**Command:**
```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -pPrisha@20 -e "USE hotel_reservation; SET @customer_name = 'Priya Nair'; SELECT c.name AS customer_name, r.reservation_id, rm.room_no, rt.type_name, r.check_in, r.check_out, DATEDIFF(r.check_out, r.check_in) AS nights, rt.price_per_night, (DATEDIFF(r.check_out, r.check_in) * rt.price_per_night) AS stay_total, r.status FROM Customer c JOIN Reservation r ON c.customer_id = r.customer_id JOIN Room rm ON r.room_id = rm.room_id JOIN RoomType rt ON rm.type_id = rt.type_id WHERE c.name = @customer_name ORDER BY r.check_in; SELECT c.name AS customer_name, COUNT(r.reservation_id) AS total_stays, SUM(DATEDIFF(r.check_out, r.check_in) * rt.price_per_night) AS grand_total_amount FROM Customer c JOIN Reservation r ON c.customer_id = r.customer_id JOIN Room rm ON r.room_id = rm.room_id JOIN RoomType rt ON rm.type_id = rt.type_id WHERE c.name = @customer_name GROUP BY c.customer_id, c.name;"
```
**Actual Output:**
```text
customer_name  reservation_id  room_no  type_name  check_in    check_out   nights  price_per_night  stay_total  status
Priya Nair     6               201      Deluxe     2026-09-05  2026-09-07  2       3500.00          7000.00     Completed
Priya Nair     1               101      Standard   2026-10-18  2026-10-21  3       2000.00          6000.00     Booked
Priya Nair     4               301      Suite      2026-11-02  2026-11-04  2       6000.00          12000.00    Booked

customer_name  total_stays  grand_total_amount
Priya Nair     3            25000.00
```
*(Exact match: 3 stays totalling ₹25,000!)*

---

## 💻 Setup & Run Steps for Windows

### Step 1: Initialize Database in MySQL 8
Open PowerShell in the project directory:
```powershell
cd C:\Users\PRISHA\Downloads\hotel_reservation_dbms_complete

# 1. Run schema.sql to create database, 6 tables, indexes, and triggers:
Get-Content -Raw schema.sql | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p

# 2. Run sample_data.sql to load 2026 sample data:
Get-Content -Raw sample_data.sql | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
```
*(Enter your MySQL root password when prompted, e.g. `Prisha@20`)*

### Step 2: Configure Environment & Dependencies
```powershell
# Change into application directory
cd hotel_reservation_dbms

# Optional: Set your MySQL root password in the environment (defaults to Prisha@20)
$env:MYSQL_PASSWORD = "YourPasswordHere"
$env:FLASK_SECRET_KEY = "my-secret-key"

# Install Flask and MySQL connector
python -m pip install -r requirements.txt
```

### Step 3: Run the Flask Web Application
```powershell
python app.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

### Step 4: Run Automated Tests
```powershell
python tests\test_system.py
```
*(Runs 10 automated unit and integration tests verifying all database checks and web routes)*

---

## 🌐 Web Interface Pages

1. **Home (`/`)**:
   - Welcome banner and hotel introduction.
   - Live availability search by check-in and check-out dates (Query 1).
   - "Book This Room" shortcut passing selected room and dates to booking form.
2. **Rooms (`/rooms`)**:
   - Directory of all hotel rooms with floor number, guest capacity, and nightly rates.
3. **Book a Room (`/book`)**:
   - Dropdown selection of registered customers, rooms, and staff attendants.
   - Transaction with `SELECT ... FOR UPDATE` row locking.
   - Displays MySQL trigger conflict errors nicely in an error banner.
4. **Customers (`/customers`)**:
   - Table of all customers.
   - Instant search filter by name, phone, or email.
   - Form to add new customers.
   - "View History" link for each guest.
5. **Customer Booking History (`/customers/<id>/history`)**:
   - Detailed history breakdown (Query 2).
   - Shows nights, rate, calculated stay total, paid amount, and grand total billed.
6. **Payments & Reports (`/payments`)**:
   - **Occupancy Report (Query 4):** Live percentage and rooms occupied on any chosen date.
   - **Payment Entry:** Supports recording payments via Cash, Card, or UPI.
   - **Billing Accounts (Query 3):** Displays all reservations, calculated bill totals, amounts paid, and pending balances.
