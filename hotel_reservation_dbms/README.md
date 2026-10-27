# LuxeStay Hotel Reservation System

A beginner-friendly college DBMS project for **one hotel with 30 rooms**. It uses MySQL 8, Python, Flask, `mysql-connector-python`, and plain HTML/CSS/JavaScript. There is no login system.

## Folder structure

```text
hotel_reservation_dbms/
├── app.py
├── schema.sql
├── sample_data.sql
├── queries.sql
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── rooms.html
│   ├── book.html
│   ├── customers.html
│   └── payments.html
└── static/
    ├── style.css
    └── script.js
```

## 1. Create the database (Windows)

1. Start the MySQL server using **Services** or MySQL Installer.
2. Open **MySQL 8.0 Command Line Client** and enter your MySQL password.
3. In the MySQL prompt, run these commands. Replace the path if your folder is elsewhere:

```sql
SOURCE C:/Users/PRISHA/HotelReservationDBMS/schema.sql;
SOURCE C:/Users/PRISHA/HotelReservationDBMS/sample_data.sql;
USE hotel_reservation;
SHOW TABLES;
```

`schema.sql` drops and recreates the six project tables, so do not rerun it if you need to keep data. The scripts create 30 rooms: 10 Standard, 10 Deluxe, and 10 Suite.

## 2. Run the SQL checks

At the MySQL prompt:

```sql
SOURCE C:/Users/PRISHA/HotelReservationDBMS/queries.sql;
```

To test the overlap trigger, the sample reservation already books room 201 from **19 Oct to 22 Oct 2026**. Try:

```sql
INSERT INTO Reservation (customer_id, room_id, staff_id, check_in, check_out, status)
VALUES (1, 11, 1, '2026-10-20', '2026-10-21', 'Booked');
```

Expected MySQL error: `ERROR 1644 (45000): Room already booked for these dates`.

The user-specified free-room expectation (“only 202 and 301”) conflicts with the requirement to create 30 rooms and insert only the seven listed reservations: the other 25 rooms have no overlapping bookings, so the general availability query correctly returns them too. The SQL query is intentionally generic and returns every room that is available. If your assignment requires only rooms 202 and 301, the assignment needs to define the status or reservations for the other rooms, or limit the expected output to the five named example rooms.

Priya's three stays total ₹25,000: room 101 = 3 × ₹2,000 = ₹6,000; room 301 = 2 × ₹6,000 = ₹12,000; room 201 = 2 × ₹3,500 = ₹7,000. The `queries.sql` history query calculates each stay total. Payment records are separate from bill totals; payment amounts do not define the bill.

## 3. Install Python packages

Open the project folder in VS Code. In **Terminal → New Terminal**, run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use Command Prompt terminal and run:

```bat
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

## 4. Configure MySQL password

Set your own MySQL credentials in the same terminal. Do not put your real password into a public repository.

PowerShell:

```powershell
$env:DB_HOST = "localhost"
$env:DB_USER = "root"
$env:DB_PASSWORD = "YOUR_MYSQL_PASSWORD"
$env:DB_NAME = "hotel_reservation"
```

Command Prompt:

```bat
set DB_HOST=localhost
set DB_USER=root
set DB_PASSWORD=YOUR_MYSQL_PASSWORD
set DB_NAME=hotel_reservation
```

Replace `YOUR_MYSQL_PASSWORD` with the password you chose during MySQL setup. The variable is used by this terminal session only.

## 5. Start the website

In the same terminal with the virtual environment activated:

```powershell
python app.py
```

Open the local address printed by Flask, usually `http://127.0.0.1:5000`.

## Pages

- **Home:** hotel details and room availability search.
- **Rooms:** list of all 30 rooms, types, capacity and prices.
- **Book a room:** create reservations; database trigger errors are shown as friendly messages.
- **Customers:** search/list/add customers and view their reservation history.
- **Payments & reports:** record multiple payments per reservation, see bills and balances, and view today's occupancy.

## Database design notes

- `Customer`, `RoomType`, `Room`, `Staff`, `Reservation`, and `Payment` are separate tables to avoid repeating customer, room-type, and staff details.
- The bill is calculated as `DATEDIFF(check_out, check_in) * price_per_night`; it is not stored.
- Payment is a separate table, so a reservation can have a deposit and later payments.
- No card number is collected or stored.
- All user-supplied SQL values use `%s` parameters.
- The booking route starts a transaction and locks the chosen room row with `SELECT ... FOR UPDATE`. The database trigger is the final overlap check.
- This is a learning project. Do not expose Flask debug mode or the development server to the public internet.
