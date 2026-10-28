-- Run after schema.sql. All sample dates are in 2026.
USE hotel_reservation;

INSERT INTO Customer (customer_id, name, phone, email) VALUES
(1, 'Priya Nair', '9000000001', 'priya@example.com'),
(2, 'Arjun Mehta', '9000000002', 'arjun@example.com'),
(3, 'Sana Khan', '9000000003', 'sana@example.com'),
(4, 'Rahul Iyer', '9000000004', 'rahul@example.com'),
(5, 'Meera Das', '9000000005', 'meera@example.com');

INSERT INTO RoomType (type_id, type_name, capacity, price_per_night) VALUES
(1, 'Standard', 2, 2000.00),
(2, 'Deluxe', 3, 3500.00),
(3, 'Suite', 4, 6000.00);

-- The hotel has 30 rooms: 10 Standard, 10 Deluxe and 10 Suite.
-- Required example room numbers are included in the list.
INSERT INTO Room (room_id, room_no, floor, type_id) VALUES
(1,101,1,1),(2,102,1,1),(3,103,1,1),(4,104,1,1),(5,105,1,1),
(6,106,1,1),(7,107,1,1),(8,108,1,1),(9,109,1,1),(10,110,1,1),
(11,201,2,2),(12,202,2,2),(13,203,2,2),(14,204,2,2),(15,205,2,2),
(16,206,2,2),(17,207,2,2),(18,208,2,2),(19,209,2,2),(20,210,2,2),
(21,301,3,3),(22,302,3,3),(23,303,3,3),(24,304,3,3),(25,305,3,3),
(26,306,3,3),(27,307,3,3),(28,308,3,3),(29,309,3,3),(30,310,3,3);

INSERT INTO Staff (staff_id, name, role, phone) VALUES
(1, 'Kavya', 'Receptionist', '9111111111'),
(2, 'Vikram', 'Manager', '9222222222');

INSERT INTO Reservation (reservation_id, customer_id, room_id, staff_id, check_in, check_out, status) VALUES
(1,1,1,1,'2026-10-18','2026-10-21','Booked'),
(2,2,11,1,'2026-10-19','2026-10-22','Booked'),
(3,3,2,1,'2026-10-22','2026-10-25','Booked'),
(4,1,21,2,'2026-11-02','2026-11-04','Booked'),
(5,4,12,1,'2026-10-14','2026-10-16','Completed'),
(6,1,11,1,'2026-09-05','2026-09-07','Completed'),
(7,5,1,1,'2026-10-25','2026-10-27','Booked');

INSERT INTO Payment (payment_id, reservation_id, amount, mode, pay_date) VALUES
(1,6,7000.00,'UPI','2026-09-07'),
(2,1,6000.00,'Card','2026-10-20'),
(3,2,10500.00,'Cash','2026-10-22');

ALTER TABLE Customer AUTO_INCREMENT = 6;
ALTER TABLE RoomType AUTO_INCREMENT = 4;
ALTER TABLE Room AUTO_INCREMENT = 31;
ALTER TABLE Staff AUTO_INCREMENT = 3;
ALTER TABLE Reservation AUTO_INCREMENT = 8;
ALTER TABLE Payment AUTO_INCREMENT = 4;
