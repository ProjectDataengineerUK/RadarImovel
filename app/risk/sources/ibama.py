"""Spatial lookup APP/APA/UC via PostGIS `risk_geodata_layers`."""
from sqlalchemy.orm import Session


class IbamaLookup:
    def __init__(self, session: Session) -> None:
        self._session = session

    def contains_point(self, lat: float, lng: float, layer_types: list[str] | None = None) -> list[str]:
        """Return list of layer_type names that contain the point."""
        from sqlalchemy import text

        layer_types = layer_types or ["APP", "APA", "UC", "TI"]
        placeholders = ", ".join(f":t{i}" for i in range(len(layer_types)))
        params: dict = {"lat": lat, "lng": lng}
        params.update({f"t{i}": t for i, t in enumerate(layer_types)})

        rows = self._session.execute(
            text(
                f"SELECT DISTINCT layer_type FROM risk_geodata_layers "
                f"WHERE layer_type IN ({placeholders}) "
                f"AND ST_Contains(geom, ST_SetSRID(ST_Point(:lng, :lat), 4326))"
            ),
            params,
        ).fetchall()
        return [r.layer_type for r in rows]
