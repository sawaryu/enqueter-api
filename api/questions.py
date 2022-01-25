from datetime import timedelta, datetime
from flask import request

from flask_restx import Namespace, fields, Resource
from flask_jwt_extended import jwt_required, current_user
from sqlalchemy import func

from api.model.enums import AnswerResultPoint
from api.model.models import Question, answer, Notification
from api.model.user import User
from database import db

question_ns = Namespace('/questions')

questionCreate = question_ns.model('QuestionCreate', {
    'content': fields.String(required=True, max_length=140, pattern=r'\S'),
})

questionDelete = question_ns.model('QuestionDelete', {
    'question_id': fields.Integer(required=True)
})

bookmarkCreateOrDelete = question_ns.model('BookmarkCreate', {
    'question_id': fields.Integer(required=True)
})

answerCreateModel = question_ns.model('BookmarkCreate', {
    'question_id': fields.Integer(required=True),
    'is_yes': fields.Boolean(required=True)
})


@question_ns.route('')
class QuestionIndex(Resource):
    @question_ns.doc(
        security='jwt_auth',
        description='Get all questions.'
    )
    @jwt_required()
    def get(self):
        objects = db.session.query(Question, User) \
            .join(User) \
            .order_by(Question.created_at.desc()) \
            .all()

        return list(map(lambda x: x.Question.to_dict() | {
            "user": x.User.to_dict()
        }, objects))

    @question_ns.doc(
        security='jwt_auth',
        body=questionCreate,
        description='Create a Question.'
    )
    @jwt_required()
    def post(self):
        if current_user.questions and (current_user.questions[0].created_at + timedelta(minutes=3)) > datetime.now():
            return {
                       "status": 400,
                       "message": "Not yet passed 3 minutes from latest question you created."
                   }, 400

        content = request.json['content']

        question = Question(
            user_id=current_user.id,
            content=content
        )

        db.session.add(question)
        db.session.commit()
        db.session.refresh(question)

        return {"status": 201, "message": "the question created.", "data": question.to_dict()}, 201

    @question_ns.doc(
        security='jwt_auth',
        body=questionDelete,
        description='Delete a question (* Only the owner user can take operation).'
    )
    @jwt_required()
    def delete(self):
        question_id = request.json['question_id']
        question = Question.query.filter_by(id=question_id).first()
        if not question or not question.user_id == current_user.id:
            return {"status": 401, "message": "Unauthorized"}, 401

        # delete notification
        Notification.query.filter_by(question_id=question_id).delete()

        db.session.delete(question)
        db.session.commit()

        return {"status": 200, "message": "The question was successfully deleted."}, 200


# TODO: improve the logics
@question_ns.route('/answer')
class QuestionsAnswer(Resource):
    @question_ns.doc(
        security='jwt_auth',
        description='Create a Answer to the Question got by question_id.(not answer to closed question.)',
        body=answerCreateModel
    )
    @jwt_required()
    def post(self):
        params = request.json
        question = Question.query.filter_by(id=params["question_id"]).first()
        if not question:
            return {"status": 404, "message": "Not Found"}, 404

        if not question.is_open():
            return {"status": 409, "message": "The questions had been closed already."}, 409

        if question.user_id == current_user.id or current_user.is_answered_question(question):
            return {"status": 400, "message": "Bad request"}, 400

        # attention that below method is the 'Dynamic'. So it should be got by the 'all()' method finally.
        if not question.answered_users.all():
            result = AnswerResultPoint.FIRST.value

        else:
            yes_count = len(db.session.query(answer)
                            .filter(answer.c.question_id == params["question_id"])
                            .filter(answer.c.is_yes == 1)
                            .all())

            no_count = len(db.session.query(answer)
                           .filter(answer.c.question_id == params["question_id"])
                           .filter(answer.c.is_yes == 0)
                           .all())
            if request.json["is_yes"]:
                yes_count += 1
                if yes_count == no_count:
                    result = AnswerResultPoint.EVEN.value
                elif yes_count > no_count:
                    result = AnswerResultPoint.RIGHT.value
                else:
                    result = AnswerResultPoint.WRONG.value
            else:
                no_count += 1
                if yes_count == no_count:
                    result = AnswerResultPoint.EVEN.value
                elif no_count > yes_count:
                    result = AnswerResultPoint.RIGHT.value
                else:
                    result = AnswerResultPoint.WRONG.value

        # create answer
        insert_answer = answer.insert().values(
            user_id=current_user.id,
            question_id=question.id,
            is_yes=params["is_yes"],
            result_point=result
        )
        db.session.execute(insert_answer)

        # create notifications
        current_user.create_answer_notification(question)

        # commit
        db.session.commit()

        return {"result": result}


