from datetime import date, datetime, timedelta
from functools import wraps
import hmac
import os
import re
import secrets
from decimal import Decimal
from urllib.parse import urlsplit
from flask import Flask, abort, render_template, request, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("Set FLASK_SECRET_KEY before starting the application.")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

# Set these environment variables in the terminal before starting the app.
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "hotel_reservation"),
}


def get_connection():
    if "MYSQL_PASSWORD" not in os.environ:
        raise RuntimeError("Set MYSQL_PASSWORD before connecting to MySQL.")
    database_config = DB_CONFIG.copy()
    database_config["password"] = os.environ["MYSQL_PASSWORD"]
    return mysql.connector.connect(**database_config)


def fetch_all(sql, params=()):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def nights_between(check_in, check_out):
    return (check_out - check_in).days


def valid_phone(phone):
    return bool(phone and phone.upper() != "PENDING"
                and re.fullmatch(r"\+?[0-9]{10,15}", phone))


def available_rooms(type_id, check_in, check_out):
    """Return rooms of a type with no overlapping Booked reservations."""
    return fetch_all(
        """SELECT rm.room_id, rm.room_no, rt.type_id, rt.type_name,
                  rt.capacity, rt.price_per_night
           FROM Room rm JOIN RoomType rt ON rt.type_id = rm.type_id
           WHERE rm.type_id = %s
             AND NOT EXISTS (
                 SELECT 1 FROM Reservation r
                 WHERE r.room_id = rm.room_id
                   AND r.status = 'Booked'
                   AND %s < r.check_out
                   AND %s > r.check_in
             )
           ORDER BY rm.room_no""",
        (type_id, check_in, check_out))


def nearest_available_dates(type_id, check_in, check_out, limit=3, max_offset=14):
    """Find nearest available date windows, testing +n then -n for each n."""
    stay_length = nights_between(check_in, check_out)
    if stay_length <= 0:
        return []

    suggestions = []
    for offset in range(1, max_offset + 1):
        for signed_offset in (offset, -offset):
            suggested_in = check_in + timedelta(days=signed_offset)
            suggested_out = suggested_in + timedelta(days=stay_length)
            rooms = available_rooms(type_id, suggested_in, suggested_out)
            if rooms:
                suggestions.append({
                    "check_in": suggested_in,
                    "check_out": suggested_out,
                    "room_id": rooms[0]["room_id"],
                    "room_no": rooms[0]["room_no"],
                })
                if len(suggestions) == limit:
                    return suggestions
    return suggestions


def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("login", next=request.full_path))
        return view_function(*args, **kwargs)

    return wrapped_view


def admin_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("login", next=request.full_path))
        if session.get("role") != "admin":
            abort(403)
        return view_function(*args, **kwargs)

    return wrapped_view


@app.before_request
def protect_post_requests():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    if request.method == "POST":
        submitted_token = request.form.get("csrf_token", "")
        if not hmac.compare_digest(session["_csrf_token"], submitted_token):
            abort(400)


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": session.get("_csrf_token", "")}


def safe_local_redirect(target):
    parts = urlsplit(target or "")
    if (parts.scheme or parts.netloc or not parts.path.startswith("/")
            or target.startswith("//") or "\\" in target):
        return None
    return target


@app.errorhandler(403)
def access_denied(_error):
    return render_template("access_denied.html"), 403


@app.errorhandler(400)
def bad_request(_error):
    return render_template("bad_request.html"), 400


@app.route("/")
def home():
    room_types = fetch_all(
        "SELECT type_id, type_name FROM RoomType ORDER BY type_id")
    rooms = []
    suggestions = []
    check_in = request.args.get("check_in", "")
    check_out = request.args.get("check_out", "")
    type_id = request.args.get("type_id", type=int)
    if check_in and check_out and type_id:
        try:
            start = date.fromisoformat(check_in)
            end = date.fromisoformat(check_out)
            if end > start:
                rooms = available_rooms(type_id, start, end)
                if not rooms:
                    suggestions = nearest_available_dates(type_id, start, end)
        except ValueError:
            flash("Enter valid check-in and check-out dates.", "error")
    return render_template(
        "index.html", rooms=rooms, room_types=room_types, type_id=type_id,
        suggestions=suggestions, check_in=check_in, check_out=check_out)


