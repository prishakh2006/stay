import os
import secrets
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("FLASK_SECRET_KEY", secrets.token_hex(32))
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import app as app_module
import create_admin
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash


class FakeCursor:
    def __init__(self, *, phone="9876543210", flag_exists=1,
                 reservation_status="Booked", check_in=None,
                 reservation_count=0, duplicate_review=False,
                 overlap_error=False, owner_mismatch=False):
        self.phone = phone
        self.flag_exists = flag_exists
        self.reservation_status = reservation_status
        self.check_in = check_in or date.today() + timedelta(days=10)
        self.reservation_count = reservation_count
        self.duplicate_review = duplicate_review
        self.overlap_error = overlap_error
        self.owner_mismatch = owner_mismatch
        self.calls = []
        self.last_sql = ""
        self.lastrowid = 41
        self.rowcount = 1

    def execute(self, sql, params=()):
        self.last_sql = sql
        self.calls.append((sql, params))
        if self.overlap_error and "INSERT INTO Reservation" in sql:
            raise Error(msg="Room already booked for these dates", errno=1644)
        if self.duplicate_review and "INSERT INTO Review" in sql:
            raise Error(msg="Duplicate review", errno=1062)
        if "DELETE FROM Staff" in sql and self.reservation_count:
            raise Error(msg="Foreign key restriction", errno=1451)

    def fetchone(self):
        if "COUNT(*) FROM Reservation WHERE staff_id" in self.last_sql:
            return (self.reservation_count,)
        if "SELECT staff_id FROM Staff" in self.last_sql:
            return (7,)
        if "FROM Room WHERE room_id" in self.last_sql:
            return (8,)
        if "FROM Customer WHERE customer_id" in self.last_sql:
            return (self.phone,)
        if "INFORMATION_SCHEMA.COLUMNS" in self.last_sql:
            return (self.flag_exists,)
        if "FROM Reservation" in self.last_sql and "FOR UPDATE" in self.last_sql:
            if self.owner_mismatch and "AND customer_id = %s" in self.last_sql:
                return None
            return (self.reservation_status, self.check_in)
        return None

    def fetchall(self):
        return []

    def close(self):
        pass


class FakeConnection:
    def __init__(self, **cursor_options):
        self.fake_cursor = FakeCursor(**cursor_options)
        self.committed = False
        self.rolled_back = False

    def cursor(self, **_kwargs):
        return self.fake_cursor

    def start_transaction(self):
        pass

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


def fake_lists(sql, _params=()):
    if "COUNT(DISTINCT r.room_id)" in sql:
        return [{"occupied": 0, "total": 30}]
    if "FROM RoomType ORDER BY type_id" in sql:
        return [{"type_id": 1, "type_name": "Standard"}]
    if "AS reservation_count" in sql:
        return [{
            "reservation_count": 8, "booked_count": 3,
            "customer_count": 5, "staff_count": 2, "review_count": 1,
        }]
    if "FROM Customer ORDER BY name" in sql:
        return [{"customer_id": 5, "name": "Guest", "phone": "9876543210"}]
    if "FROM Customer WHERE customer_id" in sql:
        return [{"customer_id": 5, "name": "Guest"}]
    if "FROM Room rm JOIN RoomType" in sql:
        return [{
            "room_id": 8, "room_no": 201, "type_id": 1,
            "type_name": "Standard", "capacity": 2, "price_per_night": 2000,
        }]
    if "FROM Staff ORDER BY name" in sql:
        return [{"staff_id": 7, "name": "Reception"}]
    if "FROM Reservation" in sql and "status = 'Completed'" in sql:
        return [{"reservation_id": 10}]
    if "FROM Reservation" in sql and "LEFT JOIN Review" in sql:
        return [{
            "reservation_id": 10, "room_no": 201, "check_in": date.today(),
            "check_out": date.today() + timedelta(days=1), "status": "Completed",
            "nights": 1, "type_name": "Standard", "price_per_night": 2000,
            "total": 2000, "review_id": None, "rating": None, "comment": None,
        }]
    if "FROM Reservation" in sql and "JOIN Customer c" in sql:
        return []
    if "FROM Reservation" in sql:
        return []
    if "FROM Customer" in sql:
        return []
    if "FROM Review" in sql:
        return []
    if "FROM RoomType rt" in sql and "AVG(rv.rating)" in sql:
        return [{"type_name": "Standard", "average_rating": 4.5, "review_count": 2}]
    if "FROM Payment" in sql:
        return []
    return []


class FeatureTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()
        with self.client.session_transaction() as browser_session:
            browser_session["_csrf_token"] = "test-csrf-token"

    def authenticate(self, role="customer", customer_id=5):
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = 1
            browser_session["role"] = role
            if role == "customer":
                browser_session["customer_id"] = customer_id

    def post(self, url, data=None, **kwargs):
        payload = dict(data or {})
        with self.client.session_transaction() as browser_session:
            payload["csrf_token"] = browser_session.get("_csrf_token", "test-csrf-token")
        return self.client.post(url, data=payload, **kwargs)

    def test_mysql_connection_uses_environment_password(self):
        with patch.dict(os.environ, {"MYSQL_PASSWORD": "configured-password"}), \
                patch.object(app_module.mysql.connector, "connect",
                             return_value="connection") as connect:
            self.assertEqual(app_module.get_connection(), "connection")
        connection_config = connect.call_args.kwargs
        self.assertEqual(connection_config["password"], "configured-password")
        self.assertEqual(connection_config["database"], "hotel_reservation")
        self.assertEqual(connection_config["user"], "root")
        self.assertEqual(connection_config["host"], "localhost")

    def test_mysql_connection_requires_environment_password(self):
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(app_module.mysql.connector, "connect") as connect:
            with self.assertRaisesRegex(RuntimeError, "MYSQL_PASSWORD"):
                app_module.get_connection()
        connect.assert_not_called()

    def booking_form(self, phone="9876543210"):
        return {
            "customer_id": "5", "room_id": "8", "staff_id": "7",
            "check_in": "2030-01-01", "check_out": "2030-01-02",
            "phone": phone,
        }

    def test_01_home_and_room_listing_render(self):
        with patch.object(app_module, "fetch_all", side_effect=fake_lists):
            home = self.client.get("/")
            rooms = self.client.get("/rooms")
        self.assertEqual(home.status_code, 200)
        self.assertIn(b"Blue Orchid", home.data)
        self.assertEqual(rooms.status_code, 200)
        self.assertIn(b"Standard room", rooms.data)

    def test_01a_admin_dashboard_and_navigation(self):
        with patch.object(app_module, "fetch_all", side_effect=fake_lists):
            response = self.client.get("/")
        self.assertIn(b"Book a room", response.data)
        self.assertIn(b"Login", response.data)
        self.authenticate(role="admin")
        with patch.object(app_module, "fetch_all", side_effect=fake_lists):
            dashboard = self.client.get("/admin")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Dashboard", dashboard.data)
        self.assertIn(b"Manage staff", dashboard.data)

    def test_02_booking_phone_validation(self):
        self.authenticate()
        with patch.object(app_module, "fetch_all", side_effect=fake_lists), \
                patch.object(app_module, "get_connection") as connect:
            for phone in ("", "PENDING", "123456789", "1234567890123456", "123-456-7890"):
                response = self.post("/book", self.booking_form(phone))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(
                    b"PENDING is only a placeholder" in response.data
                    or b"10 to 15 digits" in response.data)
            connect.assert_not_called()

    def test_03_admin_account_creation_script_hashes_password(self):
        connection = FakeConnection()
        with patch("builtins.input", return_value="blue-admin"), \
                patch.object(create_admin.getpass, "getpass",
                             side_effect=["safe-password-123", "safe-password-123"]), \
                patch.object(create_admin.mysql.connector, "connect",
                             return_value=connection), \
                patch.dict(os.environ, {"MYSQL_PASSWORD": "test-db-password"}), \
                patch("builtins.print"):
            create_admin.main()
        sql, params = connection.fake_cursor.calls[0]
        self.assertIn("INSERT INTO `User`", sql)
        self.assertEqual(params[0], "blue-admin")
        self.assertTrue(check_password_hash(params[1], "safe-password-123"))
        self.assertTrue(connection.committed)

    def test_04_admin_login_succeeds(self):
        self.client.get("/login")
        with patch.object(app_module, "fetch_all", return_value=[{
            "user_id": 1, "username": "admin",
            "password_hash": generate_password_hash("valid-password"),
            "role": "admin", "customer_id": None,
        }]):
            response = self.post("/login", {
                "username": "admin", "password": "valid-password",
            })
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as browser_session:
            self.assertEqual(browser_session["role"], "admin")
            self.assertEqual(browser_session["user_id"], 1)

    def test_05_wrong_password_is_rejected(self):
        self.client.get("/login")
        with patch.object(app_module, "fetch_all", return_value=[{
            "user_id": 1, "username": "admin",
            "password_hash": generate_password_hash("correct-password"),
            "role": "admin", "customer_id": None,
        }]):
            response = self.post("/login", {
                "username": "admin", "password": "wrong-password",
            })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Incorrect username or password", response.data)

    def test_06_customer_registration_creates_hashed_account(self):
        connection = FakeConnection()
        with patch.object(app_module, "get_connection", return_value=connection):
            response = self.post("/register", {
                "name": "Guest", "username": "guest-1", "email": "",
                "phone": "9876543210", "password": "customer-password",
                "password_confirmation": "customer-password",
            })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(connection.committed)
        user_insert = next(call for call in connection.fake_cursor.calls
                           if "INSERT INTO `User`" in call[0])
        self.assertEqual(user_insert[1][0], "guest-1")
        self.assertTrue(check_password_hash(user_insert[1][1], "customer-password"))

    def test_07_customer_login_and_logout(self):
        self.client.get("/login")
        with patch.object(app_module, "fetch_all", return_value=[{
            "user_id": 2, "username": "guest",
            "password_hash": generate_password_hash("customer-password"),
            "role": "customer", "customer_id": 5,
        }]):
            response = self.post("/login", {
                "username": "guest", "password": "customer-password",
            })
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as browser_session:
            self.assertEqual(browser_session["role"], "customer")
            self.assertEqual(browser_session["customer_id"], 5)
        response = self.post("/logout")
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as browser_session:
            self.assertNotIn("user_id", browser_session)

    def test_08_customer_cannot_access_admin_pages_or_other_bookings(self):
        self.authenticate()
        for path in ("/staff", "/customers", "/reservations", "/payments", "/reviews"):
            self.assertEqual(self.client.get(path).status_code, 403, path)
        connection = FakeConnection(
            check_in=date.today() + timedelta(days=10), owner_mismatch=True)
        with patch.object(app_module, "get_connection", return_value=connection):
            response = self.post(
                "/reservations/99/cancel", follow_redirects=False)
        self.assertEqual(response.status_code, 403)
        self.assertIn("AND customer_id = %s", connection.fake_cursor.calls[0][0])
        self.assertEqual(connection.fake_cursor.calls[0][1], (99, 5))

    def test_09_admin_staff_management_add_and_edit(self):
        self.authenticate(role="admin")
        with patch.object(app_module, "fetch_all", side_effect=fake_lists):
            self.assertEqual(self.client.get("/staff").status_code, 200)
        connection = FakeConnection()
        with patch.object(app_module, "get_connection", return_value=connection):
            self.post("/staff/add", {
                "name": "New Staff", "role": "Desk", "phone": "123",
            })
            self.post("/staff/7/edit", {"role": "Lead", "phone": "456"})
        self.assertTrue(connection.committed)
        self.assertEqual(connection.fake_cursor.calls[0][1], ("New Staff", "Desk", "123"))
        self.assertEqual(connection.fake_cursor.calls[-1][1], ("Lead", "456", 7))

    def test_10_staff_with_reservations_cannot_be_deleted(self):
        self.authenticate(role="admin")
        connection = FakeConnection(reservation_count=1)
        with patch.object(app_module, "get_connection", return_value=connection), \
                patch.object(app_module, "fetch_all", return_value=[]):
            response = self.post("/staff/7/delete", follow_redirects=True)
        self.assertIn(b"has reservations and cannot be deleted", response.data)
        self.assertFalse(connection.committed)
        self.assertEqual(len(connection.fake_cursor.calls), 1)

    def test_11_customer_can_cancel_own_eligible_booking(self):
        self.authenticate()
        connection = FakeConnection(
            reservation_status="Booked",
            check_in=date.today() + timedelta(days=10))
        with patch.object(app_module, "get_connection", return_value=connection):
            response = self.post("/reservations/10/cancel")
        self.assertEqual(response.status_code, 302)
        update = connection.fake_cursor.calls[-1]
        self.assertIn("cancelled_by = 'customer'", update[0])
        self.assertEqual(update[1], (10, 5))
        self.assertTrue(connection.committed)

    def test_12_admin_cancellation_requires_reason_and_records_it(self):
        self.authenticate(role="admin")
        connection = FakeConnection(reservation_status="Booked")
        with patch.object(app_module, "get_connection", return_value=connection):
            response = self.post("/reservations/10/cancel", {"cancel_reason": ""})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(connection.fake_cursor.calls, [])
            response = self.post(
                "/reservations/10/cancel", {"cancel_reason": "Guest request"})
        update = connection.fake_cursor.calls[-1]
        self.assertIn("cancelled_by = 'admin'", update[0])
        self.assertEqual(update[1], ("Guest request", 10))
        self.assertTrue(connection.committed)

    def test_13_cancelled_reservations_do_not_block_rebooking_query(self):
        start = date(2030, 1, 1)
        end = date(2030, 1, 2)
        with patch.object(app_module, "fetch_all", return_value=[
            {"room_id": 8, "room_no": 201},
        ]) as fetch:
            result = app_module.available_rooms(1, start, end)
        self.assertEqual(result[0]["room_id"], 8)
        self.assertIn("r.status = 'Booked'", fetch.call_args.args[0])

    def test_14_nearest_dates_use_order_and_keep_stay_length(self):
        start = date(2030, 1, 10)
        end = date(2030, 1, 13)
        offsets = []

        def availability(_type_id, suggested_in, suggested_out):
            offsets.append((suggested_in - start).days)
            if (suggested_in - start).days in (-1, 2, -3):
                return [{"room_id": 8, "room_no": 201}]
            return []

        with patch.object(app_module, "available_rooms", side_effect=availability):
            suggestions = app_module.nearest_available_dates(1, start, end)
        self.assertEqual(offsets[:6], [1, -1, 2, -2, 3, -3])
        self.assertEqual(
            [(item["check_in"] - start).days for item in suggestions],
            [-1, 2, -3])
        self.assertTrue(all(
            (item["check_out"] - item["check_in"]).days == 3
            for item in suggestions))

    def test_15_completed_stay_review_is_saved(self):
        self.authenticate()
        connection = FakeConnection()
        with patch.object(app_module, "fetch_all", side_effect=fake_lists), \
                patch.object(app_module, "get_connection", return_value=connection):
            response = self.post("/reviews/submit", {
                "reservation_id": "10", "rating": "5", "comment": "Lovely stay",
            })
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            ("INSERT INTO Review (reservation_id, customer_id, rating, comment)\n"
             "               VALUES (%s, %s, %s, %s)",
             (10, 5, 5, "Lovely stay")),
            connection.fake_cursor.calls)
        self.assertTrue(connection.committed)

    def test_16_duplicate_review_has_friendly_message(self):
        self.authenticate()
        connection = FakeConnection(duplicate_review=True)
        with patch.object(app_module, "fetch_all", side_effect=fake_lists), \
                patch.object(app_module, "get_connection", return_value=connection):
            response = self.post(
                "/reviews/submit",
                {"reservation_id": "10", "rating": "5", "comment": ""},
                follow_redirects=True)
        self.assertIn(b"already reviewed this stay", response.data)
        self.assertTrue(connection.rolled_back)

    def test_17_reviews_for_incomplete_stays_are_refused(self):
        self.authenticate()
        connection = FakeConnection()
        with patch.object(app_module, "fetch_all", return_value=[]), \
                patch.object(app_module, "get_connection", return_value=connection):
            response = self.post(
                "/reviews/submit",
                {"reservation_id": "10", "rating": "5", "comment": ""},
                follow_redirects=True)
        self.assertIn(b"only be submitted for your completed stay", response.data)
        self.assertEqual(connection.fake_cursor.calls, [])

    def test_18_admin_sees_average_rating_per_room_type(self):
        self.authenticate(role="admin")
        with patch.object(app_module, "fetch_all", side_effect=fake_lists):
            response = self.client.get("/reviews")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"4.50 / 5", response.data)
        self.assertIn(b"Standard", response.data)

    def test_19_existing_booking_and_payment_routes_remain_available(self):
        self.authenticate(role="admin")
        booking_connection = FakeConnection(phone="9876543210")
        with patch.object(app_module, "fetch_all", side_effect=fake_lists), \
                patch.object(app_module, "get_connection", return_value=booking_connection):
            booking_response = self.post("/book", self.booking_form())
        self.assertEqual(booking_response.status_code, 302)
        self.assertTrue(booking_connection.committed)
        self.assertTrue(any(
            "INSERT INTO Reservation" in sql
            for sql, _params in booking_connection.fake_cursor.calls))

        payment_connection = FakeConnection()
        with patch.object(app_module, "fetch_all", side_effect=fake_lists), \
                patch.object(app_module, "get_connection", return_value=payment_connection):
            payment_response = self.post("/payments", {
                "reservation_id": "10", "amount": "100.00",
                "mode": "Cash", "pay_date": "2030-01-01",
            })
        self.assertEqual(payment_response.status_code, 302)
        self.assertTrue(any(
            "INSERT INTO Payment" in sql and params == (10, app_module.Decimal("100.00"), "Cash", "2030-01-01")
            for sql, params in payment_connection.fake_cursor.calls))

    def test_20_overlap_trigger_error_message_is_preserved(self):
        self.authenticate(role="admin")
        connection = FakeConnection(phone="9876543210", overlap_error=True)
        with patch.object(app_module, "fetch_all", side_effect=fake_lists), \
                patch.object(app_module, "get_connection", return_value=connection):
            response = self.post(
                "/book", self.booking_form(), follow_redirects=True)
        self.assertIn(b"Room already booked for these dates", response.data)
        self.assertTrue(connection.rolled_back)


if __name__ == "__main__":
    unittest.main()
