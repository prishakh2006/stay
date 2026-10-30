"""
=============================================================================
HOTEL RESERVATION SYSTEM - Test Suite (test_system.py)
Tests database constraints, triggers, queries, transactions, and Flask routes.
=============================================================================
"""

import os
import sys
from pathlib import Path
import unittest

# Ensure project root is in sys.path
PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import app as app_module
from app import app, get_db_connection, fetch_all, fetch_one
import mysql.connector


class HotelReservationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Verify DB connection and load clean schema and sample data using mysql CLI."""
        import subprocess
        mysql_bin = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
        schema_path = str(PROJECT_DIR / "schema.sql")
        sample_path = str(PROJECT_DIR / "sample_data.sql")

        # Run schema.sql
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_content = f.read()
        subprocess.run([mysql_bin, "-u", "root", "-pPrisha@20"], input=schema_content, text=True, check=True)

        # Run sample_data.sql
        with open(sample_path, "r", encoding="utf-8") as f:
            sample_content = f.read()
        subprocess.run([mysql_bin, "-u", "root", "-pPrisha@20"], input=sample_content, text=True, check=True)

        cls.conn = get_db_connection()
        cls.cursor = cls.conn.cursor(dictionary=True)

        # Set up Flask test client
        app.config["TESTING"] = True
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.cursor.close()
        cls.conn.close()

    def setUp(self):
        """Reset DB before each test method to guarantee clean state."""
        import subprocess
        mysql_bin = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
        schema_path = str(PROJECT_DIR / "schema.sql")
        sample_path = str(PROJECT_DIR / "sample_data.sql")

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_content = f.read()
        subprocess.run([mysql_bin, "-u", "root", "-pPrisha@20"], input=schema_content, text=True, check=True)

        with open(sample_path, "r", encoding="utf-8") as f:
            sample_content = f.read()
        subprocess.run([mysql_bin, "-u", "root", "-pPrisha@20"], input=sample_content, text=True, check=True)

    def test_check_1_free_rooms_for_oct_20_23(self):
        """Check 1: Free rooms for 20-23 Oct 2026 are 202 and 301."""
        query = """
            SELECT rm.room_no
            FROM Room rm
            WHERE NOT EXISTS (
                SELECT 1 FROM Reservation r
                WHERE r.room_id = rm.room_id
                  AND r.status = 'Booked'
                  AND %s < r.check_out
                  AND %s > r.check_in
            )
            ORDER BY rm.room_no
        """
        rows = fetch_all(query, ("2026-10-20", "2026-10-23"))
        free_rooms = [r["room_no"] for r in rows]
        print(f"\n[TEST Check 1] Free rooms for 20-23 Oct 2026: {free_rooms}")
        self.assertEqual(free_rooms, [202, 301], "Check 1 failed: Expected free rooms [202, 301]")

    def test_check_2_trigger_rejects_overlap(self):
        """Check 2: Booking room 201 for 20-21 Oct fails with the trigger message."""
        # Room 201 has room_id = 3
        conn = get_db_connection()
        cursor = conn.cursor()
        trigger_message = ""
        try:
            cursor.execute(
                """INSERT INTO Reservation (customer_id, room_id, staff_id, check_in, check_out, status)
                   VALUES (1, 3, 1, '2026-10-20', '2026-10-21', 'Booked')"""
            )
            conn.commit()
            self.fail("Trigger should have rejected the booking!")
        except mysql.connector.Error as err:
            trigger_message = err.msg
            print(f"[TEST Check 2] Caught Trigger Message: '{trigger_message}' (SQLSTATE: {err.sqlstate})")
            self.assertEqual(err.msg, "Room already booked for these dates")
        finally:
            cursor.close()
            conn.close()

    def test_check_3_priya_history(self):
        """Check 3: Priya's history shows 3 stays totalling Rs 25,000."""
        query = """
            SELECT 
                COUNT(r.reservation_id) AS total_stays,
                SUM(DATEDIFF(r.check_out, r.check_in) * rt.price_per_night) AS grand_total
            FROM Customer c
            JOIN Reservation r ON c.customer_id = r.customer_id
            JOIN Room rm ON r.room_id = rm.room_id
            JOIN RoomType rt ON rm.type_id = rt.type_id
            WHERE c.name = 'Priya Nair'
        """
        summary = fetch_one(query)
        total_stays = summary["total_stays"]
        grand_total = float(summary["grand_total"])
        print(f"[TEST Check 3] Priya Nair: {total_stays} stays, Total: Rs {grand_total:,.2f}")
        self.assertEqual(total_stays, 3, "Priya should have 3 stays")
        self.assertEqual(grand_total, 25000.0, "Total stays should equal Rs 25,000")

    def test_web_home_page_and_search(self):
        """Test Home page and availability search via GET query parameters."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"LuxeStay Hotel", response.data)

        # Search 2026-10-20 to 2026-10-23
        search_resp = self.client.get("/?check_in=2026-10-20&check_out=2026-10-23")
        self.assertEqual(search_resp.status_code, 200)
        self.assertIn(b"Room 202", search_resp.data)
        self.assertIn(b"Room 301", search_resp.data)
        self.assertNotIn(b"Room 101", search_resp.data)
        self.assertNotIn(b"Room 201", search_resp.data)

    def test_web_rooms_page(self):
        """Test Rooms page."""
        response = self.client.get("/rooms")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Room 101", response.data)
        self.assertIn(b"Room 201", response.data)
        self.assertIn(b"Room 301", response.data)

    def test_web_book_page_post_trigger_error(self):
        """Test booking via Web Form: triggers 'Room already booked for these dates' flash message."""
        # Attempt to book Room 201 (room_id 3) on 2026-10-20 to 2026-10-21
        response = self.client.post("/book", data={
            "customer_id": 1,
            "room_id": 3,
            "staff_id": 1,
            "check_in": "2026-10-20",
            "check_out": "2026-10-21"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Room already booked for these dates", response.data)

    def test_web_book_page_post_success(self):
        """Test successful booking of an available room (Room 301 for 2026-10-20 to 2026-10-22)."""
        response = self.client.post("/book", data={
            "customer_id": 3,  # Sana Khan
            "room_id": 5,        # Room 301
            "staff_id": 2,       # Vikram
            "check_in": "2026-10-20",
            "check_out": "2026-10-22"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Reservation successfully booked", response.data)

    def test_web_customers_list_and_add(self):
        """Test customer directory and adding a new customer."""
        response = self.client.get("/customers")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Priya Nair", response.data)

        # Add customer
        add_resp = self.client.post("/customers", data={
            "name": "Kiran Rao",
            "phone": "9876543210",
            "email": "kiran@example.com"
        }, follow_redirects=True)
        self.assertEqual(add_resp.status_code, 200)
        self.assertIn(b"Kiran Rao", add_resp.data)

    def test_web_customer_history(self):
        """Test Customer History view for Priya Nair."""
        response = self.client.get("/customers/1/history")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Booking History: Priya Nair", response.data)
        self.assertIn(b"25000.00", response.data)

    def test_web_payments_and_reports(self):
        """Test Payments & Reports view (Occupancy + Billing status)."""
        response = self.client.get("/payments?occupancy_date=2026-10-20")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Occupancy Report", response.data)
        self.assertIn(b"Record New Payment", response.data)


if __name__ == "__main__":
    unittest.main()
