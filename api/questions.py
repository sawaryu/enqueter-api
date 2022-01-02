from datetime import timedelta, datetime
from flask import request

from flask_restx import Namespace, fields, Resource
from flask_jwt_extended import jwt_required, current_user

from api.model.models import Question, db, User

question_ns = Namespace('/questions')

questionCreate = question_ns.model('QuestionCreate', {
    'content': fields.String(required=True, max_length=255, pattern=r'\S'),
})

bookmarkCreateOrDelete = question_ns.model('BookmarkCreate', {
    'question_id': fields.Integer(required=True)
})


@question_ns.route('')
class QuestionIndex(Resource):
    @question_ns.doc(
        security='jwt_auth',
        description='Get all questions.'
    )
    @jwt_required()
    def get(self):
        objects = db.session.query(Question, User)\
            .join(User)\
            .order_by(Question.created_at.desc())\
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