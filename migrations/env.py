from alembic import context
from sqlalchemy import create_engine, pool

from disasterops.config import Settings
from disasterops.models import Base


def run_migrations():
    url = Settings().postgres_url()
    if context.is_offline_mode():
        context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
    else:
        provided = context.config.attributes.get("connection")
        if provided is not None:
            context.configure(connection=provided, target_metadata=Base.metadata)
            with context.begin_transaction():
                context.run_migrations()
            return
        engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True)
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=Base.metadata)
            with context.begin_transaction():
                context.run_migrations()


run_migrations()
