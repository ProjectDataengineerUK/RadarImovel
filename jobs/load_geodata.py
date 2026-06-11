"""Cloud Run Job: loads risk geodata (ICMBio, FUNAI, CEMADEN, IBGE, Atlas Brasil, IPEA)."""
import os
import sys

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.geodata.loaders.atlas_brasil import AtlasBrasilLoader
from app.geodata.loaders.cemaden import CemadenLoader
from app.geodata.loaders.funai import FunaiLoader
from app.geodata.loaders.ibge_mesh import IbgeMeshLoader
from app.geodata.loaders.ibge_sidra import IbgeSidraLoader
from app.geodata.loaders.icmbio import IcmbioLoader
from app.geodata.loaders.ipea_violence import IpeaViolenceLoader

settings = get_settings()
log = configure_logging("load_geodata")


def run() -> None:
    dry_run = os.environ.get("DRY_RUN", "").lower() == "true"
    skip_layers = {s for s in os.environ.get("SKIP_LAYERS", "").lower().split(",") if s}
    log.info("job.start", dry_run=dry_run, skip_layers=sorted(skip_layers))

    partial_layers: list[str] = []
    mesh: dict = {}

    with SessionLocal() as session:
        # 1. IBGE Mesh — download shapefile, populate ibge_municipality_stats base rows
        if "ibge_mesh" not in skip_layers:
            log.info("job.ibge_mesh.start")
            if not dry_run:
                try:
                    mesh_result = IbgeMeshLoader().load_mesh(session)
                    mesh = mesh_result.mesh
                    log.info(
                        "job.ibge_mesh.done",
                        municipalities=mesh_result.municipalities_loaded,
                        errors=len(mesh_result.errors),
                    )
                    for e in mesh_result.errors[:5]:
                        log.warning("job.ibge_mesh.error", detail=e)
                except Exception as exc:
                    log.error("job.ibge_mesh.failed", error=str(exc))
                    partial_layers.append("ibge_mesh")

        # 2. Geodata layers
        geo_loaders: list[tuple[str, object]] = [
            ("icmbio", IcmbioLoader()),
            ("funai", FunaiLoader()),
            ("cemaden", CemadenLoader()),
        ]

        for name, loader in geo_loaders:
            if name in skip_layers:
                log.info("job.layer.skipped", layer=name)
                continue
            log.info("job.layer.start", layer=name)
            if dry_run:
                continue
            try:
                extra = {"mesh": mesh} if name == "cemaden" else {}
                stats = loader.load(session, **extra)  # type: ignore[union-attr]
                log.info(
                    "job.layer.done",
                    layer=name,
                    polygons=stats.polygons_loaded,
                    errors=len(stats.errors),
                )
                for e in stats.errors[:3]:
                    log.warning("job.layer.error", layer=name, detail=e)
                if stats.errors:
                    partial_layers.append(name)
            except Exception as exc:
                log.error("job.layer.failed", layer=name, error=str(exc))
                partial_layers.append(name)

        # 3. Municipality stats
        stat_loaders: list[tuple[str, object]] = [
            ("ibge_sidra", IbgeSidraLoader()),
            ("atlas_brasil", AtlasBrasilLoader()),
            ("ipea_violence", IpeaViolenceLoader()),
        ]

        for name, loader in stat_loaders:
            if name in skip_layers:
                log.info("job.stats.skipped", loader=name)
                continue
            log.info("job.stats.start", loader=name)
            if dry_run:
                continue
            try:
                extra = {"gcs_bucket": settings.gcs_bucket_raw} if name == "ipea_violence" else {}
                stats = loader.load(session, **extra)  # type: ignore[union-attr]
                log.info(
                    "job.stats.done",
                    loader=name,
                    rows=stats.polygons_loaded,
                    errors=len(stats.errors),
                )
                for e in stats.errors[:3]:
                    log.warning("job.stats.error", loader=name, detail=e)
            except Exception as exc:
                log.error("job.stats.failed", loader=name, error=str(exc))

    log.info("job.done", partial_layers=partial_layers, mesh_municipalities=len(mesh))

    geo_layer_names = {"icmbio", "funai", "cemaden"} - skip_layers
    all_geo_failed = geo_layer_names and geo_layer_names.issubset(set(partial_layers))
    if all_geo_failed and len(mesh) == 0:
        log.error("job.total_failure")
        sys.exit(1)


if __name__ == "__main__":
    run()
