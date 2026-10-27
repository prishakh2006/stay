-- Hotel Reservation System: MySQL 8
-- WARNING: This script drops and recreates the project database.
CREATE DATABASE IF NOT EXISTS hotel_reservation;
USE hotel_reservation;

DROP TRIGGER IF EXISTS before_reservation_insert;
DROP TRIGGER IF EXISTS before_reservation_update;
DROP TABLE IF EXISTS Payment;
DROP TABLE IF EXISTS Reservation;
DROP TABLE IF EXISTS Room;
DROP TABLE IF EXISTS Staff;
DROP TABLE IF EXISTS RoomType;
DROP TABLE IF EXISTS Customer;

CREATE TABLE Customer (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(120) UNIQUE
);

CREATE TABLE RoomType (
    type_id INT AUTO_INCREMENT PRIMARY KEY,
    type_name VARCHAR(30) NOT NULL UNIQUE,
    capacity INT NOT NULL,
    price_per_night DECIMAL(10,2) NOT NULL,
    CHECK (capacity > 0),
    CHECK (price_per_night >= 0)
);

CREATE TABLE Room (
    room_id INT AUTO_INCREMENT PRIMARY KEY,
    room_no INT NOT NULL UNIQUE,
    floor INT NOT NULL,
    type_id INT NOT NULL,
    FOREIGN KEY (type_id) REFERENCES RoomType(type_id)
);

CREATE TABLE Staff (
    staff_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(40) NOT NULL,
    phone VARCHAR(20)
);

CREATE TABLE Reservation (
    reservation_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    room_id INT NOT NULL,
    staff_id INT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    status ENUM('Booked','Cancelled','Completed') NOT NULL DEFAULT 'Booked',
    CONSTRAINT chk_dates CHECK (check_out > check_in),
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id),
    FOREIGN KEY (room_id) REFERENCES Room(room_id),
    FOREIGN KEY (staff_id) REFERENCES Staff(staff_id),
    INDEX idx_reservation_customer (customer_id),
    INDEX idx_reservation_room_dates (room_id, check_in, check_out)
);

CREATE TABLE Payment (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    reservation_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    mode ENUM('Cash','Card','UPI') NOT NULL,
    pay_date DATE NOT NULL,
    CHECK (amount > 0),
    FOREIGN KEY (reservation_id) REFERENCES Reservation(reservation_id)
);

DELIMITER $$
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
