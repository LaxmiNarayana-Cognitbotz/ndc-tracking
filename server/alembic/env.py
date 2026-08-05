import asyncio
import os
import sys
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from config.database import Base, DATABASE_URL

# Import all models here so Alembic can read their metadata
import importlib
importlib.import_module("app.models")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
load_dotenv(verbose=True)


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
escaped_url = DATABASE_URL.replace("%", "%%")
config.set_main_option("sqlalchemy.url", escaped_url)

def process_revision_directives(context, revision, directives):
    """Skip generating empty migrations if no model changes are detected."""
    if config.cmd_opts and config.cmd_opts.autogenerate:
        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []
            print("No changes in schema detected.")

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        process_revision_directives=process_revision_directives,
        compare_type=True,
        compare_server_default=True
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

if context.is_offline_mode():
    print("Offline migrations are not supported in this simplified config.")
else:
    asyncio.run(run_async_migrations())
