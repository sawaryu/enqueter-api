from datetime import timedelta, datetime

import click
from sqlalchemy import func
from api.model.aggregate import point
from api.model.user import User, PointStats
from app import app
from database import db

"""
# * How to execute *
$ export FLASK_APP=batch.py
$ flask batch_execute "Batch job starting..."
"""


@app.cli.command('batch_execute')
@click.argument('message')
def batch_execute(message: str) -> None:
    app.logger.info("--- START ---")
    db.session.begin()
    try:
        step_1()
        # ..another steps if exists.
        db.session.commit()
        app.logger.info("Successfully finished all steps.")
    except:
        db.session.rollback()
        app.logger.error("Something fatal error happened. take rollback completely.")
        raise
    finally:
        db.session.close()
        app.logger.info("--- END ---")


def step_1():
    """
    Firstly Aggregate data.
    """
    results: list[dict] = []
    for (loop, period) in enumerate([{"days": 365 * 100}, {"days": 30}, {"days": 7}]):
        """Point & Answer count"""
        point_entities = db.session.query(User, func.sum(point.c.point).label("points")) \
            .join(point, point.c.user_id == User.id) \
            .filter(point.c.created_at > (datetime.now() - timedelta(**period))) \
            .group_by(User.id) \
            .order_by(func.sum(point.c.point).desc()) \
            .order_by(User.id.desc()) \
            .all()

        for (index_rank, entity) in enumerate(point_entities):
            if loop == 0:
                init_dict = {
                    "user_id": entity.User.id,
                    "total_rank": index_rank + 1,
                    "total_point": int(entity.points),
                    "month_rank": None,
                    "month_point": None,
                    "week_rank": None,
                    "week_point": None
                }
                results.append(init_dict)
            elif loop == 1:
                month_dict = {
                    "month_rank": index_rank + 1,
                    "month_point": int(entity.points),
                }
                for (index, r) in enumerate(results):
                    if r["user_id"] == entity.User.id:
                        results[index] = results[index] | month_dict
                        break
            elif loop == 2:
                week_dict = {
                    "week_rank": index_rank + 1,
                    "week_point": int(entity.points),
                }
                for (index, r) in enumerate(results):
                    if r["user_id"] == entity.User.id:
                        results[index] = results[index] | week_dict
                        break
    app.logger.info("Successfully collected data.")

    """
    Finally, Update or Create records
    """
    for r in results:
        stats = PointStats.find_by_user_id(r["user_id"])
        # update
        if stats:
            stats.total_rank_point = r["total_rank"]
            stats.total_point = r["total_point"]
            stats.month_rank_point = r["month_rank"]
            stats.month_point = r["month_point"]
            stats.week_rank_point = r["week_rank"]
            stats.week_point = r["week_point"]
        # create
        else:
            stats = PointStats(**r)
            db.session.add(stats)
        db.session.flush()
    app.logger.info("Successfully finished Step1.")
