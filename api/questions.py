from datetime import timedelta, datetime
from time import time

from flask import request

from flask_restx import Namespace, fields, Resource
from flask_jwt_extended import jwt_required, current_user
from sqlalchemy import func

from api.model.aggregate import point
from api.model.enum.enums import AnswerResultPoint, QuestionOption
from api.model.others import Notification
from api.model.question import Question, answer
from api.model.user import User
from database import db

question_ns = Namespace('/questions')

questionCreate = question_ns.model('QuestionCreate', {
    'content': fields.String(required=True, max_length=140, pattern=r'\S'),
    'option_first': fields.String(required=True, max_length=15, pattern=r'\S'),
    'option_second': fields.String(required=True, max_length=15, pattern=r'\S')
})

questionDelete = question_ns.model('QuestionDelete', {
    'question_id': fields.Integer(required=True)
})

bookmarkCreateOrDelete = question_ns.model('BookmarkCreate', {
    'question_id': fields.Integer(required=True)
})

answerCreateModel = question_ns.model('BookmarkCreate', {
    'question_id': fields.Integer(required=True),
    'option': fields.String(required=True, enum=QuestionOption.get_value_list())
})


# TODO
@question_ns.route('')
class QuestionIndex(Resource):
    @question_ns.doc(
        security='jwt_auth',
        description='Get all questions.',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self):
        page = int(request.args.get('page'))
        if not page:
            return {"message": "Bad Request."}, 400

        base_query = db.session.query(Question, User) \
            .join(User) \
            .order_by(Question.id.desc()) \
            .paginate(page=page, per_page=15, error_out=False)

        # get pages and questions.
        total_pages = base_query.pages
        objects = base_query.items

        questions = list(map(lambda x: x.Question.to_dict() | {
            "user": x.User.to_dict()
        }, objects))

        return {"data": {
            "questions": questions,
            "total_pages": total_pages
        }}, 200

    @question_ns.doc(
        security='jwt_auth',
        body=questionCreate,
        description='Create a Question.'
    )
    @jwt_required()
    def post(self):
        latest_question: Question = current_user.questions.first()
        if latest_question and (latest_question.created_at + timedelta(minutes=3)) > datetime.now():
            return {
                       "status": 400,
                       "message": "Not yet passed 3 minutes from latest question you created."
                   }, 400

        question = Question(
            user_id=current_user.id,
            content=request.json['content'],
            option_first=request.json['option_first'],
            option_second=request.json['option_second']
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
        params: dict = request.json
        question: Question = Question.query.filter_by(id=params["question_id"]).first()
        if not question:
            return {"status": 404, "message": "Not Found"}, 404
        if not question.is_open:
            return {"status": 409, "message": "The questions had been closed already."}, 409
        if question.user_id == current_user.id or current_user.is_answered_question(question):
            return {"status": 400, "message": "Bad request"}, 400

        # attention that below method is the 'Dynamic'. So it should be got by the 'all()' method finally.
        if not question.answered_users.all():
            result_point: int = AnswerResultPoint.FIRST.value

        else:
            first_count: int = len(db.session.query(answer)
                                   .filter(answer.c.question_id == params["question_id"])
                                   .filter(answer.c.option == QuestionOption.first.value)
                                   .all())

            second_count: int = len(db.session.query(answer)
                                    .filter(answer.c.question_id == params["question_id"])
                                    .filter(answer.c.option == QuestionOption.second.value)
                                    .all())
            if params["option"] == QuestionOption.first.value:
                first_count += 1
                if first_count == second_count:
                    result_point = AnswerResultPoint.EVEN.value
                elif first_count > second_count:
                    result_point = AnswerResultPoint.RIGHT.value
                else:
                    result_point = AnswerResultPoint.WRONG.value
            else:
                second_count += 1
                if first_count == second_count:
                    result_point = AnswerResultPoint.EVEN.value
                elif second_count > first_count:
                    result_point = AnswerResultPoint.RIGHT.value
                else:
                    result_point = AnswerResultPoint.WRONG.value

        # create answer
        insert_answer = answer.insert().values(
            user_id=current_user.id,
            question_id=question.id,
            option=params["option"],
        )
        db.session.execute(insert_answer)

        # create point
        insert_point = point.insert().values(
            user_id=current_user.id,
            point=result_point
        )
        db.session.execute(insert_point)

        # create notifications
        current_user.create_answer_notification(question)

        # commit
        db.session.commit()

        return result_point


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
        elif question.is_open and not question.user_id == current_user.id \
                and not current_user.is_answered_question(question):
            return {"status": 403, "message": "Forbidden"}, 403

        # Aggregate each options count.
        first_count: int = len(db.session.query(answer)
                               .filter(answer.c.question_id == question_id)
                               .filter(answer.c.option == QuestionOption.first.value)
                               .all())

        second_count: int = len(db.session.query(answer)
                                .filter(answer.c.question_id == question_id)
                                .filter(answer.c.option == QuestionOption.second.value)
                                .all())

        count_data = [first_count, second_count]

        # Get answered users and their options.
        objects = db.session.query(User, answer.c.option.label("option")) \
            .join(answer, answer.c.user_id == User.id) \
            .filter(answer.c.question_id == question_id) \
            .order_by(answer.c.created_at.desc()) \
            .all()

        users = list(map(lambda x: x.User.to_dict() | {
            "option": x.option
        }, objects))

        return {"count_data": count_data, "users": users}, 200


@question_ns.route('/next')
class QuestionNext(Resource):
    @question_ns.doc(
        security='jwt_auth',
        description='Get the next question_id that is answerable at random '
                    'that is using for the next question page.(* only unanswered and not owned question).'
    )
    @jwt_required()
    def get(self):
        answered_question_ids = list(map(lambda x: x.id, current_user.answered_questions))
        owner_question_ids = list(map(lambda x: x.id, current_user.questions))

        question = Question.query \
            .filter(Question.closed_at > time()) \
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
        description='Get a questions of timeline (related with following users.)',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self):
        page = int(request.args.get("page"))

        following_ids = [current_user.id]
        for user in current_user.followings:
            following_ids.append(user.id)

        objects = db.session.query(Question, User) \
            .filter(Question.user_id.in_(following_ids)) \
            .join(User) \
            .order_by(Question.id.desc()) \
            .paginate(page=page, per_page=15, error_out=False) \
            .items

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
