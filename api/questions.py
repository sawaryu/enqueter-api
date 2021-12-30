from datetime import timedelta, datetime
from flask import request

from flask_restx import Namespace, fields, Resource
from flask_jwt_extended import jwt_required, current_user

from api.model.models import Question, db

question_ns = Namespace('/questions')

questionCreate = question_ns.model('QuestionCreate', {
    'content': fields.String(required=True, max_length=255, pattern=r'\S'),
})


@question_ns.route('')
class QuestionIndex(Resource):
    @question_ns.doc(
        security='jwt_auth',
        description='Get all questions.'
    )
    @jwt_required()
    def get(self):
        questions = Question.query.all()
        return list(map(lambda x: x.to_dict(), questions))

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
                       "message": "Not yet passed 3 minutes from latest question you created"
                   }, 400

        content = request.json['content']

        question = Question(
            user_id=current_user.id,
            contetn=content
        )

        db.session.add(question)
        db.session.commit()

        return {"status": 201, "message": "the question created."}, 201



