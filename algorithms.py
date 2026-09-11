"""
algorithms.py
Implements the four algorithms named on the "Algorithm" slide:

1. Dijkstra's Algorithm  -> optimal (cheapest) route between airports
2. A* Search Algorithm   -> faster airport-to-airport path finding using a heuristic
3. Greedy Algorithm      -> seat allocation (pick best available seat)
4. Hashing               -> O(1) booking / passenger lookup
"""

import heapq
from db import run_query


# ============================================================
# 1. DIJKSTRA'S ALGORITHM — optimal route calculation
# ============================================================
def build_flight_graph():
    """
    Builds a weighted graph of airports from the flights table.
    Nodes  = airport_id
    Edges  = flight_id, weighted by ticket price (cost of the route)
    """
    flights = run_query(
        "SELECT flight_id, source_id, destination_id, price "
        "FROM flights WHERE status != 'CANCELLED'",
        fetch=True,
    )

    graph = {}
    for f in flights:
        graph.setdefault(f["source_id"], []).append(
            {"to": f["destination_id"], "weight": float(f["price"]), "flight_id": f["flight_id"]}
        )
    return graph


def dijkstra(graph, start_id, end_id):
    """
    Returns the cheapest path (list of airport_ids) and total cost
    from start_id to end_id, or (None, float('inf')) if unreachable.
    """
    distances = {start_id: 0}
    previous = {}
    visited = set()
    heap = [(0, start_id)]

    while heap:
        current_dist, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)

        if node == end_id:
            break

        for edge in graph.get(node, []):
            neighbor = edge["to"]
            new_dist = current_dist + edge["weight"]
            if new_dist < distances.get(neighbor, float("inf")):
                distances[neighbor] = new_dist
                previous[neighbor] = node
                heapq.heappush(heap, (new_dist, neighbor))

    if end_id not in distances:
        return None, float("inf")

    # Reconstruct path
    path = [end_id]
    while path[-1] != start_id:
        path.append(previous[path[-1]])
    path.reverse()

    return path, distances[end_id]


# ============================================================
# 2. A* SEARCH ALGORITHM — heuristic-guided path finding
# ============================================================
def _load_airport_coords():
    """
    A* needs a heuristic. We approximate straight-line distance using
    a simple coordinate table (extend the airports table with lat/lng
    for real use — this is a placeholder set for demo purposes).
    """
    return {
        1: (17.2403, 78.4294),   # HYD
        2: (28.5562, 77.1000),   # DEL
        3: (19.0896, 72.8656),   # BOM
        4: (13.1986, 77.7066),   # BLR
    }


def _euclidean_heuristic(a, b, coords):
    (x1, y1), (x2, y2) = coords.get(a, (0, 0)), coords.get(b, (0, 0))
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


def a_star(graph, start_id, end_id):
    """
    Returns the fastest-to-compute path using A* with a straight-line
    distance heuristic between airport coordinates.
    """
    coords = _load_airport_coords()
    open_set = [(0, start_id)]
    g_score = {start_id: 0}
    previous = {}
    visited = set()

    while open_set:
        _, node = heapq.heappop(open_set)
        if node in visited:
            continue
        visited.add(node)

        if node == end_id:
            path = [end_id]
            while path[-1] != start_id:
                path.append(previous[path[-1]])
            path.reverse()
            return path, g_score[end_id]

        for edge in graph.get(node, []):
            neighbor = edge["to"]
            tentative_g = g_score[node] + edge["weight"]
            if tentative_g < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = tentative_g
                previous[neighbor] = node
                f_score = tentative_g + _euclidean_heuristic(neighbor, end_id, coords)
                heapq.heappush(open_set, (f_score, neighbor))

    return None, float("inf")


# ============================================================
# 3. GREEDY ALGORITHM — seat allocation
# ============================================================
def greedy_seat_allocation(flight_id, total_seats):
    """
    Greedily picks the first (lowest-numbered) unbooked seat for a flight.
    Seats are labelled 1A, 1B, 1C, 1D, 2A, 2B ... (4 seats per row).
    """
    booked = run_query(
        "SELECT seat_number FROM bookings WHERE flight_id = %s AND status = 'CONFIRMED'",
        (flight_id,),
        fetch=True,
    )
    booked_seats = {row["seat_number"] for row in booked}

    letters = ["A", "B", "C", "D"]
    seat_num = 1
    while True:
        for letter in letters:
            seat = f"{seat_num}{letter}"
            if seat not in booked_seats:
                if (seat_num - 1) * 4 + letters.index(letter) < total_seats:
                    return seat
                else:
                    return None  # flight is full
        seat_num += 1


# ============================================================
# 4. HASHING — O(1) booking / passenger lookup
# ============================================================
class HashIndex:
    """
    A lightweight in-memory hash index used to cache lookups for
    frequently accessed bookings/passengers/flights, avoiding a
    database round-trip on every request. Backed by a Python dict
    (a hash table), giving average O(1) get/set/delete.
    """

    def __init__(self):
        self._table = {}

    def put(self, key, value):
        self._table[key] = value

    def get(self, key):
        return self._table.get(key)

    def remove(self, key):
        self._table.pop(key, None)

    def contains(self, key):
        return key in self._table


# Process-wide caches (simple demo; swap for Redis in production)
booking_cache = HashIndex()
passenger_cache = HashIndex()


def lookup_booking(booking_id):
    """Fast O(1) booking lookup, falling back to the DB on a cache miss."""
    cached = booking_cache.get(booking_id)
    if cached:
        return cached

    booking = run_query(
        "SELECT * FROM bookings WHERE booking_id = %s", (booking_id,), fetch_one=True
    )
    if booking:
        booking_cache.put(booking_id, booking)
    return booking