@app.route("/rooms")
def rooms():
    rows = fetch_all("""SELECT rm.room_id, rm.room_no, rm.floor, rt.type_name,
                              rt.capacity, rt.price_per_night
                       FROM Room rm JOIN RoomType rt ON rt.type_id = rm.type_id
                       ORDER BY rm.room_no""")
    return render_template("rooms.html", rooms=rows)


@app.route("/admin")
@admin_required
def admin_dashboard():
    summary_rows = fetch_all(
        """SELECT
               (SELECT COUNT(*) FROM Reservation) AS reservation_count,
               (SELECT COUNT(*) FROM Reservation WHERE status = 'Booked') AS booked_count,
               (SELECT COUNT(*) FROM Customer) AS customer_count,
               (SELECT COUNT(*) FROM Staff) AS staff_count,
               (SELECT COUNT(*) FROM Review) AS review_count""")
    return render_template("admin_dashboard.html", summary=summary_rows[0])


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        users = fetch_all(
            """SELECT user_id, username, password_hash, role, customer_id
               FROM `User` WHERE username = %s""",
            (username,))
        if not users or not check_password_hash(users[0]["password_hash"], password):
            flash("Incorrect username or password.", "error")
            return render_template("login.html")

        user = users[0]
        session.clear()
        session["user_id"] = user["user_id"]
        session["role"] = user["role"]
        if user["customer_id"] is not None:
            session["customer_id"] = user["customer_id"]
        session["_csrf_token"] = secrets.token_urlsafe(32)
        flash("You are now logged in.", "success")
        next_url = safe_local_redirect(request.form.get("next", ""))
        if next_url:
            return redirect(next_url)
        if user["role"] == "admin":
            return redirect(url_for("home"))
        return redirect(url_for("history"))
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip() or None
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        password_confirmation = request.form.get("password_confirmation", "")

        if not username or len(username) > 80:
            flash("Username is required and must be 80 characters or fewer.", "error")
        elif not name or len(name) > 100:
            flash("Name is required and must be 100 characters or fewer.", "error")
        elif email and len(email) > 120:
            flash("Email must be 120 characters or fewer.", "error")
        elif not valid_phone(phone):
            flash("Enter a phone number with 10 to 15 digits and an optional leading +.", "error")
        elif len(password) < 8 or len(password) > 256:
            flash("Password must be between 8 and 256 characters.", "error")
        elif password != password_confirmation:
            flash("The password confirmation does not match.", "error")
        else:
            connection = None
            cursor = None
            try:
                connection = get_connection()
                cursor = connection.cursor()
                connection.start_transaction()
                cursor.execute(
                    "INSERT INTO Customer (name, phone, email) VALUES (%s, %s, %s)",
                    (name, phone, email))
                customer_id = cursor.lastrowid
                cursor.execute(
                    """INSERT INTO `User`
                       (username, password_hash, role, customer_id)
                       VALUES (%s, %s, 'customer', %s)""",
                    (username, generate_password_hash(password), customer_id))
                connection.commit()
                flash("Registration complete. Please log in.", "success")
                return redirect(url_for("login"))
            except Error as error:
                if connection:
                    connection.rollback()
                if error.errno == 1062:
                    flash("That username or email is already registered.", "error")
                else:
                    app.logger.exception("Customer registration failed.")
                    flash("Registration could not be completed due to a database error.", "error")
            finally:
                if cursor:
                    cursor.close()
                if connection:
                    connection.close()
        return render_template("register.html")
    return render_template("register.html")


