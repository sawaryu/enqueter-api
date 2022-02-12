from datetime import timedelta, datetime

import click
from sqlalchemy import func

from api.model.aggregate import point, response
from api.model.others import Question
from api.model.user import User, Stats
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
    db.session.begin()
    try:
        """
        TODO: delete non active users.
        """

        """
        Collect data
        """
        results: list[dict] = []
        users = User.query.all()
        for user in users:
            initial_dict = {
                "user_id": user.id,
                # rank
                "total_rank_point": None,
                "total_point": None,
                "month_rank_point": None,
                "month_point": None,
                "week_rank_point": None,
                "week_point": None,
                "total_rank_response": None,
                "total_response": None,
                "month_rank_response": None,
                "month_response": None,
                "week_rank_response": None,
                "week_response": None,

                # others
                "total_questions": 0,
                "week_questions": 0,
                "month_questions": 0,
                "total_answers": 0,
                "week_answers": 0,
                "month_answers": 0,
            }
            results.append(initial_dict)

        periods: list[dict] = [{"days": 365 * 100}, {"days": 30}, {"days": 7}]
        for (step, period) in enumerate(periods):
            """Point & Answer count"""
            point_entities = db.session.query(User, func.sum(point.c.point).label("points"),
                                              func.count(point.c.user_id).label("answers")) \
                .join(point, point.c.user_id == User.id) \
                .filter(point.c.created_at > (datetime.now() - timedelta(**period))) \
                .group_by(User.id) \
                .order_by(func.sum(point.c.point).desc()) \
                .order_by(User.id.desc()) \
                .all()

            for (index_rank, entity) in enumerate(point_entities):
                if step == 0:
                    temp_dict = {
                        "user_id": entity.User.id,
                        "total_rank_point": index_rank + 1,
                        "total_point": int(entity.points),
                        "total_answers": int(entity.answers),
                        "total_questions": len(entity.User.questions.all())
                    }
                    for (index, r) in enumerate(results):
                        if r["user_id"] == entity.User.id:
                            results[index] = results[index] | temp_dict
                            break
                elif step == 1:
                    temp_dict = {
                        "user_id": entity.User.id,
                        "month_rank_point": index_rank + 1,
                        "month_point": int(entity.points),
                        "month_answers": int(entity.answers),
                        "month_questions": len(
                            entity.User.questions.filter(
                                Question.created_at > (datetime.now() - timedelta(**period))).all())
                    }
                    for (index, r) in enumerate(results):
                        if r["user_id"] == entity.User.id:
                            results[index] = results[index] | temp_dict
                            break
                elif step == 2:
                    temp_dict = {
                        "user_id": entity.User.id,
                        "week_rank_point": index_rank + 1,
                        "week_point": int(entity.points),
                        "week_answers": int(entity.answers),
                        "week_questions": len(
                            entity.User.questions.filter(
                                Question.created_at > (datetime.now() - timedelta(**period))).all())
                    }
                    for (index, r) in enumerate(results):
                        if r["user_id"] == entity.User.id:
                            results[index] = results[index] | temp_dict
                            break
            """Responses"""
            response_entities = db.session.query(User, func.count(response.c.user_id).label("responses")) \
                .join(response, response.c.user_id == User.id) \
                .filter(response.c.created_at > (datetime.now() - timedelta(**period))) \
                .group_by(User.id) \
                .order_by(func.count(response.c.user_id).desc()) \
                .order_by(User.id.desc()) \
                .all()

            for (index_rank, entity) in enumerate(response_entities):
                if step == 0:
                    temp_dict = {
                        "user_id": entity.User.id,
                        "total_rank_response": index_rank + 1,
                        "total_response": int(entity.responses),
                    }
                    for (index, r) in enumerate(results):
                        if r["user_id"] == entity.User.id:
                            results[index] = results[index] | temp_dict
                            break
                elif step == 1:
                    temp_dict = {
                        "user_id": entity.User.id,
                        "month_rank_response": index_rank + 1,
                        "month_response": int(entity.responses),
                    }
                    for (index, r) in enumerate(results):
                        if r["user_id"] == entity.User.id:
                            results[index] = results[index] | temp_dict
                            break
                elif step == 2:
                    temp_dict = {
                        "user_id": entity.User.id,
                        "week_rank_response": index_rank + 1,
                        "week_response": int(entity.responses),
                    }
                    for (index, r) in enumerate(results):
                        if r["user_id"] == entity.User.id:
                            results[index] = results[index] | temp_dict
                            break
        app.logger.info("Successfully collected data.")

        """
        Update or Create records
        """
        for r in results:
            stats = Stats.find_by_user_id(r["user_id"])
            # update
            if stats:
                # point
                stats.total_rank_point = r["total_rank_point"]
                stats.total_point = r["total_point"]
                stats.month_rank_point = r["month_rank_point"]
                stats.month_point = r["month_point"]
                stats.week_rank_point = r["week_rank_point"]
                stats.week_point = r["week_point"]
                # response
                stats.total_rank_response = r["total_rank_response"]
                stats.total_response = r["total_response"]
                stats.month_rank_response = r["month_rank_response"]
                stats.month_response = r["month_response"]
                stats.week_rank_response = r["week_rank_response"]
                stats.week_response = r["week_response"]
                # other
                stats.total_answers = r["total_answers"]
                stats.month_answers = r["month_answers"]
                stats.week_answers = r["week_answers"]
                stats.total_questions = r["total_questions"]
                stats.month_questions = r["month_questions"]
                stats.week_questions = r["week_questions"]
            # create
            else:
                stats = Stats(**r)
                db.session.add(stats)
            db.session.flush()

        db.session.commit()
        app.logger.info("Successfully finished.")
    except:
        db.session.rollback()
        app.logger.error("Something fatal error happened. take rollback completely.")
        raise
    finally:
        db.session.close()
