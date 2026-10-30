import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from alembic.operations.ops import CreateTableOp, ExecuteSQLOp
from sqlalchemy import engine_from_config, pool

# Add the backend package to sys.path so we can import backend.db.session
# The alembic.ini is in packages/backend/, so we need to go up to find src/
backend_src = Path(__file__).parents[1] / "src"
sys.path.insert(0, str(backend_src))

# Import the database URL getter from our backend package
from backend.db.session import get_database_url

# Import models for autogenerate support
from backend.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Normalize database URL for Alembic (ConfigParser treats % specially)
url = get_database_url()
url = url.replace("postgresql://", "postgresql+psycopg://", 1)
url = url.replace("%", "%%")
config.set_main_option("sqlalchemy.url", url)

# target_metadata for autogenerate support
target_metadata = Base.metadata

# Tables to exclude from autogenerate.
# Only tables genuinely managed by external systems (not SQLAlchemy models)
# are excluded here. All application tables are now under Alembic management.
EXCLUDE_TABLES = set()

# Synthetic telemetry tables (lowercase snake_case, timestamp_utc PK)
SYNTHETIC_TABLES = {
    "state_snapshot",
    "thermal_output",
    "power_output",
    "comms_output",
    "radiation_output",
    "cross_model_state",
    "telemetry_packet",
    "anomaly_events",
    "ml_feature_vectors",
}

# ALL TimescaleDB hypertables with their time dimension column.
# Separates "is this a hypertable?" from "is this a synthetic table?".
# Real-data hypertables (close_approaches, orion_ephemeris) use different time columns.
HYPERTABLES = {
    # Synthetic hypertables (timestamp_utc)
    "state_snapshot": "timestamp_utc",
    "thermal_output": "timestamp_utc",
    "power_output": "timestamp_utc",
    "comms_output": "timestamp_utc",
    "radiation_output": "timestamp_utc",
    "cross_model_state": "timestamp_utc",
    "telemetry_packet": "timestamp_utc",
    "anomaly_events": "timestamp_utc",
    "ml_feature_vectors": "timestamp_utc",
    # Real-data hypertables (different time dimensions)
    "close_approaches": "close_approach_time",
    "orion_ephemeris": "epoch",
    # New real-data hypertables
    "goes_integral_protons": "time",
    "dsn_site_geometry": "epoch",
}


def include_object(object, name, type_, reflected, compare_to):
    """Filter objects for autogenerate - exclude existing JPL/NASA tables."""
    return not (type_ == "table" and name in EXCLUDE_TABLES)


def process_revision_directives(context, revision, directives):
    """
    Hook to inject TimescaleDB hypertable creation after each hypertable creation.
    
    This runs during autogenerate and modifies the operation list to add
    create_hypertable() calls immediately after each hypertable's CreateTableOp.
    Also prepends CREATE EXTENSION IF NOT EXISTS timescaledb as the first operation.
    """
    if not directives:
        return
    
    # Only process the first directive (the upgrade path)
    for directive in directives:
        if not hasattr(directive, "upgrade_ops"):
            continue
            
        upgrade_ops = directive.upgrade_ops
        if not upgrade_ops or not hasattr(upgrade_ops, "ops"):
            continue
        
        original_ops = list(upgrade_ops.ops)
        new_ops = []
        seen_create_hypertable = set()  # Guard against duplicate injection
        
        for op in original_ops:
            new_ops.append(op)
            
            # After each CreateTableOp for a hypertable, inject create_hypertable
            if isinstance(op, CreateTableOp):
                table_name = op.table_name
                if table_name in HYPERTABLES and table_name not in seen_create_hypertable:
                    time_column = HYPERTABLES[table_name]
                    # Inject create_hypertable call with correct time dimension
                    hypertable_sql = (
                        f"SELECT create_hypertable('{table_name}', '{time_column}', "
                        f"if_not_exists => TRUE, create_default_indexes => FALSE)"
                    )
                    new_ops.append(
                        ExecuteSQLOp(
                            sqltext=hypertable_sql,
                            execution_options={},
                        )
                    )
                    seen_create_hypertable.add(table_name)
        
        # Prepend TimescaleDB extension creation as the very first operation
        # Only if we have hypertables being created
        if seen_create_hypertable:
            extension_op = ExecuteSQLOp(
                sqltext="CREATE EXTENSION IF NOT EXISTS timescaledb",
                execution_options={},
            )
            new_ops.insert(0, extension_op)
        
        upgrade_ops.ops = new_ops


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()