@app.route("/book", methods=["GET", "POST"])
@login_required
def book():
    if session.get("role") == "admin":
        customers = fetch_all(
            "SELECT customer_id, name, phone FROM Customer ORDER BY name")
    else:
        customers = fetch_all(
            """SELECT customer_id, name, phone FROM Customer
               WHERE customer_id = %s""",
            (session.get("customer_id"),))
    room_rows = fetch_all("""SELECT rm.room_id, rm.room_no, rt.type_name, rt.price_per_night
                             FROM Room rm JOIN RoomType rt ON rt.type_id = rm.type_id
                             ORDER BY rm.room_no""")
    staff = fetch_all("SELECT staff_id, name FROM Staff ORDER BY name")
    form_values = request.form if request.method == "POST" else request.args
    if request.method == "POST":
        customer_id = request.form.get("customer_id", type=int)
        room_id = request.form.get("room_id", type=int)
        staff_id = request.form.get("staff_id", type=int)
        check_in_text = request.form.get("check_in", "")
        check_out_text = request.form.get("check_out", "")
        phone = request.form.get("phone", "").strip()
        if phone.upper() == "PENDING":
            flash("PENDING is only a placeholder. Enter the customer's real phone number.", "error")
            return render_template(
                "book.html", customers=customers, rooms=room_rows, staff=staff,
                form_values=form_values)
        if not valid_phone(phone):
            flash("Enter a phone number with 10 to 15 digits and an optional leading +.", "error")
            return render_template(
                "book.html", customers=customers, rooms=room_rows, staff=staff,
                form_values=form_values)
        try:
            if not customer_id or not room_id or not staff_id:
                raise ValueError("Choose a customer, room, and staff member.")
            check_in = date.fromisoformat(check_in_text)
            check_out = date.fromisoformat(check_out_text)
            if check_out <= check_in:
                flash("Check-out must be after check-in.", "error")
                return render_template(
                    "book.html", customers=customers, rooms=room_rows, staff=staff,
                    form_values=form_values)
            connection = get_connection()
            cursor = connection.cursor()
            try:
                # Lock the room row so two booking requests cannot check it simultaneously.
                connection.start_transaction()
                cursor.execute("SELECT room_id FROM Room WHERE room_id = %s FOR UPDATE", (room_id,))
                if cursor.fetchone() is None:
                    raise ValueError("Please choose a valid room.")
                cursor.execute(
                    "SELECT phone FROM Customer WHERE customer_id = %s FOR UPDATE",
                    (customer_id,))
                customer_row = cursor.fetchone()
                if customer_row is None:
                    raise ValueError("Please choose a valid customer.")
                if session.get("role") != "admin" and customer_id != session.get("customer_id"):
                    abort(403)
                stored_phone = (customer_row[0] or "").strip()
                if stored_phone != phone:
                    if session.get("role") != "admin" or request.form.get("confirm_phone_update") != "yes":
                        raise ValueError(
                            "This customer's phone differs from the saved number. "
                            "An admin must confirm the phone update before booking.")
                    cursor.execute(
                        """SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                           WHERE TABLE_SCHEMA = DATABASE()
                             AND TABLE_NAME = 'Customer'
                             AND COLUMN_NAME = 'phone_needs_update'""")
                    has_phone_flag = cursor.fetchone()[0] > 0
                    if has_phone_flag:
                        cursor.execute(
                            """UPDATE Customer
                               SET phone = %s, phone_needs_update = 0
                               WHERE customer_id = %s""",
                            (phone, customer_id))
                    else:
                        cursor.execute(
                            "UPDATE Customer SET phone = %s WHERE customer_id = %s",
                            (phone, customer_id))
                cursor.execute(
                    """INSERT INTO Reservation
                       (customer_id, room_id, staff_id, check_in, check_out, status)
                       VALUES (%s, %s, %s, %s, %s, 'Booked')""",
                    (customer_id, room_id, staff_id, check_in, check_out))
                connection.commit()
                flash("Booking created successfully!", "success")
                if session.get("role") == "admin":
                    return redirect(url_for("reservations"))
                return redirect(url_for("history"))
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()
                connection.close()
        except Error as error:
            if "Room already booked for these dates" in str(error):
                flash("Room already booked for these dates. Please choose another room or dates.", "error")
            else:
                app.logger.exception("Booking failed due to a database error.")
                flash("The booking could not be saved because of a database error.", "error")
        except (ValueError, TypeError) as error:
            flash("Please check the dates and selections: " + str(error), "error")
    return render_template(
        "book.html", customers=customers, rooms=room_rows, staff=staff,
        form_values=form_values)


