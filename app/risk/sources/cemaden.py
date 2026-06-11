"""Spatial lookup zonas de risco (deslizamento/inundação) via PostGIS."""
from sqlalchemy.orm import Session


class CemadenLookup:
    def __init__(self, session: Session) -> None:
        self._session = session

    def risk_zones(self, lat: float, lng: float) -> list[str]:
        """Return risk zone types at the given point (e.g. ['deslizamento'])."""
        from sqlalchemy import text

        rows = self._session.execute(
            text(
                "SELECT DISTINCT layer_type FROM risk_geodata_layers "
                "WHERE layer_type IN ('deslizamento', 'inundacao', 'enchente') "
                "AND ST_Contains(geom, ST_SetSRID(ST_Point(:lng, :lat), 4326))"
            ),
            {"lat": lat, "lng": lng},
        ).fetchall()
        return [r.layer_type for r in rows]
