from app.models.report import ConditionEnum

# High risk species list
HIGH_RISK_SPECIES = ["tiger", "bear", "elephant", "leopard", "rhino", "crocodile"]
MEDIUM_RISK_SPECIES = ["wolf", "wild boar", "zebra", "giraffe"]

# Nepal coordinates bounds (approximate)
NEPAL_SETTLEMENTS = [
    {"name": "Chitwan", "lat": 27.5291, "lon": 84.3542, "radius_km": 20},
    {"name": "Kathmandu", "lat": 27.7172, "lon": 85.3240, "radius_km": 15},
    {"name": "Pokhara", "lat": 28.2096, "lon": 83.9856, "radius_km": 10},
    {"name": "Bardia", "lat": 28.3167, "lon": 81.5000, "radius_km": 15},
]

def calculate_distance_km(lat1, lon1, lat2, lon2) -> float:
    """Simple distance calculation between two coordinates."""
    import math
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def calculate_risk_score(
    species: str,
    condition: str,
    latitude: float,
    longitude: float
) -> dict:
    """
    Calculate risk score based on species, condition and proximity to settlements.
    Returns severity level and alert message.
    """
    species_lower = species.lower() if species else ""
    score = 0

    # Species risk
    if any(s in species_lower for s in HIGH_RISK_SPECIES):
        score += 40
        species_risk = "high"
    elif any(s in species_lower for s in MEDIUM_RISK_SPECIES):
        score += 20
        species_risk = "medium"
    else:
        score += 10
        species_risk = "low"

    # Condition risk
    if condition == ConditionEnum.rage:
        score += 40
    elif condition == ConditionEnum.injured:
        score += 20
    elif condition == ConditionEnum.poached:
        score += 30
    else:
        score += 5

    # Proximity to settlement
    nearest_settlement = None
    min_distance = float('inf')

    for settlement in NEPAL_SETTLEMENTS:
        distance = calculate_distance_km(
            latitude, longitude,
            settlement["lat"], settlement["lon"]
        )
        if distance < min_distance:
            min_distance = distance
            nearest_settlement = settlement["name"]

    if min_distance < 5:
        score += 30
        proximity = "critical"
    elif min_distance < 15:
        score += 20
        proximity = "high"
    elif min_distance < 30:
        score += 10
        proximity = "medium"
    else:
        score += 0
        proximity = "low"

    # Determine final severity
    if score >= 80:
        severity = "critical"
    elif score >= 60:
        severity = "high"
    elif score >= 35:
        severity = "medium"
    else:
        severity = "low"

    message = (
        f"⚠️ {species} sighting reported near {nearest_settlement} "
        f"({min_distance:.1f} km away). "
        f"Condition: {condition}. Risk level: {severity.upper()}"
    )

    return {
        "severity": severity,
        "score": score,
        "message": message,
        "nearest_settlement": nearest_settlement,
        "distance_km": round(min_distance, 2),
        "species_risk": species_risk,
        "proximity_risk": proximity
    }