@app.route("/customers", methods=["GET", "POST"])
@admin_required
def customers():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip() or None
        email = request.form.get("email", "").strip() or None
        if not name:
            flash("Customer name is required.", "error")
        else:
            connection = get_connection()
            cursor = connection.cursor()
            try:
                cursor.execute("INSERT INTO Customer (name, phone, email) VALUES (%s, %s, %s)",
                               (name, phone, email))
                connection.commit()
                flash("Customer added.", "success")
                return redirect(url_for("customers"))
            except Error as error:
                connection.rollback()
                flash("Could not add customer: " + str(error), "error")
            finally:
                cursor.close()
                connection.close()
    search = request.args.get("search", "").strip()
    rows = fetch_all("""SELECT customer_id, name, phone, email FROM Customer
                       WHERE name LIKE %s OR COALESCE(email, '') LIKE %s
                       ORDER BY name""", ("%" + search + "%", "%" + search + "%"))
    selected_id = request.args.get("customer_id", type=int)
    history = []
    selected_customer = None
    if selected_id:
        selected = fetch_all("SELECT customer_id, name FROM Customer WHERE customer_id = %s", (selected_id,))
        if selected:
            selected_customer = selected[0]
            history = fetch_all("""SELECT r.reservation_id, rm.room_no, r.check_in, r.check_out, r.status,
                                       DATEDIFF(r.check_out, r.check_in) AS nights,
                                       rt.price_per_night,
                                       DATEDIFF(r.check_out, r.check_in) * rt.price_per_night AS total
                                FROM Reservation r JOIN Room rm ON rm.room_id = r.room_id
                                JOIN RoomType rt ON rt.type_id = rm.type_id
                                WHERE r.customer_id = %s ORDER BY r.check_in DESC""", (selected_id,))
    return render_template("customers.html", customers=rows, search=search,
                           history=history, selected_customer=selected_customer)


@app.route("/history")
@login_required
def history():
    if session.get("role") != "customer":
        return redirect(url_for("reservations"))
    customer_id = session.get("customer_id")
    customer_rows = fetch_all(
        "SELECT customer_id, name FROM Customer WHERE customer_id = %s",
        (customer_id,))
    if not customer_rows:
        abort(403)
    rows = fetch_all(
        """SELECT r.reservation_id, rm.room_no, r.check_in, r.check_out, r.status,
                  DATEDIFF(r.check_out, r.check_in) AS nights,
                  rt.type_name, rt.price_per_night,
                  DATEDIFF(r.check_out, r.check_in) * rt.price_per_night AS total,
                  rv.review_id, rv.rating, rv.comment
           FROM Reservation r
           JOIN Room rm ON rm.room_id = r.room_id
           JOIN RoomType rt ON rt.type_id = rm.type_id
           LEFT JOIN Review rv ON rv.reservation_id = r.reservation_id
           WHERE r.customer_id = %s
           ORDER BY r.check_in DESC""",
        (customer_id,))
    return render_template(
        "history.html", customer=customer_rows[0], history=rows,
        cancel_after=date.today() + timedelta(days=1))


