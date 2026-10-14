from __future__ import annotations

import os

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://planejamento@localhost:5432/planejamento",
        ),
    )
    if test_config:
        app.config.update(test_config)

    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"], pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app.extensions["db_engine"] = engine
    app.extensions["db_session_factory"] = session_factory
    Base.metadata.create_all(engine)

    from .routes import register_routes
    from .importer import register_import_command

    register_routes(app)
    register_import_command(app)
    return app
