# Blue Orchid – Hotel Reservation System

## About the Project
Blue Orchid is a Flask and MySQL hotel reservation management system developed as a Database Management System (DBMS) project.

## Features
- Hotel room reservation management
- Customer and administrator accounts
- Staff, payment, cancellation, and review management
- Database schema and SQL queries
- Sample data for testing
- Jinja web interface for customers and administrators

## Technologies Used
- Python
- Flask and MySQL 8
- mysql-connector-python
- HTML and CSS
- JavaScript

## Project Structure
- `hotel_reservation_dbms/app.py` – Application entry point
- `hotel_reservation_dbms/migration_review3.sql` – Non-destructive additions for an existing database
- `hotel_reservation_dbms/schema.sql` – Initial schema only; destructive to an existing database
- `queries.sql` – SQL queries
- `sample_data.sql` – Sample database records
- `hotel_reservation_dbms/templates/` – Jinja pages
- `hotel_reservation_dbms/static/` – CSS and JavaScript

## How to Run
1. Follow `hotel_reservation_dbms/README.md` to configure environment variables and install dependencies.
2. Verify and, if needed, run `migration_review3.sql` against the existing database. Never run `schema.sql` on a database containing data.
3. Create an administrator with `create_admin.py`, then run `python app.py` from the project directory.

## Purpose
This project demonstrates database design and hotel reservation management.
