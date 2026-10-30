"""
=============================================================================
HOTEL RESERVATION SYSTEM - Flask Backend (app.py)
College DBMS Project - Simple, Beginner-Friendly, Fully Commented
Stack: Python, Flask, MySQL 8 (mysql-connector-python)
No login system, No external frameworks, 100% Parameterized Queries.
=============================================================================
"""

import os
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error

# Initialize Flask application
app = Flask(__name__)
# Secret key used for secure session handling and flash messages
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "hotel-reservation-secret-key-2026")

# -----------------------------------------------------------------------------
# DATABASE CONNECTION CONFIGURATION
# Set MYSQL_PASSWORD in your environment, or it defaults to the local password.
# -----------------------------------------------------------------------------
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", "Prisha@20"),
    "database": os.environ.get("DB_NAME", "hotel_reservation"),
}


def get_db_connection():
    """
    Creates and returns a new MySQL database connection.
    Autocommit is disabled by default so we can control transactions explicitly.
    """
    return mysql.connector.connect(**DB_CONFIG)


def fetch_all(query, params=()):
    """
    Helper function to execute a SELECT query and return all matching rows as dictionaries.
    Uses parameterized queries (%s) to guarantee protection against SQL injection.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return rows
    finally:
        cursor.close()
        conn.close()


def fetch_one(query, params=()):
    """
    Helper function to execute a SELECT query and return a single row as a dictionary.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        row = cursor.fetchone()
        return row
    finally:
        cursor.close()
        conn.close()


