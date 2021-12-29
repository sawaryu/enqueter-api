from flask_restx import Namespace, fields

question_ns = Namespace('/questions')

questionCreate = question_ns.model('QuestionCreate', {
    'content': fields.String(required=True, max_length=255, pattern=r'\S'),
})
