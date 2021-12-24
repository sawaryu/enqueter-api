from datetime import timedelta, datetime

from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource, fields

from api.model.models import Report, db, ReportCategory, ReportTag, ReportTagCategory

report_ns = Namespace('/reports')

reportUserCreate = report_ns.model('ReportUserCreate', {
    'target_id': fields.String(required=True, pattern=r'[0-9]'),
    'from_id': fields.Integer(required=True, pattern=r'[0-9]'),
    'content': fields.String(required=True, max_length=200),
    'category': fields.String(required=True, enum=ReportCategory.get_value_list())
})

reportTagCreate = report_ns.model('ReportTagCreate', {
    'target_id': fields.String(required=True, pattern=r'[0-9]'),
    'from_id': fields.Integer(required=True, pattern=r'[0-9]'),
    'content': fields.String(required=True, max_length=200),
    'category': fields.String(required=True, enum=ReportTagCategory.get_value_list())
})


# User
@report_ns.route('')
class ReportsIndex(Resource):
    # create
    @report_ns.doc(
        security='jwt_auth',
        description='ユーザー報告の作成',
        body=reportUserCreate
    )
    @jwt_required()
    def post(self):
        target_id = request.json['target_id']
        from_id = request.json['from_id']
        content = request.json['content']
        category = request.json['category']

        already_report = Report.query.filter_by(from_id=from_id).filter_by(target_id=target_id).first()
        if already_report and (already_report.created_at + timedelta(days=1)) > datetime.now():
            return {
                       "status": 400,
                       "message": "このユーザーを報告してからまだ24時間が経過していません。"
                   }, 400

        new_report = Report(
            from_id=from_id,
            target_id=target_id,
            content=content,
            category=category
        )

        db.session.add(new_report)
        db.session.commit()

        return {"status": 200, "message": "successfully reported"}


# Tag
@report_ns.route('/tag')
class ReportsTagIndex(Resource):
    # create
    @report_ns.doc(
        security='jwt_auth',
        description='タグ報告の作成',
        body=reportTagCreate
    )
    @jwt_required()
    def post(self):
        target_id = request.json['target_id']
        from_id = request.json['from_id']
        content = request.json['content']
        category = request.json['category']

        already_report = ReportTag.query.filter_by(from_id=from_id).filter_by(target_id=target_id).first()
        if already_report and (already_report.created_at + timedelta(days=1)) > datetime.now():
            return {
                       "status": 400,
                       "message": "このタグを報告してからまだ24時間が経過していません。"
                   }, 400

        new_report = ReportTag(
            from_id=from_id,
            target_id=target_id,
            content=content,
            category=category
        )

        db.session.add(new_report)
        db.session.commit()

        return {"status": 200, "message": "successfully reported"}
