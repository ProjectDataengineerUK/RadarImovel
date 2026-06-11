"""Geodata ingestion — loaders for risk spatial layers and municipality stats."""
from app.geodata.loaders.atlas_brasil import AtlasBrasilLoader
from app.geodata.loaders.cemaden import CemadenLoader
from app.geodata.loaders.funai import FunaiLoader
from app.geodata.loaders.ibge_mesh import IbgeMeshLoader
from app.geodata.loaders.ibge_sidra import IbgeSidraLoader
from app.geodata.loaders.icmbio import IcmbioLoader
from app.geodata.loaders.ipea_violence import IpeaViolenceLoader

__all__ = [
    "AtlasBrasilLoader",
    "CemadenLoader",
    "FunaiLoader",
    "IbgeMeshLoader",
    "IbgeSidraLoader",
    "IcmbioLoader",
    "IpeaViolenceLoader",
]
