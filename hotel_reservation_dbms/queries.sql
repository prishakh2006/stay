USE hotel_reservation;

-- 1. Rooms available for the whole requested stay.
-- Change the two dates to test another date range.
SET @date_in = '2026-10-20';
SET @date_out = '2026-10-23';
SELECT rm.room_no, rt.type_name, rt.capacity, rt.price_per_night
FROM Room rm
JOIN RoomType rt ON rt.type_id = rm.type_id
WHERE NOT EXISTS (
    SELECT 1 FROM Reservation r
    WHERE r.room_id = rm.room_id
      AND r.status = 'Booked'
      AND @date_in < r.check_out
      AND @date_out > r.check_in
)
ORDER BY rm.room_no;

-- 2. Booking history for one customer; total is nights x room price.
SET @customer_name = 'Priya Nair';
SELECT c.name, r.reservation_id, rm.room_no, r.check_in, r.check_out,
       DATEDIFF(r.check_out, r.check_in) AS nights,
       rt.price_per_night,
       DATEDIFF(r.check_out, r.check_in) * rt.price_per_night AS stay_total,
       r.status
FROM Customer c
JOIN Reservation r ON r.customer_id = c.customer_id
JOIN Room rm ON rm.room_id = r.room_id
JOIN RoomType rt ON rt.type_id = rm.type_id
WHERE c.name = @customer_name
ORDER BY r.check_in;

-- 3. Reservations with balance remaining (zero balance is not pending).
SELECT r.reservation_id, c.name, rm.room_no,
       DATEDIFF(r.check_out, r.check_in) * rt.price_per_night AS bill_total,
       COALESCE(SUM(p.amount), 0) AS amount_paid,
       (DATEDIFF(r.check_out, r.check_in) * rt.price_per_night)
          - COALESCE(SUM(p.amount), 0) AS pending_amount
FROM Reservation r
JOIN Customer c ON c.customer_id = r.customer_id
JOIN Room rm ON rm.room_id = r.room_id
JOIN RoomType rt ON rt.type_id = rm.type_id
LEFT JOIN Payment p ON p.reservation_id = r.reservation_id
WHERE r.status <> 'Cancelled'
GROUP BY r.reservation_id, c.name, rm.room_no, r.check_in, r.check_out, rt.price_per_night
HAVING pending_amount > 0
ORDER BY r.check_in;

-- 4. Occupancy on a given date: a room is occupied if check-in <= date < check-out.
SET @occupancy_date = '2026-10-20';
SELECT COUNT(DISTINCT r.room_id) AS rooms_occupied,
       (SELECT COUNT(*) FROM Room) AS total_rooms
FROM Reservation r
WHERE r.status = 'Booked'
  AND r.check_in <= @occupancy_date
  AND r.check_out > @occupancy_date;
