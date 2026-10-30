# Blue Orchid Hotel Reservation System

A Flask and MySQL 8 college project for managing hotel rooms, customers, reservations, payments, staff, cancellations, and guest reviews. The interface uses Jinja templates, CSS, and JavaScript.

## Project files

```text
hotel_reservation_dbms/
├── app.py
├── create_admin.py
├── migration_review3.sql
├── schema.sql
├── sample_data.sql
├── queries.sql
├── requirements.txt
├── README.md
├── static/
│   ├── script.js
│   └── style.css
├── templates/
│   ├── access_denied.html
│   ├── admin_dashboard.html
│   ├── bad_request.html
│   ├── base.html
│   ├── book.html
│   ├── customers.html
│   ├── history.html
│   ├── index.html
│   ├── login.html
│   ├── payments.html
│   ├── register.html
│   ├── reservations.html
│   ├── reviews.html
│   ├── rooms.html
│   └── staff.html
└── tests/
    ├── run_feature_report.py
    └── test_app.py
```

## Important database safety warning

**Never run `schema.sql` against a database containing project data.** It drops and recreates the project tables and triggers.

The existing database is `hotel_reservation`. Before using the new login, cancellation, and review features, apply the separate migration only after checking that it has not already been applied. The migration is written to tolerate existing flag/columns and tables, but it does not validate the structure of an already-existing table.

In the VS Code PowerShell terminal, connect to MySQL:

```powershell
mysql -u root -p hotel_reservation
```

At the MySQL prompt, check the server version and existing migration objects:

```sql
SELECT VERSION();
SHOW COLUMNS FROM Customer;
SHOW COLUMNS FROM Reservation;
SHOW TABLES LIKE 'Review';
SHOW TABLES LIKE 'User';
SHOW TRIGGERS FROM hotel_reservation;
```

If a migration is needed, run it from the MySQL prompt:

```sql
SOURCE C:/Users/PRISHA/Downloads/hotel_reservation_dbms_complete/hotel_reservation_dbms/migration_review3.sql;
```

Then verify the results:

```sql
SHOW COLUMNS FROM Customer;
SHOW COLUMNS FROM Reservation;
SHOW CREATE TABLE Review;
SHOW CREATE TABLE `User`;
SHOW TRIGGERS FROM hotel_reservation;

SELECT customer_id, name, phone, phone_needs_update
FROM Customer
WHERE phone_needs_update = 1 OR phone IS NULL OR TRIM(phone) = '';
```

Confirm that the existing `Customer.phone` column is still present (it is not added by the migration), the flag and cancellation columns exist, both new tables have the expected constraints, missing phone values are `PENDING` and flagged, and these triggers remain present:

- `before_reservation_insert`
- `before_reservation_update`

The triggers must retain their overlap check and exact error message: `Room already booked for these dates`. The migration does not drop tables, delete records, or recreate triggers. Take a backup before applying schema changes.

## Install packages

From the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If the virtual environment already exists, activate it and install packages only if needed.

## Configure the app

In the same PowerShell terminal, set your own MySQL values and generate a private Flask session key:

```powershell
$env:DB_HOST = "localhost"
$env:DB_USER = "root"
$env:MYSQL_PASSWORD = "YOUR_MYSQL_PASSWORD"
$env:DB_NAME = "hotel_reservation"
$env:FLASK_SECRET_KEY = (& python -c "import secrets; print(secrets.token_hex(32))").Trim()
```

Replace the placeholder with your MySQL password in the VS Code PowerShell terminal only. Do not put database passwords or the generated Flask key in source control. These environment values apply only to the current terminal session. Restart the Flask process after changing these values.

## Create the first admin

After applying and verifying the migration, run:

```powershell
python create_admin.py
```

Enter the admin username and password when prompted. The password prompt is hidden; the script asks for it twice and stores only a Werkzeug password hash. To create additional admins, run the script again with a different username.

## Start the local website

With the same environment variables set:

```powershell
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

`python app.py` is for local development. Do not expose Flask's development server or enable debug mode in deployment. A production setup should use a production WSGI server such as the included Gunicorn package and HTTPS.

## Accounts and access

- **Admin:** Sign in at `/login` using the account created by `create_admin.py`. The `/admin` dashboard and navigation provide staff, customer, reservation, payment, and review management.
- **Customer:** Register at `/register`, then sign in at `/login`. Customers can book for their linked customer record and see only their own history, eligible cancellation actions, and review forms.
- **Log out:** Use the navigation's Log out button.
- Customers cannot access `/staff`, `/customers`, `/reservations`, `/payments`, or the admin review report.
- A customer may cancel only their own `Booked` reservation when check-in is at least one day away. Admin cancellation requires a reason. Reservations are updated, never deleted.
- Reviews are accepted only for the customer's `Completed` reservations. One-review-per-stay is enforced by the database unique key.
- Changed customer phone numbers require an authenticated admin's explicit confirmation. `PENDING` is a migration placeholder, not a valid phone number.

## Features

- Home search filters availability by room type and dates.
- When a requested room type is fully booked, the app checks nearby date windows in `+1, -1, +2, -2` order, up to 14 days each way, preserving stay length.
- Existing reservation overlap triggers remain the final booking check.
- Staff with reservations cannot be deleted.
- Payments retain the existing multiple-payment, bill, balance, and occupancy functionality.
- User-supplied SQL values use MySQL Connector `%s` parameters.
- Passwords use Werkzeug password hashing. Session forms use CSRF tokens.

## Tests

Run the 21 automated feature checks:

```powershell
$env:FLASK_SECRET_KEY = (& python -c "import secrets; print(secrets.token_hex(32))").Trim()
python tests/run_feature_report.py
```

The test suite uses mocked database connections and does **not** connect to or alter the real MySQL database. The report prints the expected behavior, actual assertion outcome, and PASS/FAIL for each check. Live database integration still needs to be tested against your MySQL server after the migration is verified.

## Existing database design

The six original tables remain in place:

- `Customer(customer_id, name, phone, email)` — migration adds `phone_needs_update`; it does not add `phone`.
- `RoomType(type_id, type_name, capacity, price_per_night)`
- `Room(room_id, room_no, floor, type_id)`
- `Staff(staff_id, name, role, phone)`
- `Reservation(reservation_id, customer_id, room_id, staff_id, check_in, check_out, status)` — migration adds `cancel_reason` and `cancelled_by`.
- `Payment(payment_id, reservation_id, amount, mode, pay_date)`

New migration tables:

- `Review(review_id, reservation_id, customer_id, rating, comment, created_at)` — primary key; unique reservation; reservation/customer foreign keys; rating check from 1 to 5.
- ``User(user_id, username, password_hash, role, customer_id)`` — primary key; unique username; customer foreign key; role/customer relationship check.

The original foreign keys, data, and reservation triggers are preserved. The migration uses MySQL 8 SQL and its `CHECK` constraints require MySQL 8.0.16 or later for enforcement.
