from datetime import timedelta, datetime
from flask import request

from flask_restx import Namespace, fields, Resource
from flask_jwt_extended import jwt_required, current_user

from api.model.enums import AnswerResult
from api.model.models import Question, db, User, answer

question_ns = Namespace('/questions')

questionCreate = question_ns.model('QuestionCreate', {
    'content': fields.String(required=True, max_length=255, pattern=r'\S'),
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


# TODO: improve the logics
@question_ns.route('/answer')
class QuestionsAnswer(Resource):
    @question_ns.doc(
        security='jwt_auth',
        description='Create a Answer to the Question got by question_id.',
        body=answerCreateModel
    )
    @jwt_required()
    def post(self):
        params = request.json
        question = Question.query.filter_by(id=params["question_id"]).first()
        if not question or question.user_id == current_user.id or current_user.is_answered_question(question):
            return {"status": 400, "message": "bad request."}, 400

        result = None

        if not question.answered_users:
            result = AnswerResult.first

        else:
            yes_count = len(db.session.query(answer)
                            .filter(answer.c.question_id == params["question_id"])
                            .filter(answer.c.is_yes == True)
                            .all())

            no_count = len(db.session.query(answer)
                           .filter(answer.c.question_id == params["question_id"])
                           .filter(answer.c.is_yes == False)
                           .all())
            if request.json["is_yes"]:
                yes_count += 1
                if yes_count == no_count:
                    result = AnswerResult.even
                elif yes_count > no_count:
                    result = AnswerResult.right
                else:
                    result = AnswerResult.wrong
            else:
                no_count += 1
                if yes_count == no_count:
                    result = AnswerResult.even
                elif no_count > yes_count:
                    result = AnswerResult.right
                else:
                    result = AnswerResult.wrong

        insert_answer = answer.insert().values(
            user_id=current_user.id,
            question_id=question.id,
            is_yes=params["is_yes"],
            result=result
        )
        db.session.execute(insert_answer)
        db.session.commit()

        return {"message": result}


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


# only be accessed by the owner and answered users. todo
@question_ns.route('/<int:question_id>/owner')
class QuestionOwner(Resource):
    @question_ns.doc(
        security='jwt_auth',
        description='Get the questions`s details information. (* only be accessed by the owner and answered users.)'
    )
    @jwt_required()
    def get(self, question_id):
        question = Question.query.filter_by(id=question_id).first()
        if not question:
            return {"status": 404, "message": "Not Found"}, 404

        # pie_chart
        pie_chart_data = {"yes": 12, "no": 32}

        # line chart TODO
        line_chart_data = {}

        # users
        users = list(map(lambda x: x.to_dict(), question.answered_users))

        return {"pie_chart_data": pie_chart_data, "line_chart_data": line_chart_data, "users": users}


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
            .order_by(Question.id.desc()) \
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