@app.route("/reservations")
@admin_required
def reservations():
    rows = fetch_all(
        """SELECT r.reservation_id, c.name, rm.room_no, rt.type_name,
                  r.check_in, r.check_out, r.status, r.cancel_reason,
                  r.cancelled_by
           FROM Reservation r
           JOIN Customer c ON c.customer_id = r.customer_id
           JOIN Room rm ON rm.room_id = r.room_id
           JOIN RoomType rt ON rt.type_id = rm.type_id
           ORDER BY r.check_in DESC, r.reservation_id DESC""")
    return render_template("reservations.html", reservations=rows)


@app.route("/reservations/<int:reservation_id>/cancel", methods=["POST"])
@login_required
def cancel_reservation(reservation_id):
    role = session.get("role")
    if role not in ("admin", "customer"):
        abort(403)
    reason = request.form.get("cancel_reason", "").strip()
    if role == "admin" and (not reason or len(reason) > 255):
        flash("Admins must enter a cancellation reason of 255 characters or fewer.", "error")
        return redirect(url_for("reservations"))

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        connection.start_transaction()
        if role == "admin":
            cursor.execute(
                """SELECT status, check_in FROM Reservation
                   WHERE reservation_id = %s FOR UPDATE""",
                (reservation_id,))
        else:
            cursor.execute(
                """SELECT status, check_in FROM Reservation
                   WHERE reservation_id = %s AND customer_id = %s FOR UPDATE""",
                (reservation_id, session.get("customer_id")))
        reservation = cursor.fetchone()
        if reservation is None:
            abort(403)
        if reservation[0] != "Booked":
            flash("Only booked reservations can be cancelled.", "error")
            return redirect(url_for("reservations" if role == "admin" else "history"))
        check_in = reservation[1]
        if isinstance(check_in, datetime):
            check_in = check_in.date()
        elif isinstance(check_in, str):
            check_in = date.fromisoformat(check_in)
        if role == "customer" and check_in < date.today() + timedelta(days=1):
            flash("Reservations can only be cancelled at least one day before check-in.", "error")
            return redirect(url_for("history"))

        if role == "admin":
            cursor.execute(
                """UPDATE Reservation
                   SET status = 'Cancelled', cancel_reason = %s, cancelled_by = 'admin'
                   WHERE reservation_id = %s AND status = 'Booked'""",
                (reason, reservation_id))
        else:
            cursor.execute(
                """UPDATE Reservation
                   SET status = 'Cancelled', cancelled_by = 'customer'
                   WHERE reservation_id = %s AND customer_id = %s AND status = 'Booked'""",
                (reservation_id, session.get("customer_id")))
        if cursor.rowcount != 1:
            connection.rollback()
            flash("This reservation was already changed; refresh and try again.", "error")
            return redirect(url_for("reservations" if role == "admin" else "history"))
        connection.commit()
        flash("Reservation cancelled.", "success")
    except Error:
        if connection:
            connection.rollback()
        app.logger.exception("Reservation cancellation failed.")
        flash("The reservation could not be cancelled due to a database error.", "error")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    return redirect(url_for("reservations" if role == "admin" else "history"))


@app.route("/reviews", methods=["GET", "POST"])
@login_required
def reviews():
    if session.get("role") == "admin":
        review_rows = fetch_all(
            """SELECT rv.review_id, rv.reservation_id, rv.rating, rv.comment,
                      rv.created_at, c.name, rm.room_no, rt.type_name
               FROM Review rv
               JOIN Reservation r ON r.reservation_id = rv.reservation_id
               JOIN Customer c ON c.customer_id = rv.customer_id
               JOIN Room rm ON rm.room_id = r.room_id
               JOIN RoomType rt ON rt.type_id = rm.type_id
               ORDER BY rv.created_at DESC, rv.review_id DESC""")
        averages = fetch_all(
            """SELECT rt.type_name, AVG(rv.rating) AS average_rating,
                      COUNT(rv.review_id) AS review_count
               FROM RoomType rt
               LEFT JOIN Room rm ON rm.type_id = rt.type_id
               LEFT JOIN Reservation r ON r.room_id = rm.room_id
               LEFT JOIN Review rv ON rv.reservation_id = r.reservation_id
               GROUP BY rt.type_id, rt.type_name
               ORDER BY rt.type_name""")
        return render_template(
            "reviews.html", reviews=review_rows, averages=averages)
    abort(403)


