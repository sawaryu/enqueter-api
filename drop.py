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
    """Drop all tables."""
    try:
        app.logger.info("---START---")
        db.session.begin()
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        db.session.flush()
        tables = db.session.execute(text("show tables;"))
        for tbl in tables:
            # ex: ('user',) > user
            tbl = str(tbl).replace("('", "").replace("',)", "")
            db.session.execute(text(f'DROP TABLE IF EXISTS {tbl};'))
            db.session.flush()
            app.logger.info(f'{tbl} dropped.')
        app.logger.info("Drop All tables completely.")
    except:
        app.logger.error("Something fatal error occurred and start rollback.")
        db.session.rollback()
        raise
    finally:
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        db.session.commit()
        db.session.close()
        app.logger.info("---END---")
