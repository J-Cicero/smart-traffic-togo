from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core.config import ConfigurationApplication
from app.core.database import Base
import app.intersection.models  # Charge les métadonnées de toutes les tables

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Injection dynamique de l'URL de base de données depuis la configuration de l'application
app_config = ConfigurationApplication()
config.set_main_option("sqlalchemy.url", app_config.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Exécution des migrations en mode 'offline'."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Exécution des migrations en mode 'online'."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
