from app.core.config import get_settings


def calculate_score(property_data: dict) -> int:
    settings = get_settings()
    discount = min(
        float(property_data.get("discount_percent") or 0),
        settings.score_discount_max_points,
    )
    occupancy_bonus = (
        settings.score_occupancy_bonus
        if property_data.get("occupancy_status") == "Desocupado"
        else 0
    )
    return int(min(discount + occupancy_bonus, 100))
