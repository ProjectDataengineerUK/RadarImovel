import io
from typing import Iterator
import pandas as pd
from app.connectors.base import RawProperty
from app.core.logging import logger

# Mapeamento de colunas do XLSX da Caixa para nomes internos
COLUMN_MAP = {
    "Número do imóvel": "external_code",
    "UF": "state",
    "Cidade": "city",
    "Bairro": "neighborhood",
    "Endereço": "address",
    "Preço": "current_value",
    "Valor de avaliação": "appraisal_value",
    "Desconto": "discount_percent",
    "Descrição": "title",
    "Modalidade de venda": "sale_modality",
    "Link de acesso": "official_url",
    "Situação do imóvel": "occupancy_status",
    "Tipo do imóvel": "property_type",
}


class CaixaParser:
    def parse(self, raw_bytes: bytes, source_url: str, uf: str) -> Iterator[RawProperty]:
        if not raw_bytes:
            logger.warning("caixa.parser.empty_bytes", source_url=source_url)
            return

        try:
            df = pd.read_excel(io.BytesIO(raw_bytes), header=0, dtype=str)
            df = df.rename(columns=COLUMN_MAP)
            df = df.dropna(subset=["external_code"])

            for _, row in df.iterrows():
                raw_data = row.to_dict()
                raw_data["state"] = uf  # garante UF correta mesmo se ausente no arquivo
                external_code = str(raw_data.get("external_code", "")).strip()
                if not external_code:
                    continue
                yield RawProperty(
                    external_code=external_code,
                    source_url=source_url,
                    raw_data=raw_data,
                    bank_code="caixa",
                    source_name=f"caixa_lista_{uf}",
                )
        except Exception as exc:
            logger.error("caixa.parser.failed", source_url=source_url, error=str(exc))
