from app.models.report import ConditionEnum

# ── New risk rules (per product spec) ────────────────────────────────────────
#
# Condition: normal / injured / suspicious (poached)
#   0–3 km  → HIGH
#   4–10 km → MEDIUM
#   > 10 km → LOW
#
# Condition: rage
#   0–3 km  → CRITICAL
#   4–10 km → HIGH
#   > 10 km → LOW
#
# "km" here means straight-line distance from the reporter's GPS coordinates
# to the nearest known settlement.

NEPAL_SETTLEMENTS = [
    {"name": "Chitwan",   "lat": 27.5291, "lon": 84.3542},
    {"name": "Kathmandu", "lat": 27.7172, "lon": 85.3240},
    {"name": "Pokhara",   "lat": 28.2096, "lon": 83.9856},
    {"name": "Bardia",    "lat": 28.3167, "lon": 81.5000},
]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _nearest_settlement(latitude: float, longitude: float) -> tuple:
    best_name = "the area"
    best_dist = float("inf")
    for s in NEPAL_SETTLEMENTS:
        d = _haversine_km(latitude, longitude, s["lat"], s["lon"])
        if d < best_dist:
            best_dist = d
            best_name = s["name"]
    return best_name, round(best_dist, 2)


def calculate_risk_score(
    species: str,
    condition: str,
    latitude: float,
    longitude: float,
) -> dict:
    """
    Derive alert severity from condition x proximity.

    Severity matrix:
      normal/injured/suspicious:  0-3km=HIGH, 4-10km=MEDIUM, >10km=LOW
      rage:                       0-3km=CRITICAL, 4-10km=HIGH, >10km=LOW
    """
    settlement_name, distance_km = _nearest_settlement(latitude, longitude)

    is_rage = (condition == ConditionEnum.rage or str(condition).lower() == "rage")

    if is_rage:
        if distance_km <= 3:
            severity = "critical"
        elif distance_km <= 10:
            severity = "high"
        else:
            severity = "low"
    else:
        if distance_km <= 3:
            severity = "high"
        elif distance_km <= 10:
            severity = "medium"
        else:
            severity = "low"

    condition_str = str(condition).replace("ConditionEnum.", "").lower()
    species_display = (species or "Unknown").capitalize()
    lat_str = f"{latitude:.4f}"
    lng_str = f"{longitude:.4f}"

    message = (
        f"{species_display} spotted in {condition_str} condition near "
        f"{lat_str}, {lng_str}"
    )

    return {
        "severity": severity,
        "score": {"critical": 100, "high": 75, "medium": 50, "low": 25}[severity],
        "message": message,
        "nearest_settlement": settlement_name,
        "distance_km": distance_km,
        "species_risk": "n/a",
        "proximity_risk": severity,
    }