@app.route("/reviews/submit", methods=["POST"])
@login_required
def submit_review():
    if session.get("role") != "customer":
        abort(403)
    reservation_id = request.form.get("reservation_id", type=int)
    rating_text = request.form.get("rating", "")
    comment = request.form.get("comment", "").strip()
    try:
        rating = int(rating_text)
    except ValueError:
        rating = 0
    if not reservation_id or rating < 1 or rating > 5 or len(comment) > 500:
        flash("Choose a rating from 1 to 5 and keep the comment within 500 characters.", "error")
        return redirect(url_for("history"))

    eligible = fetch_all(
        """SELECT reservation_id FROM Reservation
           WHERE reservation_id = %s AND customer_id = %s AND status = 'Completed'""",
        (reservation_id, session.get("customer_id")))
    if not eligible:
        flash("A review can only be submitted for your completed stay.", "error")
        return redirect(url_for("history"))

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO Review (reservation_id, customer_id, rating, comment)
               VALUES (%s, %s, %s, %s)""",
            (reservation_id, session.get("customer_id"), rating, comment or None))
        connection.commit()
        flash("Thank you for sharing your review.", "success")
    except Error as error:
        if connection:
            connection.rollback()
        if error.errno == 1062:
            flash("You have already reviewed this stay.", "error")
        else:
            app.logger.exception("Review submission failed.")
            flash("Your review could not be saved due to a database error.", "error")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    return redirect(url_for("history"))


@app.route("/payments", methods=["GET", "POST"])
@admin_required
def payments():
    if request.method == "POST":
        reservation_id = request.form.get("reservation_id", type=int)
        amount_text = request.form.get("amount", "")
        mode = request.form.get("mode", "")
        pay_date = request.form.get("pay_date", "")
        try:
            amount = Decimal(amount_text)
            if amount <= 0:
                raise ValueError("Payment amount must be greater than zero.")
            date.fromisoformat(pay_date)
            connection = get_connection()
            cursor = connection.cursor()
            try:
                cursor.execute("INSERT INTO Payment (reservation_id, amount, mode, pay_date) VALUES (%s, %s, %s, %s)",
                               (reservation_id, amount, mode, pay_date))
                connection.commit()
                flash("Payment recorded.", "success")
                return redirect(url_for("payments"))
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()
                connection.close()
        except (ValueError, Error) as error:
            flash("Could not record payment: " + str(error), "error")
    reservations = fetch_all("""SELECT r.reservation_id, c.name, rm.room_no,
                                     DATEDIFF(r.check_out, r.check_in) * rt.price_per_night AS bill_total
                              FROM Reservation r JOIN Customer c ON c.customer_id = r.customer_id
                              JOIN Room rm ON rm.room_id = r.room_id
                              JOIN RoomType rt ON rt.type_id = rm.type_id
                              WHERE r.status <> 'Cancelled' ORDER BY r.reservation_id DESC""")
    rows = fetch_all("""SELECT r.reservation_id, c.name, rm.room_no,
                             DATEDIFF(r.check_out, r.check_in) * rt.price_per_night AS bill_total,
                             COALESCE(SUM(p.amount), 0) AS paid,
                             DATEDIFF(r.check_out, r.check_in) * rt.price_per_night - COALESCE(SUM(p.amount), 0) AS pending
                      FROM Reservation r JOIN Customer c ON c.customer_id = r.customer_id
                      JOIN Room rm ON rm.room_id = r.room_id JOIN RoomType rt ON rt.type_id = rm.type_id
                      LEFT JOIN Payment p ON p.reservation_id = r.reservation_id
                      WHERE r.status <> 'Cancelled'
                      GROUP BY r.reservation_id, c.name, rm.room_no, r.check_in, r.check_out, rt.price_per_night
                      ORDER BY r.reservation_id DESC""")
    occupancy = fetch_all("""SELECT COUNT(DISTINCT r.room_id) AS occupied,
                                   (SELECT COUNT(*) FROM Room) AS total
                            FROM Reservation r WHERE r.status = 'Booked'
                              AND r.check_in <= CURDATE() AND r.check_out > CURDATE()""")[0]
    return render_template("payments.html", reservations=reservations, payments=rows, occupancy=occupancy,
                           today=date.today().isoformat())


@app.route("/staff")
@admin_required
def staff():
    staff_rows = fetch_all(
        "SELECT staff_id, name, role, phone FROM Staff ORDER BY name, staff_id")
    return render_template("staff.html", staff=staff_rows)


@app.route("/staff/add", methods=["POST"])
@admin_required
def add_staff():
    name = request.form.get("name", "").strip()
    role = request.form.get("role", "").strip()
    phone = request.form.get("phone", "").strip() or None
    if not name or len(name) > 100 or not role or len(role) > 40 or (phone and len(phone) > 20):
        flash("Enter a name and role, and keep each field within its allowed length.", "error")
        return redirect(url_for("staff"))

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO Staff (name, role, phone) VALUES (%s, %s, %s)",
            (name, role, phone))
        connection.commit()
        flash("Staff member added.", "success")
    except Error:
        if connection:
            connection.rollback()
        flash("Could not add the staff member because of a database error.", "error")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    return redirect(url_for("staff"))


@app.route("/staff/<int:staff_id>/edit", methods=["POST"])
@admin_required
def edit_staff(staff_id):
    role = request.form.get("role", "").strip()
    phone = request.form.get("phone", "").strip() or None
    if not role or len(role) > 40 or (phone and len(phone) > 20):
        flash("Enter a role of 40 characters or fewer and a phone of 20 characters or fewer.", "error")
        return redirect(url_for("staff"))

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT staff_id FROM Staff WHERE staff_id = %s", (staff_id,))
        if cursor.fetchone() is None:
            flash("That staff member was not found.", "error")
            return redirect(url_for("staff"))
        cursor.execute(
            "UPDATE Staff SET role = %s, phone = %s WHERE staff_id = %s",
            (role, phone, staff_id))
        connection.commit()
        flash("Staff member updated.", "success")
    except Error:
        if connection:
            connection.rollback()
        flash("Could not update the staff member because of a database error.", "error")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    return redirect(url_for("staff"))


@app.route("/staff/<int:staff_id>/delete", methods=["POST"])
@admin_required
def delete_staff(staff_id):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM Reservation WHERE staff_id = %s",
            (staff_id,))
        if cursor.fetchone()[0] > 0:
            flash("This staff member has reservations and cannot be deleted.", "error")
            return redirect(url_for("staff"))

        cursor.execute("DELETE FROM Staff WHERE staff_id = %s", (staff_id,))
        if cursor.rowcount == 0:
            flash("That staff member was not found.", "error")
            return redirect(url_for("staff"))
        connection.commit()
        flash("Staff member deleted.", "success")
    except Error as error:
        if connection:
            connection.rollback()
        if error.errno == 1451:
            flash("This staff member has reservations and cannot be deleted.", "error")
        else:
            flash("Could not delete the staff member because of a database error.", "error")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    return redirect(url_for("staff"))


if __name__ == "__main__":
    # debug=True is useful for a local college project; do not use it on a public server.
    app.run(debug=True)
