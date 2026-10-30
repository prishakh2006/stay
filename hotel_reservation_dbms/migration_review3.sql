-- Blue Orchid review 3 migration for MySQL 8.
-- Preserves existing tables, data, foreign keys, and reservation triggers.
USE hotel_reservation;

-- Add the correction flag only when it does not already exist.
SET @migration_sql = IF(
    (
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'Customer'
          AND COLUMN_NAME = 'phone_needs_update'
    ) = 0,
    'ALTER TABLE Customer ADD COLUMN phone_needs_update TINYINT(1) NOT NULL DEFAULT 0',
    'SELECT 1'
);
PREPARE migration_stmt FROM @migration_sql;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

-- Customer.phone already exists. Flag and backfill only missing or blank values.
UPDATE Customer
SET phone = 'PENDING',
    phone_needs_update = 1
WHERE phone IS NULL
   OR TRIM(phone) = '';

-- Create Review only when it does not already exist.
CREATE TABLE IF NOT EXISTS Review (
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

-- Quote User because it can conflict with SQL keywords.
CREATE TABLE IF NOT EXISTS `User` (
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

-- Add cancel_reason only when it does not already exist.
SET @migration_sql = IF(
    (
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'Reservation'
          AND COLUMN_NAME = 'cancel_reason'
    ) = 0,
    'ALTER TABLE Reservation ADD COLUMN cancel_reason VARCHAR(255) NULL',
    'SELECT 1'
);
PREPARE migration_stmt FROM @migration_sql;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;

-- Add cancelled_by only when it does not already exist.
SET @migration_sql = IF(
    (
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'Reservation'
          AND COLUMN_NAME = 'cancelled_by'
    ) = 0,
    'ALTER TABLE Reservation ADD COLUMN cancelled_by ENUM(''customer'', ''admin'') NULL',
    'SELECT 1'
);
PREPARE migration_stmt FROM @migration_sql;
EXECUTE migration_stmt;
DEALLOCATE PREPARE migration_stmt;
