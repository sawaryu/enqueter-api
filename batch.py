from datetime import timedelta, datetime

import click
from sqlalchemy import func

from api.model.others import answer
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
    # if not declare the "FLASK_APP=batch.py" below is needed.
    # with app.app_context():
    db.session.begin()
    try:
        # """Sequence"""
        # before_sequence_id: int = db.session.query(sequence.c.id).scalar()
        # if before_sequence_id is None:
        #     app.logger.error("The sequence record does not exist. Please check "
        #                      "your application had initialize 'seed' completely.")
        #     raise
        #
        # update_sequence = text("UPDATE sequence SET id=LAST_INSERT_ID(id+1);")
        # db.session.execute(update_sequence)
        # db.session.flush()
        #
        # sequence_id: int = db.session.execute(text("SELECT LAST_INSERT_ID();")).scalar()
        # app.logger.info(f'{message}, before_sequence: {before_sequence_id}, new_sequence: {sequence_id}')

        """Collect data"""
        results: list[dict] = []
        periods: list[dict] = [{"days": 365 * 100}, {"days": 30}, {"days": 7}]
        for (step, period) in enumerate(periods):

            # Because of "join", The user who have not answer any questions will not be contained to "entities".
            entities = db.session.query(User, func.sum(answer.c.result_point)) \
                .join(answer, answer.c.user_id == User.id) \
                .filter(answer.c.created_at > (datetime.now() - timedelta(**period))) \
                .group_by(User.id) \
                .order_by(func.sum(answer.c.result_point).desc()) \
                .order_by(User.id.desc()) \
                .all()

            for (index_rank, entity) in enumerate(entities):
                if step == 0:
                    temp_dict = {
                        "user_id": entity.User.id,
                        "total_rank": index_rank + 1,
                        "total_point": int(entity[1]),
                        "month_rank": None,
                        "month_point": None,
                        "week_rank": None,
                        "week_point": None
                    }
                    results.append(temp_dict)
                elif step == 1:
                    temp_dict = {
                        "month_rank": index_rank + 1,
                        "month_point": int(entity[1])
                    }
                    for (index, r) in enumerate(results):
                        if r["user_id"] == entity.User.id:
                            results[index] = results[index] | temp_dict
                            break
                elif step == 2:
                    temp_dict = {
                        "week_rank": index_rank + 1,
                        "week_point": int(entity[1])
                    }
                    for (index, r) in enumerate(results):
                        if r["user_id"] == entity.User.id:
                            results[index] = results[index] | temp_dict
                            break
        app.logger.info("Successfully collected data.")

        """Update or Create records"""
        for r in results:
            point_stats = PointStats.find_by_user_id(r["user_id"])

            # update
            if point_stats:
                point_stats.week_rank = r["week_rank"]
                point_stats.week_point = r["week_point"]
                point_stats.month_rank = r["month_rank"]
                point_stats.month_point = r["month_point"]
                point_stats.total_rank = r["total_rank"]
                point_stats.total_point = r["total_point"]

            # create
            else:
                point_stats = PointStats(**r)
                db.session.add(point_stats)
            db.session.flush()

        db.session.commit()
        app.logger.info("Successfully finished.")
    except:
        db.session.rollback()
        app.logger.error("Something fatal error happened. take rollback completely.")
        raise
    finally:
        db.session.close()
