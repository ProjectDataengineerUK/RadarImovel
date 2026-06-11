"""Gera HTML → WeasyPrint → bytes PDF do relatório de due diligence."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_RISK_COLORS = {
    "low": "#22c55e",
    "moderate": "#eab308",
    "elevated": "#f97316",
    "high": "#ef4444",
    "critical": "#18181b",
}


def generate_report(
    property_data: dict,
    risk_score: dict,
) -> bytes:
    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)
    env.filters["risk_color"] = lambda level: _RISK_COLORS.get(level, "#6b7280")
    template = env.get_template("due_diligence.html")

    html = template.render(
        property=property_data,
        risk=risk_score,
        risk_colors=_RISK_COLORS,
    )

    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except ImportError as exc:
        raise RuntimeError("weasyprint not installed — add it to the api extra in pyproject.toml") from exc