# common question info
@question_ns.route('/<int:question_id>')
class QuestionShow(Resource):
    @question_ns.doc(
        security='jwt_auth',
        description='Get a questions by id.'
    )
    @jwt_required()
    def get(self, question_id):
        question = Question.query.filter_by(id=question_id).first()
        if not question:
            return {"status": 404, "message": "Not Found"}, 404

        return question.to_dict() | {
            "user": question.user.to_dict()
        }


@question_ns.route('/<int:question_id>/owner')
class QuestionOwner(Resource):
    @question_ns.doc(
        security='jwt_auth',
        description='Get the questions`s details information. (* only be accessed by the owner and answered users.)'
                    '(* if closed, all the user can access.)'
    )
    @jwt_required()
    def get(self, question_id):
        question = Question.query.filter_by(id=question_id).first()
        if not question:
            return {"status": 404, "message": "Not Found"}, 404
        elif question.is_open() and not question.user_id == current_user.id \
                and not current_user.is_answered_question(question):
            return {"status": 403, "message": "Forbidden"}, 403

        # pie_chart_data
        pie_chart_data = [
            len(db.session.query(answer)
                .filter(answer.c.question_id == question_id)
                .filter(answer.c.is_yes == 0)
                .all()),
            len(db.session.query(answer)
                .filter(answer.c.question_id == question_id)
                .filter(answer.c.is_yes == 1)
                .all())
        ]

        # answered users
        objects = db.session.query(User, answer) \
            .join(answer, answer.c.user_id == User.id) \
            .filter(answer.c.question_id == question_id) \
            .order_by(answer.c.created_at.desc()) \
            .all()
        users = list(map(lambda x: x.User.to_dict() | {
            "is_yes": x[3]
        }, objects))

        return {"pie_chart_data": pie_chart_data, "users": users}


@question_ns.route('/next')
class QuestionNext(Resource):
    @question_ns.doc(
        security='jwt_auth',
        description='Get the next question_id at random '
                    'that is using for the next question page.(* only unanswered and not owned question).'
    )
    @jwt_required()
    def get(self):
        answered_question_ids = list(map(lambda x: x.id, current_user.answered_questions))
        owner_question_ids = list(map(lambda x: x.id, current_user.questions))

        question = Question.query \
            .filter(Question.closed_at > datetime.now()) \
            .filter(Question.id.notin_(answered_question_ids + owner_question_ids)) \
            .order_by(func.rand()) \
            .limit(1) \
            .first()
        if not question:
            return {"status": 200, "message": "none", "data": None}
        return {"status": 200, "message": "ok", "data": question.id}


@question_ns.route('/timeline')
class QuestionTimeline(Resource):
    @question_ns.doc(
        security='jwt_auth',
        description='Get a questions of timeline (related with following users.)'
    )
    @jwt_required()
    def get(self):
        following_ids = [current_user.id]
        for user in current_user.followings:
            following_ids.append(user.id)

        objects = db.session.query(Question, User) \
            .filter(Question.user_id.in_(following_ids)) \
            .join(User) \
            .order_by(Question.created_at.desc()) \
            .all()

        return list(map(lambda x: x.Question.to_dict() | {
            "user": x.User.to_dict()
        }, objects))


@question_ns.route('/bookmark')
class QuestionBookmark(Resource):
    @question_ns.doc(
        security='jwt_auth',
        description='Get bookmarked questions. (current_user)'
    )
    @jwt_required()
    def get(self):
        objects = current_user.bookmarks.join(User).all()

        return list(map(lambda x: x.Question.to_dict() | {
            "user": x.User.to_dict()
        }, objects))

    @question_ns.doc(
        security='jwt_auth',
        description='Create the bookmark of question.',
        body=bookmarkCreateOrDelete
    )
    @jwt_required()
    def post(self):
        question_id = request.json["question_id"]

        question = Question.query.filter_by(id=question_id).first()
        if not question:
            return {"status": 400, "message": "bad request"}, 400

        current_user.bookmark_question(question)
        db.session.commit()

        return {"status": 201, "message": "successfully bookmarked the question."}

    @question_ns.doc(
        security='jwt_auth',
        description='Delete the bookmark of question.',
        body=bookmarkCreateOrDelete
    )
    @jwt_required()
    def delete(self):
        question_id = request.json["question_id"]

        question = Question.query.filter_by(id=question_id).first()
        if not question:
            return {"status": 400, "message": "bad request"}, 400

        current_user.un_bookmark_question(question)
        db.session.commit()

        return {"status": 200, "message": "successfully un bookmarked the question."}
