-- ============================================================
-- Flight Booking Management & Analytics Portal
-- Database Schema (MySQL)
-- ============================================================

CREATE DATABASE IF NOT EXISTS flight_portal;
USE flight_portal;

-- ---------------------------------------------------------
-- AIRPORTS
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS airports (
    airport_id   INT AUTO_INCREMENT PRIMARY KEY,
    code         VARCHAR(10) NOT NULL UNIQUE,     -- e.g. HYD, DEL
    name         VARCHAR(120) NOT NULL,
    city         VARCHAR(100) NOT NULL
);

-- ---------------------------------------------------------
-- FLIGHTS
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS flights (
    flight_id        INT AUTO_INCREMENT PRIMARY KEY,
    flight_number    VARCHAR(20) NOT NULL,
    source_id        INT NOT NULL,
    destination_id   INT NOT NULL,
    departure_time   DATETIME NOT NULL,
    arrival_time     DATETIME NOT NULL,
    total_seats      INT NOT NULL,
    available_seats  INT NOT NULL,
    price            DECIMAL(10, 2) NOT NULL,
    delay_minutes    INT NOT NULL DEFAULT 0,
    status           ENUM('SCHEDULED', 'DELAYED', 'DEPARTED', 'CANCELLED') DEFAULT 'SCHEDULED',
    FOREIGN KEY (source_id) REFERENCES airports(airport_id),
    FOREIGN KEY (destination_id) REFERENCES airports(airport_id)
);

-- ---------------------------------------------------------
-- PASSENGERS
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS passengers (
    passenger_id  INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(120) NOT NULL,
    email         VARCHAR(120) NOT NULL,
    phone         VARCHAR(20)
);

-- ---------------------------------------------------------
-- BOOKINGS
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS bookings (
    booking_id     INT AUTO_INCREMENT PRIMARY KEY,
    passenger_id   INT NOT NULL,
    flight_id      INT NOT NULL,
    seat_number    VARCHAR(10) NOT NULL,
    status         ENUM('CONFIRMED', 'CANCELLED') DEFAULT 'CONFIRMED',
    booking_time   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id),
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
);

-- Helpful indexes for fast lookup / analytics
CREATE INDEX idx_flight_route ON flights(source_id, destination_id);
CREATE INDEX idx_booking_flight ON bookings(flight_id);
CREATE INDEX idx_booking_passenger ON bookings(passenger_id);

-- ---------------------------------------------------------
-- Sample seed data
-- ---------------------------------------------------------
INSERT INTO airports (code, name, city) VALUES
('HYD', 'Rajiv Gandhi International Airport', 'Hyderabad'),
('DEL', 'Indira Gandhi International Airport', 'Delhi'),
('BOM', 'Chhatrapati Shivaji Maharaj Airport', 'Mumbai'),
('BLR', 'Kempegowda International Airport', 'Bengaluru');

INSERT INTO flights (flight_number, source_id, destination_id, departure_time, arrival_time, total_seats, available_seats, price, delay_minutes, status) VALUES
('AI101', 1, 2, '2026-09-15 06:00:00', '2026-09-15 08:15:00', 150, 150, 4500.00, 0, 'SCHEDULED'),
('AI102', 2, 3, '2026-09-15 09:00:00', '2026-09-15 11:00:00', 180, 180, 5200.00, 15, 'DELAYED'),
('AI103', 1, 4, '2026-09-15 10:30:00', '2026-09-15 11:45:00', 120, 120, 3200.00, 0, 'SCHEDULED'),
('AI104', 3, 4, '2026-09-15 13:00:00', '2026-09-15 14:30:00', 160, 160, 3900.00, 0, 'SCHEDULED');
