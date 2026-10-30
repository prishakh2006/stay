-- =============================================================================
-- HOTEL RESERVATION SYSTEM - DATABASE SCHEMA (MySQL 8)
-- College DBMS Project - 6 Tables in 3rd Normal Form (3NF)
-- =============================================================================

CREATE DATABASE IF NOT EXISTS hotel_reservation;
USE hotel_reservation;

-- Drop existing objects cleanly
SET FOREIGN_KEY_CHECKS = 0;
DROP TRIGGER IF EXISTS before_reservation_insert;
DROP TRIGGER IF EXISTS before_reservation_update;
DROP TABLE IF EXISTS Payment;
DROP TABLE IF EXISTS Reservation;
DROP TABLE IF EXISTS Staff;
DROP TABLE IF EXISTS Room;
DROP TABLE IF EXISTS RoomType;
DROP TABLE IF EXISTS Customer;
DROP TABLE IF EXISTS `User`;
DROP TABLE IF EXISTS Review;
SET FOREIGN_KEY_CHECKS = 1;

-- -----------------------------------------------------------------------------
-- 1. Customer Table (in 3NF: all non-key attributes depend only on customer_id)
-- -----------------------------------------------------------------------------
CREATE TABLE Customer (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(120) UNIQUE
);

-- -----------------------------------------------------------------------------
-- 2. RoomType Table (stores room categories, capacity, and nightly rates)
-- -----------------------------------------------------------------------------
CREATE TABLE RoomType (
    type_id INT AUTO_INCREMENT PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL UNIQUE,
    capacity INT NOT NULL,
    price_per_night DECIMAL(10, 2) NOT NULL,
    CONSTRAINT chk_capacity CHECK (capacity > 0),
    CONSTRAINT chk_price CHECK (price_per_night >= 0)
);

-- -----------------------------------------------------------------------------
-- 3. Room Table (physical rooms linked to a RoomType)
-- -----------------------------------------------------------------------------
CREATE TABLE Room (
    room_id INT AUTO_INCREMENT PRIMARY KEY,
    room_no INT NOT NULL UNIQUE,
    floor INT NOT NULL,
    type_id INT NOT NULL,
    CONSTRAINT fk_room_type FOREIGN KEY (type_id) REFERENCES RoomType(type_id)
);

-- -----------------------------------------------------------------------------
-- 4. Staff Table (hotel employees handling reservations)
-- -----------------------------------------------------------------------------
CREATE TABLE Staff (
    staff_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL,
    phone VARCHAR(20)
);

-- -----------------------------------------------------------------------------
-- 5. Reservation Table (links customer, room, and staff)
-- Rules enforced:
-- - check_out must be strictly after check_in
-- - Bill total is NOT stored here: derived as nights x price_per_night
-- - Foreign keys ensure referential integrity
-- -----------------------------------------------------------------------------
CREATE TABLE Reservation (
    reservation_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    room_id INT NOT NULL,
    staff_id INT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    status ENUM('Booked', 'Cancelled', 'Completed') NOT NULL DEFAULT 'Booked',
    CONSTRAINT chk_checkout_after_checkin CHECK (check_out > check_in),
    CONSTRAINT fk_reservation_customer FOREIGN KEY (customer_id) REFERENCES Customer(customer_id),
    CONSTRAINT fk_reservation_room FOREIGN KEY (room_id) REFERENCES Room(room_id),
    CONSTRAINT fk_reservation_staff FOREIGN KEY (staff_id) REFERENCES Staff(staff_id),
    INDEX idx_reservation_customer (customer_id),
    INDEX idx_reservation_room_dates (room_id, check_in, check_out)
);

-- -----------------------------------------------------------------------------
-- 6. Payment Table (supports multiple payments per reservation, e.g. deposit + balance)
-- Rules enforced:
-- - No card numbers stored (PCI-DSS compliance)
-- - Positive payment amount
-- -----------------------------------------------------------------------------
CREATE TABLE Payment (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    reservation_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    mode ENUM('Cash', 'Card', 'UPI') NOT NULL,
    pay_date DATE NOT NULL,
    CONSTRAINT chk_payment_amount CHECK (amount > 0),
    CONSTRAINT fk_payment_reservation FOREIGN KEY (reservation_id) REFERENCES Reservation(reservation_id)
);

-- =============================================================================
-- TRIGGERS TO PREVENT DOUBLE-BOOKING
-- Standard interval overlap formula:
-- [new.check_in, new.check_out) overlaps with [existing.check_in, existing.check_out)
-- if and only if: (new.check_in < existing.check_out AND new.check_out > existing.check_in)
-- =============================================================================

DELIMITER $$

-- Trigger 1: BEFORE INSERT
CREATE TRIGGER before_reservation_insert
BEFORE INSERT ON Reservation
FOR EACH ROW
BEGIN
    IF NEW.status = 'Booked' AND EXISTS (
        SELECT 1 FROM Reservation r
        WHERE r.room_id = NEW.room_id
          AND r.status = 'Booked'
          AND NEW.check_in < r.check_out
          AND NEW.check_out > r.check_in
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Room already booked for these dates';
    END IF;
END$$

-- Trigger 2: BEFORE UPDATE (ignores current reservation ID)
CREATE TRIGGER before_reservation_update
BEFORE UPDATE ON Reservation
FOR EACH ROW
BEGIN
    IF NEW.status = 'Booked' AND EXISTS (
        SELECT 1 FROM Reservation r
        WHERE r.room_id = NEW.room_id
          AND r.reservation_id <> OLD.reservation_id
          AND r.status = 'Booked'
          AND NEW.check_in < r.check_out
          AND NEW.check_out > r.check_in
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Room already booked for these dates';
    END IF;
END$$

DELIMITER ;
