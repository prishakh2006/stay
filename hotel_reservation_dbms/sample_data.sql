-- =============================================================================
-- HOTEL RESERVATION SYSTEM - SAMPLE DATA (All dates in 2026)
-- Run this script AFTER schema.sql.
-- =============================================================================

USE hotel_reservation;

-- -----------------------------------------------------------------------------
-- 1. Insert Customers
-- -----------------------------------------------------------------------------
INSERT INTO Customer (customer_id, name, phone, email) VALUES
(1, 'Priya Nair', '9000000001', 'priya@example.com'),
(2, 'Arjun Mehta', '9000000002', 'arjun@example.com'),
(3, 'Sana Khan', '9000000003', 'sana@example.com'),
(4, 'Rahul Iyer', '9000000004', 'rahul@example.com'),
(5, 'Meera Das', '9000000005', 'meera@example.com');

-- -----------------------------------------------------------------------------
-- 2. Insert Room Types
-- -----------------------------------------------------------------------------
INSERT INTO RoomType (type_id, type_name, capacity, price_per_night) VALUES
(1, 'Standard', 2, 2000.00),
(2, 'Deluxe',   3, 3500.00),
(3, 'Suite',    4, 6000.00);

-- -----------------------------------------------------------------------------
-- 3. Insert Rooms
-- The hotel schema supports up to 30 rooms (10 Standard, 10 Deluxe, 10 Suite).
-- For college project test checks, the 5 core test rooms are active below:
-- Rooms 101, 102 (Standard); 201, 202 (Deluxe); 301 (Suite).
-- -----------------------------------------------------------------------------
INSERT INTO Room (room_id, room_no, floor, type_id) VALUES
(1, 101, 1, 1),
(2, 102, 1, 1),
(3, 201, 2, 2),
(4, 202, 2, 2),
(5, 301, 3, 3);

-- (Optional extension up to 30 rooms - uncomment if testing with full capacity):
-- INSERT INTO Room (room_id, room_no, floor, type_id) VALUES
-- (6, 103, 1, 1), (7, 104, 1, 1), (8, 105, 1, 1), (9, 106, 1, 1), (10, 107, 1, 1),
-- (11, 108, 1, 1), (12, 109, 1, 1), (13, 110, 1, 1),
-- (14, 203, 2, 2), (15, 204, 2, 2), (16, 205, 2, 2), (17, 206, 2, 2), (18, 207, 2, 2),
-- (19, 208, 2, 2), (20, 209, 2, 2), (21, 210, 2, 2),
-- (22, 302, 3, 3), (23, 303, 3, 3), (24, 304, 3, 3), (25, 305, 3, 3), (26, 306, 3, 3),
-- (27, 307, 3, 3), (28, 308, 3, 3), (29, 309, 3, 3), (30, 310, 3, 3);

-- -----------------------------------------------------------------------------
-- 4. Insert Staff
-- -----------------------------------------------------------------------------
INSERT INTO Staff (staff_id, name, role, phone) VALUES
(1, 'Kavya',  'Receptionist', '9111111111'),
(2, 'Vikram', 'Manager',      '9222222222');

-- -----------------------------------------------------------------------------
-- 5. Insert Reservations
-- -----------------------------------------------------------------------------
INSERT INTO Reservation (reservation_id, customer_id, room_id, staff_id, check_in, check_out, status) VALUES
(1, 1, 1, 1, '2026-10-18', '2026-10-21', 'Booked'),    -- Priya: Room 101
(2, 2, 3, 1, '2026-10-19', '2026-10-22', 'Booked'),    -- Arjun: Room 201
(3, 3, 2, 1, '2026-10-22', '2026-10-25', 'Booked'),    -- Sana: Room 102
(4, 1, 5, 2, '2026-11-02', '2026-11-04', 'Booked'),    -- Priya: Room 301
(5, 4, 4, 1, '2026-10-14', '2026-10-16', 'Completed'), -- Rahul: Room 202
(6, 1, 3, 1, '2026-09-05', '2026-09-07', 'Completed'), -- Priya: Room 201
(7, 5, 1, 1, '2026-10-25', '2026-10-27', 'Booked');    -- Meera: Room 101

-- -----------------------------------------------------------------------------
-- 6. Insert Payments
-- -----------------------------------------------------------------------------
INSERT INTO Payment (payment_id, reservation_id, amount, mode, pay_date) VALUES
(1, 6,  7000.00, 'UPI',  '2026-09-07'),  -- Priya 201 stay (2 nights @ 3500)
(2, 1,  6000.00, 'Card', '2026-10-20'),  -- Priya 101 stay (3 nights @ 2000)
(3, 2, 10500.00, 'Cash', '2026-10-22');  -- Arjun 201 stay (3 nights @ 3500)

-- Set auto_increment to start beyond sample rows
ALTER TABLE Customer AUTO_INCREMENT = 6;
ALTER TABLE RoomType AUTO_INCREMENT = 4;
ALTER TABLE Room AUTO_INCREMENT = 6;
ALTER TABLE Staff AUTO_INCREMENT = 3;
ALTER TABLE Reservation AUTO_INCREMENT = 8;
ALTER TABLE Payment AUTO_INCREMENT = 4;
