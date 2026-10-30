-- LuxeStay review 3 migration for MySQL 8.
-- This file preserves existing tables and reservation overlap triggers.
USE hotel_reservation;

ALTER TABLE Customer
    ADD COLUMN phone_needs_update TINYINT(1) NOT NULL DEFAULT 0;

CREATE TABLE Review (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    reservation_id INT NOT NULL UNIQUE,
    customer_id INT NOT NULL,
    rating INT NOT NULL,
    comment VARCHAR(500),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_review_rating CHECK (rating BETWEEN 1 AND 5),
    CONSTRAINT fk_review_reservation
        FOREIGN KEY (reservation_id) REFERENCES Reservation(reservation_id),
    CONSTRAINT fk_review_customer
        FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
);

CREATE TABLE `User` (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'customer') NOT NULL,
    customer_id INT NULL,
    CONSTRAINT fk_user_customer
        FOREIGN KEY (customer_id) REFERENCES Customer(customer_id),
    CONSTRAINT chk_user_role_customer CHECK (
        (role = 'admin' AND customer_id IS NULL)
        OR (role = 'customer' AND customer_id IS NOT NULL)
    )
);

ALTER TABLE Reservation
    ADD COLUMN cancel_reason VARCHAR(255) NULL,
    ADD COLUMN cancelled_by ENUM('customer', 'admin') NULL;
