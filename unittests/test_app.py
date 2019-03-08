# -*- coding: utf-8 -*-

from flask import Flask
from flask import _app_ctx_stack
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from flask_sqlalchemy import BaseQuery

# database session registry object, configured from
# create_app factory
DbSession = scoped_session(
    sessionmaker(),
    # __ident_func__ should be hashable, therefore used
    # for recognizing different incoming requests
    scopefunc=_app_ctx_stack.__ident_func__
)

def create_app(name_handler, config_object):
    """
    Application factory

    :param name_handler: name of the application.
    :param config_object: the configuration object.
    """
    app = Flask(name_handler)
    app.config.update(config_object)
    app.engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])

    global DbSession
    # BaseQuery class provides some additional methods like
    # first_or_404() or get_or_404() -- borrowed from
    # mitsuhiko's Flask-SQLAlchemy
    DbSession.configure(bind=app.engine, query_cls=BaseQuery)

    @app.teardown_appcontext
    def teardown(exception=None):
        global DbSession
        if DbSession:
            DbSession.remove()

    return app