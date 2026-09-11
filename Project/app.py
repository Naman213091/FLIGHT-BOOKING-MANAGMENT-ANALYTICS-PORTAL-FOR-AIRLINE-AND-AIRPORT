"""
app.py
Flask backend for the Flight Booking Management & Analytics Portal.

Covers:
  - Booking Management: search, book, change, cancel tickets
  - Live Analytics: daily bookings, seat utilization, on-time rate, route analysis
  - Uses algorithms.py for Dijkstra / A* / Greedy / Hashing
"""

from flask import Flask, request, jsonify
from db import run_query
from algorithms import (
    build_flight_graph,
    dijkstra,
    a_star,
    greedy_seat_allocation,
    lookup_booking,
    booking_cache,
)

app = Flask(__name__)


# ============================================================
# BOOKING MANAGEMENT
# ============================================================

@app.route("/api/flights/search", methods=["GET"])
def search_flights():
    """Search flights by source, destination, and/or date."""
    source = request.args.get("source")
    destination = request.args.get("destination")
    date = request.args.get("date")  # format: YYYY-MM-DD

    query = """
        SELECT f.flight_id, f.flight_number, f.departure_time, f.arrival_time,
               f.available_seats, f.price, f.status,
               src.code AS source_code, dst.code AS destination_code
        FROM flights f
        JOIN airports src ON f.source_id = src.airport_id
        JOIN airports dst ON f.destination_id = dst.airport_id
        WHERE 1=1
    """
    params = []
    if source:
        query += " AND src.code = %s"
        params.append(source.upper())
    if destination:
        query += " AND dst.code = %s"
        params.append(destination.upper())
    if date:
        query += " AND DATE(f.departure_time) = %s"
        params.append(date)

    results = run_query(query, tuple(params), fetch=True)
    return jsonify(results)


@app.route("/api/bookings", methods=["POST"])
def create_booking():
    """
    Book a ticket.
    Body JSON: { "passenger_id": int, "flight_id": int }
    (create the passenger first via /api/passengers if needed)
    """
    data = request.get_json()
    passenger_id = data.get("passenger_id")
    flight_id = data.get("flight_id")

    flight = run_query(
        "SELECT * FROM flights WHERE flight_id = %s", (flight_id,), fetch_one=True
    )
    if not flight:
        return jsonify({"error": "Flight not found"}), 404
    if flight["available_seats"] <= 0:
        return jsonify({"error": "Flight is full"}), 400

    # Greedy algorithm picks the seat
    seat = greedy_seat_allocation(flight_id, flight["total_seats"])
    if seat is None:
        return jsonify({"error": "No seats available"}), 400

    booking_id = run_query(
        "INSERT INTO bookings (passenger_id, flight_id, seat_number, status) "
        "VALUES (%s, %s, %s, 'CONFIRMED')",
        (passenger_id, flight_id, seat),
        commit=True,
    )

    # Seat count updates the moment a ticket is booked
    run_query(
        "UPDATE flights SET available_seats = available_seats - 1 WHERE flight_id = %s",
        (flight_id,),
        commit=True,
    )

    booking = run_query(
        "SELECT * FROM bookings WHERE booking_id = %s", (booking_id,), fetch_one=True
    )
    booking_cache.put(booking_id, booking)

    send_booking_confirmation(passenger_id, booking)

    return jsonify(booking), 201


