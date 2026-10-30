-- =============================================================================
-- HOTEL RESERVATION SYSTEM - QUERIES (queries.sql)
-- College DBMS Project - Core Business & Reporting Queries
-- =============================================================================

USE hotel_reservation;

-- -----------------------------------------------------------------------------
-- 1. Rooms free for a date range (with room type, capacity, and price per night)
-- Rule: Room is free if it has NO 'Booked' reservation that overlaps:
--       (@check_in < existing.check_out AND @check_out > existing.check_in)
-- Test dates: 2026-10-20 to 2026-10-23
-- Expected result: Rooms 202 and 301
-- -----------------------------------------------------------------------------
SET @check_in = '2026-10-20';
SET @check_out = '2026-10-23';

SELECT 
    rm.room_no, 
    rt.type_name, 
    rt.capacity, 
    rt.price_per_night
FROM Room rm
JOIN RoomType rt ON rm.type_id = rt.type_id
WHERE NOT EXISTS (
    SELECT 1 FROM Reservation r
    WHERE r.room_id = rm.room_id
      AND r.status = 'Booked'
      AND @check_in < r.check_out
      AND @check_out > r.check_in
)
ORDER BY rm.room_no;

-- -----------------------------------------------------------------------------
-- 2. Booking history of one customer (nights and total per stay)
-- Total is calculated as: DATEDIFF(check_out, check_in) * price_per_night
-- Expected for Priya Nair: 3 stays totalling Rs 25,000
-- -----------------------------------------------------------------------------
SET @customer_name = 'Priya Nair';

-- Detailed stay-by-stay breakdown:
SELECT 
    c.name AS customer_name,
    r.reservation_id,
    rm.room_no,
    rt.type_name,
    r.check_in,
    r.check_out,
    DATEDIFF(r.check_out, r.check_in) AS nights,
    rt.price_per_night,
    (DATEDIFF(r.check_out, r.check_in) * rt.price_per_night) AS stay_total,
    r.status
FROM Customer c
JOIN Reservation r ON c.customer_id = r.customer_id
JOIN Room rm ON r.room_id = rm.room_id
JOIN RoomType rt ON rm.type_id = rt.type_id
WHERE c.name = @customer_name
ORDER BY r.check_in;

-- Summary grand total:
SELECT 
    c.name AS customer_name,
    COUNT(r.reservation_id) AS total_stays,
    SUM(DATEDIFF(r.check_out, r.check_in) * rt.price_per_night) AS grand_total_amount
FROM Customer c
JOIN Reservation r ON c.customer_id = r.customer_id
JOIN Room rm ON r.room_id = rm.room_id
JOIN RoomType rt ON rm.type_id = rt.type_id
WHERE c.name = @customer_name
GROUP BY c.customer_id, c.name;

-- -----------------------------------------------------------------------------
-- 3. Reservations with pending payments (total minus paid)
-- Calculated as: bill_total - COALESCE(SUM(amount), 0)
-- -----------------------------------------------------------------------------
SELECT 
    r.reservation_id,
    c.name AS customer_name,
    rm.room_no,
    r.check_in,
    r.check_out,
    (DATEDIFF(r.check_out, r.check_in) * rt.price_per_night) AS bill_total,
    COALESCE(SUM(p.amount), 0) AS total_paid,
    ((DATEDIFF(r.check_out, r.check_in) * rt.price_per_night) - COALESCE(SUM(p.amount), 0)) AS pending_amount
FROM Reservation r
JOIN Customer c ON r.customer_id = c.customer_id
JOIN Room rm ON r.room_id = rm.room_id
JOIN RoomType rt ON rm.type_id = rt.type_id
LEFT JOIN Payment p ON r.reservation_id = p.reservation_id
WHERE r.status <> 'Cancelled'
GROUP BY r.reservation_id, c.name, rm.room_no, r.check_in, r.check_out, rt.price_per_night
HAVING pending_amount > 0
ORDER BY r.check_in;

-- -----------------------------------------------------------------------------
-- 4. Occupancy on a given date (rooms occupied / total rooms)
-- A room is occupied on date D if: check_in <= D AND check_out > D
-- -----------------------------------------------------------------------------
SET @target_date = '2026-10-20';

SELECT 
    COUNT(DISTINCT r.room_id) AS rooms_occupied,
    (SELECT COUNT(*) FROM Room) AS total_rooms,
    ROUND((COUNT(DISTINCT r.room_id) / (SELECT COUNT(*) FROM Room)) * 100, 2) AS occupancy_percentage
FROM Reservation r
WHERE r.status = 'Booked'
  AND r.check_in <= @target_date
  AND r.check_out > @target_date;
