import os.path as op
import logging
from flask import Flask, config, has_app_context
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_migrate import Migrate
from celery import Celery


# Set up the Flask app
templates_dir = op.join(op.dirname(__file__), 'templates')
static_dir = op.join(op.dirname(__file__), 'static')

app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)
app.config.from_object('config')



# Initialise database model
db = SQLAlchemy(app)  #, engine_options={'pool_pre_ping': True})


# Initialise Alembic database migrations
migrate = Migrate(app, db)


# Initialise Flask mail
mail = Mail(app)

# Initialise Celery for background tasks (including periodically scheduled)
celery = Celery(
    app.import_name,
    backend=app.config['CELERY_RESULT_BACKEND'],
    broker=app.config['CELERY_BROKER_URL'])

celery.conf.update(app.config)

class ContextTask(celery.Task):  # pylint: disable=too-few-public-methods
    def __call__(self, *args, **kwargs):
        if not has_app_context():
            with app.app_context():
                return self.run(*args, **kwargs)
        else:
            return self.run(*args, **kwargs)

celery.Task = ContextTask

# Import models, views and periodic tasks into package root to register them
from .models import *  # pylint: disable=wrong-import-position
from .tasks import schedule  # pylint: disable=wrong-import-position


# # To avoid debug being overridden by IDE (i.e. VSCode)
# app.config['DEBUG_WAS_SET'] = app.debug


if 'gunicorn.error' in logging.root.manager.loggerDict:
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)  # pylint: disable=no-member
