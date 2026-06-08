from logging.config import fileConfig
from alembic import context
from app.models.base import Base
import app.models  # noqa: F401 — registra todos os modelos no metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Import engine here (not at module top) so Cloud SQL Connector initialises
    # only when actually running migrations — not during alembic config loading.
    from app.core.database import engine  # noqa: PLC0415

    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