def execute_action(query, params=()):
    """
    Helper function to execute an INSERT, UPDATE, or DELETE statement.
    Commits changes to the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()


# =============================================================================
# ROUTE 1: HOME PAGE (Hotel Info + Room Search by Date Range)
# =============================================================================
@app.route("/")
def home():
    """
    Displays the hotel homepage with hotel details and an availability search form.
    If search dates (check_in and check_out) are provided via GET query parameters,
    it runs Query 1 to find rooms with no overlapping 'Booked' reservations.
    """
    check_in_str = request.args.get("check_in", "").strip()
    check_out_str = request.args.get("check_out", "").strip()
    
    available_rooms = []
    search_performed = False

    if check_in_str and check_out_str:
        search_performed = True
        try:
            check_in_date = datetime.strptime(check_in_str, "%Y-%m-%d").date()
            check_out_date = datetime.strptime(check_out_str, "%Y-%m-%d").date()

            if check_out_date <= check_in_date:
                flash("Check-out date must be after check-in date.", "error")
            else:
                # QUERY 1: Rooms free for a date range (with type, capacity, price)
                # A room is free if there is NO existing Booked reservation where:
                # (check_in < existing.check_out AND check_out > existing.check_in)
                sql = """
                    SELECT 
                        rm.room_id,
                        rm.room_no,
                        rm.floor,
                        rt.type_name,
                        rt.capacity,
                        rt.price_per_night
                    FROM Room rm
                    JOIN RoomType rt ON rm.type_id = rt.type_id
                    WHERE NOT EXISTS (
                        SELECT 1 FROM Reservation r
                        WHERE r.room_id = rm.room_id
                          AND r.status = 'Booked'
                          AND %s < r.check_out
                          AND %s > r.check_in
                    )
                    ORDER BY rm.room_no
                """
                available_rooms = fetch_all(sql, (check_in_str, check_out_str))
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "error")

    return render_template(
        "index.html",
        check_in=check_in_str,
        check_out=check_out_str,
        available_rooms=available_rooms,
        search_performed=search_performed
    )


# =============================================================================
# ROUTE 2: ROOMS LIST
# =============================================================================
@app.route("/rooms")
def rooms():
    """
    Displays all rooms in the hotel along with their floor, room type,
    guest capacity, and nightly tariff.
    """
    sql = """
        SELECT 
            rm.room_id,
            rm.room_no,
            rm.floor,
            rt.type_name,
            rt.capacity,
            rt.price_per_night
        FROM Room rm
        JOIN RoomType rt ON rm.type_id = rt.type_id
        ORDER BY rm.room_no
    """
    all_rooms = fetch_all(sql)
    return render_template("rooms.html", rooms=all_rooms)


# =============================================================================
# ROUTE 3: BOOK A ROOM (Transaction + Row Lock + Trigger Handling)
# =============================================================================
@app.route("/book", methods=["GET", "POST"])
def book():
    """
    GET: Displays the reservation form populated with customers, rooms, and staff.
    POST: Processes the booking request inside a database transaction:
          1. Locks the room row (SELECT ... FOR UPDATE) to prevent race conditions.
          2. Inserts the reservation.
          3. If the MySQL BEFORE INSERT trigger detects an overlap, it throws
             SQLSTATE '45000' with 'Room already booked for these dates'.
          4. Catches the error and displays the message nicely in a flash banner.
    """
    if request.method == "POST":
        customer_id = request.form.get("customer_id")
        room_id = request.form.get("room_id")
        staff_id = request.form.get("staff_id")
        check_in = request.form.get("check_in")
        check_out = request.form.get("check_out")

        # Basic form validation
        if not (customer_id and room_id and staff_id and check_in and check_out):
            flash("All fields are required.", "error")
            return redirect(url_for("book", room_id=room_id, check_in=check_in, check_out=check_out))

        try:
            d_in = datetime.strptime(check_in, "%Y-%m-%d").date()
            d_out = datetime.strptime(check_out, "%Y-%m-%d").date()
            if d_out <= d_in:
                flash("Check-out date must be strictly after check-in date.", "error")
                return redirect(url_for("book", room_id=room_id, check_in=check_in, check_out=check_out))
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "error")
            return redirect(url_for("book"))

        # TRANSACTION WITH ROW-LEVEL LOCKING
        # Begins a transaction to serialize concurrent booking attempts on the same room.
        conn = get_db_connection()
        try:
            conn.start_transaction()
            cursor = conn.cursor(dictionary=True)

            # Step 1: Lock the Room row using SELECT ... FOR UPDATE
            # Any concurrent booking for this specific room waits here until this transaction finishes.
            lock_sql = "SELECT room_id, room_no FROM Room WHERE room_id = %s FOR UPDATE"
            cursor.execute(lock_sql, (room_id,))
            locked_room = cursor.fetchone()

            if not locked_room:
                conn.rollback()
                flash("Selected room does not exist.", "error")
                return redirect(url_for("book"))

            # Step 2: Attempt to insert the reservation
            # If dates overlap an existing 'Booked' reservation, the BEFORE INSERT trigger
            # fires: SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Room already booked for these dates'
            insert_sql = """
                INSERT INTO Reservation (customer_id, room_id, staff_id, check_in, check_out, status)
                VALUES (%s, %s, %s, %s, %s, 'Booked')
            """
            cursor.execute(insert_sql, (customer_id, room_id, staff_id, check_in, check_out))

            # Step 3: Commit transaction
            conn.commit()
            flash(f"Reservation successfully booked for Room {locked_room['room_no']}!", "success")
            return redirect(url_for("payments"))

        except Error as err:
            # Rollback any uncommitted changes on failure
            conn.rollback()
            # Capture the trigger error message or database exception
            # MySQL trigger message: 'Room already booked for these dates'
            flash(f"Booking Error: {err.msg}", "error")
            return redirect(url_for("book", room_id=room_id, check_in=check_in, check_out=check_out))

        finally:
            cursor.close()
            conn.close()

    # GET Request: Fetch dropdown options
    customers = fetch_all("SELECT customer_id, name, phone, email FROM Customer ORDER BY name")
    rooms_list = fetch_all("""
        SELECT rm.room_id, rm.room_no, rt.type_name, rt.price_per_night
        FROM Room rm JOIN RoomType rt ON rm.type_id = rt.type_id
        ORDER BY rm.room_no
    """)
    staff_list = fetch_all("SELECT staff_id, name, role FROM Staff ORDER BY name")

    # Pre-selection from query params (e.g. from Home search result)
    selected_room_id = request.args.get("room_id", type=int)
    default_check_in = request.args.get("check_in", "")
    default_check_out = request.args.get("check_out", "")

    return render_template(
        "book.html",
        customers=customers,
        rooms=rooms_list,
        staff=staff_list,
        selected_room_id=selected_room_id,
        default_check_in=default_check_in,
        default_check_out=default_check_out
    )


# =============================================================================
# ROUTE 4: CUSTOMERS (List, Search, Add)
# =============================================================================
@app.route("/customers", methods=["GET", "POST"])
def customers():
    """
    Handles customer directory:
    - POST: Adds a new customer into the Customer table.
    - GET: Displays all customers or filters by search term (name, phone, email).
    """
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()

        if not name:
            flash("Customer name is required.", "error")
        else:
            try:
                execute_action(
                    "INSERT INTO Customer (name, phone, email) VALUES (%s, %s, %s)",
                    (name, phone if phone else None, email if email else None)
                )
                flash(f"Customer '{name}' added successfully!", "success")
                return redirect(url_for("customers"))
            except Error as err:
                flash(f"Could not add customer: {err.msg}", "error")

    # Search filter
    search_query = request.args.get("q", "").strip()
    if search_query:
        # Search by name, phone, or email using LIKE
        like_term = f"%{search_query}%"
        sql = """
            SELECT customer_id, name, phone, email
            FROM Customer
            WHERE name LIKE %s OR phone LIKE %s OR email LIKE %s
            ORDER BY customer_id DESC
        """
        customer_list = fetch_all(sql, (like_term, like_term, like_term))
    else:
        customer_list = fetch_all("SELECT customer_id, name, phone, email FROM Customer ORDER BY customer_id")

    return render_template("customers.html", customers=customer_list, search_query=search_query)


# =============================================================================
# ROUTE 5: CUSTOMER BOOKING HISTORY
# =============================================================================
@app.route("/customers/<int:customer_id>/history")
def customer_history(customer_id):
    """
    Displays the complete booking history of a customer (Query 2).
    Calculates stay total as: nights x price_per_night.
    Shows grand total across all stays.
    """
    customer = fetch_one("SELECT customer_id, name, phone, email FROM Customer WHERE customer_id = %s", (customer_id,))
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for("customers"))

    # QUERY 2: Booking history for one customer
    history_sql = """
        SELECT 
            r.reservation_id,
            rm.room_no,
            rt.type_name,
            r.check_in,
            r.check_out,
            DATEDIFF(r.check_out, r.check_in) AS nights,
            rt.price_per_night,
            (DATEDIFF(r.check_out, r.check_in) * rt.price_per_night) AS stay_total,
            r.status,
            COALESCE(SUM(p.amount), 0) AS amount_paid
        FROM Reservation r
        JOIN Room rm ON r.room_id = rm.room_id
        JOIN RoomType rt ON rm.type_id = rt.type_id
        LEFT JOIN Payment p ON r.reservation_id = p.reservation_id
        WHERE r.customer_id = %s
        GROUP BY r.reservation_id, rm.room_no, rt.type_name, r.check_in, r.check_out, rt.price_per_night, r.status
        ORDER BY r.check_in DESC
    """
    stays = fetch_all(history_sql, (customer_id,))

    # Calculate grand total across stays
    grand_total = sum(stay["stay_total"] for stay in stays)
    total_paid = sum(stay["amount_paid"] for stay in stays)

    return render_template(
        "history.html",
        customer=customer,
        stays=stays,
        grand_total=grand_total,
        total_paid=total_paid
    )


# =============================================================================
# ROUTE 6: PAYMENTS & REPORTS (Occupancy, Bills, Payment Entry)
# =============================================================================
@app.route("/payments", methods=["GET", "POST"])
def payments():
    """
    GET:
      - Query 4: Occupancy report on a given date (default today).
      - Query 3: Reservation billing & pending payments overview.
      - Dropdown list for recording new payments.
    POST:
      - Records a payment in the Payment table (Cash, Card, or UPI).
    """
    if request.method == "POST":
        reservation_id = request.form.get("reservation_id")
        amount = request.form.get("amount")
        mode = request.form.get("mode")
        pay_date = request.form.get("pay_date")

        if not (reservation_id and amount and mode and pay_date):
            flash("All payment fields are required.", "error")
        else:
            try:
                amt = float(amount)
                if amt <= 0:
                    flash("Payment amount must be greater than zero.", "error")
                elif mode not in ("Cash", "Card", "UPI"):
                    flash("Payment mode must be Cash, Card, or UPI.", "error")
                else:
                    execute_action(
                        """INSERT INTO Payment (reservation_id, amount, mode, pay_date)
                           VALUES (%s, %s, %s, %s)""",
                        (reservation_id, amt, mode, pay_date)
                    )
                    flash(f"Payment of ₹{amt:,.2f} recorded via {mode}!", "success")
                    return redirect(url_for("payments"))
            except ValueError:
                flash("Invalid payment amount.", "error")
            except Error as err:
                flash(f"Payment error: {err.msg}", "error")

    # Selected date for Occupancy Report (Query 4)
    target_date_str = request.args.get("occupancy_date", "").strip()
    if not target_date_str:
        # Default to 2026-10-20 to match sample dataset demonstration, or current date
        target_date_str = "2026-10-20"

    # QUERY 4: Occupancy on a given date
    occupancy_sql = """
        SELECT 
            COUNT(DISTINCT r.room_id) AS rooms_occupied,
            (SELECT COUNT(*) FROM Room) AS total_rooms
        FROM Reservation r
        WHERE r.status = 'Booked'
          AND r.check_in <= %s
          AND r.check_out > %s
    """
    occ_data = fetch_one(occupancy_sql, (target_date_str, target_date_str))
    occupied = occ_data["rooms_occupied"] if occ_data else 0
    total = occ_data["total_rooms"] if occ_data and occ_data["total_rooms"] else 1
    occupancy_percent = round((occupied / total) * 100, 1)

    # QUERY 3: Financial & Pending Payments Status
    # Calculates derived bill total: DATEDIFF(check_out, check_in) * price_per_night
    # Calculates paid: SUM(p.amount)
    # Calculates pending: bill_total - paid
    reports_sql = """
        SELECT 
            r.reservation_id,
            c.name AS customer_name,
            rm.room_no,
            rt.type_name,
            r.check_in,
            r.check_out,
            r.status,
            DATEDIFF(r.check_out, r.check_in) AS nights,
            (DATEDIFF(r.check_out, r.check_in) * rt.price_per_night) AS bill_total,
            COALESCE(SUM(p.amount), 0) AS total_paid,
            ((DATEDIFF(r.check_out, r.check_in) * rt.price_per_night) - COALESCE(SUM(p.amount), 0)) AS pending_amount
        FROM Reservation r
        JOIN Customer c ON r.customer_id = c.customer_id
        JOIN Room rm ON r.room_id = rm.room_id
        JOIN RoomType rt ON rm.type_id = rt.type_id
        LEFT JOIN Payment p ON r.reservation_id = p.reservation_id
        WHERE r.status <> 'Cancelled'
        GROUP BY r.reservation_id, c.name, rm.room_no, rt.type_name, r.check_in, r.check_out, r.status, rt.price_per_night
        ORDER BY r.check_in DESC
    """
    reservation_reports = fetch_all(reports_sql)

    # Active reservations list for payment dropdown
    active_reservations = [r for r in reservation_reports if r["pending_amount"] > 0]

    return render_template(
        "payments.html",
        occupancy_date=target_date_str,
        rooms_occupied=occupied,
        total_rooms=total,
        occupancy_percent=occupancy_percent,
        reports=reservation_reports,
        active_reservations=active_reservations,
        today_date=date.today().strftime("%Y-%m-%d")
    )


# =============================================================================
# ROUTE 7: CANCEL RESERVATION (Optional status update)
# =============================================================================
@app.route("/reservation/<int:reservation_id>/cancel", methods=["POST"])
def cancel_reservation(reservation_id):
    """
    Updates the reservation status to 'Cancelled'.
    Releases the room for other guests.
    """
    try:
        execute_action(
            "UPDATE Reservation SET status = 'Cancelled' WHERE reservation_id = %s",
            (reservation_id,)
        )
        flash(f"Reservation #{reservation_id} has been cancelled.", "success")
    except Error as err:
        flash(f"Error cancelling reservation: {err.msg}", "error")

    return redirect(url_for("payments"))


# -----------------------------------------------------------------------------
# APPLICATION ENTRYPOINT
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Run development server on port 5000
    print("Hotel Reservation System running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
