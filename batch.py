from datetime import timedelta, datetime
from sqlalchemy import func
from api.model.aggregate import point, response
from api.model.user import User, PointStats, ResponseStats
from app import app
from database import db

"""
# * How to execute *
$ export FLASK_APP=batch.py
$ flask batch_execute "Batch job starting..."
"""


@app.cli.command('batch_execute')
def batch_execute() -> None:
    """Aggregate ranking data."""
    try:
        app.logger.info("---START---")
        db.session.begin()
        step_0()
        step_1()
        step_2()
        db.session.commit()
        app.logger.info("Finished all steps successfully.")
    except:
        app.logger.error("Something fatal error occurred and start rollback.")
        db.session.rollback()
        raise
    finally:
        db.session.close()
        app.logger.info("---END---")


def step_0() -> None:
    """Delete non active users."""
    app.logger.info("---Start step0---")
    User.query.filter_by(is_deleted=True).delete()
    db.session.flush()
    app.logger.info("---End step0---")


def step_1() -> None:
    """Firstly Aggregate data."""
    app.logger.info("---Start step1---")
    results: list[dict] = []
    for (loop, period) in enumerate([{"days": 365 * 100}, {"days": 30}, {"days": 7}]):
        """Point"""
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

    """Finally, Update or Create records."""
    for r in results:
        stats = PointStats.find_by_user_id(r["user_id"])
        # update
        if stats:
            stats.total_rank = r["total_rank"]
            stats.total_point = r["total_point"]
            stats.month_rank = r["month_rank"]
            stats.month_point = r["month_point"]
            stats.week_rank = r["week_rank"]
            stats.week_point = r["week_point"]
        # create
        else:
            stats = PointStats(**r)
            db.session.add(stats)
        db.session.flush()
    app.logger.info("Successfully create and update data.")
    app.logger.info("---End step1---")


def step_2() -> None:
    """Firstly Aggregate data."""
    app.logger.info("---Start step2---")
    results: list[dict] = []
    for (loop, period) in enumerate([{"days": 365 * 100}, {"days": 30}, {"days": 7}]):
        """response & Answer count"""
        response_entities = db.session.query(User, func.count(response.c.user_id).label("responses")) \
            .join(response, response.c.user_id == User.id) \
            .filter(response.c.created_at > (datetime.now() - timedelta(**period))) \
            .group_by(User.id) \
            .order_by(func.count(response.c.user_id).desc()) \
            .order_by(User.id.desc()) \
            .all()

        for (index_rank, entity) in enumerate(response_entities):
            if loop == 0:
                init_dict = {
                    "user_id": entity.User.id,
                    "total_rank": index_rank + 1,
                    "total_response": int(entity.responses),
                    "month_rank": None,
                    "month_response": None,
                    "week_rank": None,
                    "week_response": None
                }
                results.append(init_dict)
            elif loop == 1:
                month_dict = {
                    "month_rank": index_rank + 1,
                    "month_response": int(entity.responses),
                }
                for (index, r) in enumerate(results):
                    if r["user_id"] == entity.User.id:
                        results[index] = results[index] | month_dict
                        break
            elif loop == 2:
                week_dict = {
                    "week_rank": index_rank + 1,
                    "week_response": int(entity.responses),
                }
                for (index, r) in enumerate(results):
                    if r["user_id"] == entity.User.id:
                        results[index] = results[index] | week_dict
                        break
    app.logger.info("Successfully collected data.")

    """Finally, Update or Create records."""
    for r in results:
        stats = ResponseStats.find_by_user_id(r["user_id"])
        # update
        if stats:
            stats.total_rank = r["total_rank"]
            stats.total_response = r["total_response"]
            stats.month_rank = r["month_rank"]
            stats.month_response = r["month_response"]
            stats.week_rank = r["week_rank"]
            stats.week_response = r["week_response"]
        # create
        else:
            stats = ResponseStats(**r)
            db.session.add(stats)
        db.session.flush()
    app.logger.info("Successfully create and update data.")
    app.logger.info("---End step2---")
