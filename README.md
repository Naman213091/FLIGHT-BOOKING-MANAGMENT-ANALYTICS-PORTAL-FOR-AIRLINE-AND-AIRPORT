# Flight Booking Management & Analytics Portal — Backend

Matches the tech stack from the project deck: **Python + Flask** backend, **MySQL** database.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create the database:
   ```
   mysql -u root -p < schema.sql
   ```

3. Update the credentials in `db.py` (`DB_CONFIG`) to match your MySQL setup.

4. Run the server:
   ```
   python app.py
   ```
   The API runs at `http://localhost:5000`.

## Files

- `schema.sql` — Tables for Airports, Flights, Passengers, Bookings (+ sample data)
- `db.py` — MySQL connection pool + query helper
- `algorithms.py` — Dijkstra (optimal route), A* (fast path finding), Greedy (seat allocation), Hashing (fast lookup)
- `app.py` — Flask REST API: booking management + live analytics endpoints

## Key Endpoints

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/flights/search?source=HYD&destination=DEL&date=2026-09-15` | Search flights |
| POST | `/api/bookings` | Book a ticket (`{passenger_id, flight_id}`) |
| GET | `/api/bookings/<id>` | Fetch a booking (hash-cache backed) |
| PUT | `/api/bookings/<id>` | Change a booking to another flight |
| DELETE | `/api/bookings/<id>` | Cancel a booking |
| GET | `/api/route/optimal?source_id=1&destination_id=2` | Cheapest route (Dijkstra) |
| GET | `/api/route/fast?source_id=1&destination_id=2` | Fast path find (A*) |
| GET | `/api/analytics/daily-bookings` | Bookings per day |
| GET | `/api/analytics/route-bookings` | Bookings per route |
| GET | `/api/analytics/seat-utilization` | Seat fill % per flight |
| GET | `/api/analytics/on-time-rate` | % flights with no delay |
| GET | `/api/analytics/route-analysis` | Combined route demand ranking |