@app.route("/api/bookings/<int:booking_id>", methods=["GET"])
def get_booking(booking_id):
    """Fast lookup via the hash-index cache, falling back to the DB."""
    booking = lookup_booking(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    return jsonify(booking)


@app.route("/api/bookings/<int:booking_id>", methods=["PUT"])
def change_booking(booking_id):
    """Change a booking to a different flight."""
    data = request.get_json()
    new_flight_id = data.get("new_flight_id")

    booking = run_query(
        "SELECT * FROM bookings WHERE booking_id = %s", (booking_id,), fetch_one=True
    )
    if not booking or booking["status"] != "CONFIRMED":
        return jsonify({"error": "Active booking not found"}), 404

    new_flight = run_query(
        "SELECT * FROM flights WHERE flight_id = %s", (new_flight_id,), fetch_one=True
    )
    if not new_flight or new_flight["available_seats"] <= 0:
        return jsonify({"error": "New flight unavailable"}), 400

    # release old seat
    run_query(
        "UPDATE flights SET available_seats = available_seats + 1 WHERE flight_id = %s",
        (booking["flight_id"],),
        commit=True,
    )

    new_seat = greedy_seat_allocation(new_flight_id, new_flight["total_seats"])

    run_query(
        "UPDATE bookings SET flight_id = %s, seat_number = %s WHERE booking_id = %s",
        (new_flight_id, new_seat, booking_id),
        commit=True,
    )
    run_query(
        "UPDATE flights SET available_seats = available_seats - 1 WHERE flight_id = %s",
        (new_flight_id,),
        commit=True,
    )

    booking_cache.remove(booking_id)  # invalidate stale cache entry
    updated = run_query(
        "SELECT * FROM bookings WHERE booking_id = %s", (booking_id,), fetch_one=True
    )
    return jsonify(updated)


@app.route("/api/bookings/<int:booking_id>", methods=["DELETE"])
def cancel_booking(booking_id):
    """Cancel a booking and release the seat back to the flight."""
    booking = run_query(
        "SELECT * FROM bookings WHERE booking_id = %s", (booking_id,), fetch_one=True
    )
    if not booking or booking["status"] != "CONFIRMED":
        return jsonify({"error": "Active booking not found"}), 404

    run_query(
        "UPDATE bookings SET status = 'CANCELLED' WHERE booking_id = %s",
        (booking_id,),
        commit=True,
    )
    run_query(
        "UPDATE flights SET available_seats = available_seats + 1 WHERE flight_id = %s",
        (booking["flight_id"],),
        commit=True,
    )
    booking_cache.remove(booking_id)

    return jsonify({"message": "Booking cancelled"})


@app.route("/api/passengers", methods=["POST"])
def create_passenger():
    """Register a new passenger."""
    data = request.get_json()
    passenger_id = run_query(
        "INSERT INTO passengers (name, email, phone) VALUES (%s, %s, %s)",
        (data.get("name"), data.get("email"), data.get("phone")),
        commit=True,
    )
    return jsonify({"passenger_id": passenger_id}), 201


def send_booking_confirmation(passenger_id, booking):
    """
    Placeholder for 'Sends booking details straight to the passenger.'
    Wire this up to an email/SMS provider (e.g. SMTP, Twilio) in production.
    """
    passenger = run_query(
        "SELECT * FROM passengers WHERE passenger_id = %s", (passenger_id,), fetch_one=True
    )
    print(f"[CONFIRMATION] Sent to {passenger['email']}: booking #{booking['booking_id']} "
          f"seat {booking['seat_number']} confirmed.")


# ============================================================
# ROUTE FINDING (Dijkstra + A*)
# ============================================================

@app.route("/api/route/optimal", methods=["GET"])
def optimal_route():
    """Cheapest route between two airports using Dijkstra's algorithm."""
    source_id = int(request.args.get("source_id"))
    destination_id = int(request.args.get("destination_id"))

    graph = build_flight_graph()
    path, cost = dijkstra(graph, source_id, destination_id)

    if path is None:
        return jsonify({"error": "No route found"}), 404
    return jsonify({"path": path, "total_cost": cost})


@app.route("/api/route/fast", methods=["GET"])
def fast_route():
    """Airport-to-airport path finding using A* search."""
    source_id = int(request.args.get("source_id"))
    destination_id = int(request.args.get("destination_id"))

    graph = build_flight_graph()
    path, cost = a_star(graph, source_id, destination_id)

    if path is None:
        return jsonify({"error": "No route found"}), 404
    return jsonify({"path": path, "total_cost": cost})


# ============================================================
# LIVE ANALYTICS
# ============================================================

@app.route("/api/analytics/daily-bookings", methods=["GET"])
def daily_bookings():
    """Daily bookings = COUNT(Bookings)"""
    results = run_query(
        """
        SELECT DATE(booking_time) AS booking_date, COUNT(*) AS total_bookings
        FROM bookings
        WHERE status = 'CONFIRMED'
        GROUP BY DATE(booking_time)
        ORDER BY booking_date DESC
        """,
        fetch=True,
    )
    return jsonify(results)


@app.route("/api/analytics/route-bookings", methods=["GET"])
def route_bookings():
    """Route bookings = COUNT(Bookings) grouped by source & destination"""
    results = run_query(
        """
        SELECT src.code AS source, dst.code AS destination, COUNT(b.booking_id) AS total_bookings
        FROM bookings b
        JOIN flights f ON b.flight_id = f.flight_id
        JOIN airports src ON f.source_id = src.airport_id
        JOIN airports dst ON f.destination_id = dst.airport_id
        WHERE b.status = 'CONFIRMED'
        GROUP BY src.code, dst.code
        ORDER BY total_bookings DESC
        """,
        fetch=True,
    )
    return jsonify(results)


@app.route("/api/analytics/seat-utilization", methods=["GET"])
def seat_utilization():
    """Seat utilization (%) = Booked seats ÷ Total seats × 100"""
    results = run_query(
        """
        SELECT flight_id, flight_number, total_seats, available_seats,
               ROUND((total_seats - available_seats) / total_seats * 100, 2) AS utilization_pct
        FROM flights
        """,
        fetch=True,
    )
    return jsonify(results)


@app.route("/api/analytics/on-time-rate", methods=["GET"])
def on_time_rate():
    """On-time rate (%) = On-time flights ÷ Total flights × 100"""
    result = run_query(
        """
        SELECT
            ROUND(SUM(CASE WHEN delay_minutes = 0 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS on_time_rate_pct,
            COUNT(*) AS total_flights
        FROM flights
        """,
        fetch_one=True,
    )
    return jsonify(result)


@app.route("/api/analytics/route-analysis", methods=["GET"])
def route_analysis():
    """For each route: total bookings, avg delay, seat utilization — ranked by demand."""
    results = run_query(
        """
        SELECT src.code AS source, dst.code AS destination,
               COUNT(b.booking_id) AS total_bookings,
               ROUND(AVG(f.delay_minutes), 2) AS avg_delay_minutes,
               ROUND((f.total_seats - f.available_seats) / f.total_seats * 100, 2) AS seat_utilization_pct
        FROM flights f
        LEFT JOIN bookings b ON f.flight_id = b.flight_id AND b.status = 'CONFIRMED'
        JOIN airports src ON f.source_id = src.airport_id
        JOIN airports dst ON f.destination_id = dst.airport_id
        GROUP BY src.code, dst.code, f.total_seats, f.available_seats
        ORDER BY total_bookings DESC
        """,
        fetch=True,
    )
    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
