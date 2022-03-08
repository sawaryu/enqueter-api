import os
import shutil

from sqlalchemy import text
from app import app
from database import db

"""
# * How to execute *
$ export FLASK_APP=drop.py
$ flask drop_execute
"""


@app.cli.command('drop_execute')
def seed_execute():
    """Drop all tables and migration files."""
    try:
        app.logger.info("---START---")
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        db.session.flush()
        tables = db.session.execute(text("show tables;"))
        for tbl in tables:
            # ex: ('user',) > user
            tbl = str(tbl).replace("('", "").replace("',)", "")
            db.session.execute(text(f'DROP TABLE IF EXISTS {tbl};'))
            db.session.flush()
            app.logger.info(f'{tbl} dropped.')
        dir_path = "./migrations"
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
        app.logger.info("Drop All tables and migration files completely.")
    except:
        app.logger.error("Something fatal error occurred and start rollback.")
        db.session.rollback()
        raise
    finally:
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        db.session.commit()
        db.session.close()
        app.logger.info("---END---")
