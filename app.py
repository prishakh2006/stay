from datetime import date
import os
from decimal import Decimal
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "college-project-change-me")

# Set these environment variables in the terminal before starting the app.
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": "Prisha@20",
    "database": os.environ.get("DB_NAME", "hotel_reservation"),
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


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


@app.route("/")
def home():
    rooms = []
    check_in = request.args.get("check_in", "")
    check_out = request.args.get("check_out", "")
    if check_in and check_out and check_out > check_in:
        rooms = fetch_all(
            """SELECT rm.room_id, rm.room_no, rt.type_name, rt.capacity,
                      rt.price_per_night
               FROM Room rm JOIN RoomType rt ON rt.type_id = rm.type_id
               WHERE NOT EXISTS (
                   SELECT 1 FROM Reservation r
                   WHERE r.room_id = rm.room_id AND r.status = 'Booked'
                     AND %s < r.check_out AND %s > r.check_in
               ) ORDER BY rm.room_no""", (check_in, check_out))
    return render_template("index.html", rooms=rooms, check_in=check_in, check_out=check_out)


@app.route("/rooms")
def rooms():
    rows = fetch_all("""SELECT rm.room_id, rm.room_no, rm.floor, rt.type_name,
                              rt.capacity, rt.price_per_night
                       FROM Room rm JOIN RoomType rt ON rt.type_id = rm.type_id
                       ORDER BY rm.room_no""")
    return render_template("rooms.html", rooms=rows)


@app.route("/book", methods=["GET", "POST"])
def book():
    customers = fetch_all("SELECT customer_id, name FROM Customer ORDER BY name")
    room_rows = fetch_all("""SELECT rm.room_id, rm.room_no, rt.type_name, rt.price_per_night
                             FROM Room rm JOIN RoomType rt ON rt.type_id = rm.type_id
                             ORDER BY rm.room_no""")
    staff = fetch_all("SELECT staff_id, name FROM Staff ORDER BY name")
    if request.method == "POST":
        customer_id = request.form.get("customer_id", type=int)
        room_id = request.form.get("room_id", type=int)
        staff_id = request.form.get("staff_id", type=int)
        check_in_text = request.form.get("check_in", "")
        check_out_text = request.form.get("check_out", "")
        try:
            check_in = date.fromisoformat(check_in_text)
            check_out = date.fromisoformat(check_out_text)
            if check_out <= check_in:
                flash("Check-out must be after check-in.", "error")
                return render_template("book.html", customers=customers, rooms=room_rows, staff=staff)
            connection = get_connection()
            cursor = connection.cursor()
            try:
                # Lock the room row so two booking requests cannot check it simultaneously.
                connection.start_transaction()
                cursor.execute("SELECT room_id FROM Room WHERE room_id = %s FOR UPDATE", (room_id,))
                if cursor.fetchone() is None:
                    raise ValueError("Please choose a valid room.")
                cursor.execute(
                    """INSERT INTO Reservation
                       (customer_id, room_id, staff_id, check_in, check_out, status)
                       VALUES (%s, %s, %s, %s, %s, 'Booked')""",
                    (customer_id, room_id, staff_id, check_in, check_out))
                connection.commit()
                flash("Booking created successfully!", "success")
                return redirect(url_for("customers"))
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
                flash("Database error: " + str(error), "error")
        except (ValueError, TypeError) as error:
            flash("Please check the dates and selections: " + str(error), "error")
    return render_template("book.html", customers=customers, rooms=room_rows, staff=staff)


@app.route("/customers", methods=["GET", "POST"])
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


@app.route("/payments", methods=["GET", "POST"])
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


if __name__ == "__main__":
    # debug=True is useful for a local college project; do not use it on a public server.
    app.run(debug=True)
