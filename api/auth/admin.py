from flask_jwt_extended import jwt_required, current_user
from flask_restx import Resource, Namespace, fields
from flask import request
from sqlalchemy.orm import aliased
from api.model.models import UserRole, db, User, Report, ReportTag, Tag

"""
*For Admin
"""

admin_ns = Namespace("/admin", description="only for admin user")

adminReportsUser = admin_ns.model('AdminReportsUser', {
    'ids': fields.List(fields.Integer(required=True), required=True)
})

adminReportsTag = admin_ns.model('AdminReportsTag', {
    'ids': fields.List(fields.Integer(required=True), required=True)
})


# User #
@admin_ns.route('/reports')
class ReportsIndex(Resource):
    # index
    @admin_ns.doc(
        security='jwt_auth',
        description='list of user reports'
    )
    @jwt_required()
    def get(self):
        if not current_user.role == UserRole.admin:
            return {"status": 403, "message": "Forbidden"}, 403

        from_user = aliased(User)

        objects = db.session.query(Report, User, from_user)\
            .join(User, User.id == Report.target_id)\
            .join(from_user, from_user.id == Report.from_id)\
            .order_by(Report.id.desc())\
            .all()

        # (<Report 1>, <User 8>, <User 1>) > xの中身
        return list(map(lambda x: x.Report.to_dict() | {"user": x.User.to_dict(),
                                                        "from_user": x[2].to_dict()},
                        objects))

    # delete
    @admin_ns.doc(
        security='jwt_auth',
        description='チェックボックスにて選択中の報告を全て削除する。',
        body=adminReportsUser
    )
    @jwt_required()
    def post(self):
        if not current_user.role == UserRole.admin:
            return {"status": 403, "message": "Forbidden"}, 403

        ids = request.json["ids"]

        if len(ids):
            Report.query.filter(Report.id.in_(ids)).delete()
            db.session.commit()

        return {"status": 200, "message": "ok"}


@admin_ns.route('/reports/mark')
class ReportsIndexMark(Resource):

    @admin_ns.doc(
        security='jwt_auth',
        description='チェック済みの報告を全てマークする(マーク済みの場合はtoggleする)',
        body=adminReportsUser
    )
    @jwt_required()
    def post(self):
        if not current_user.role == UserRole.admin:
            return {"status": 403, "message": "Forbidden"}, 403

        ids = request.json["ids"]

        if len(ids):
            reports = Report.query.filter(Report.id.in_(ids)).all()
            for r in reports:
                # toggle
                r.marked = not r.marked
            db.session.commit()

        return {"status": 200, "message": "ok"}


# Tag #
@admin_ns.route('/reports/tag')
class ReportsTagIndex(Resource):
    # index
    @admin_ns.doc(
        security='jwt_auth',
        description='報告タグの一覧(※管理者専用)'
    )
    @jwt_required()
    def get(self):
        if not current_user.role == UserRole.admin:
            return {"status": 403, "message": "Forbidden"}, 403

        objects = db.session.query(ReportTag, Tag, User) \
            .join(Tag, Tag.id == ReportTag.target_id).order_by(ReportTag.id.desc()) \
            .join(User, User.id == ReportTag.from_id)\
            .order_by(ReportTag.id.desc())\
            .all()

        return list(map(lambda x: x.ReportTag.to_dict() | {"tag": x.Tag.to_dict(),
                                                           "from_user": x.User.to_dict()},
                        objects))

    # delete
    @admin_ns.doc(
        security='jwt_auth',
        description='チェックボックスにて選択中の報告を全て削除する。',
        body=adminReportsTag
    )
    @jwt_required()
    def post(self):
        if not current_user.role == UserRole.admin:
            return {"status": 403, "message": "Forbidden"}, 403

        ids = request.json["ids"]

        if len(ids):
            ReportTag.query.filter(ReportTag.id.in_(ids)).delete()
            db.session.commit()

        return {"status": 200, "message": "ok"}


@admin_ns.route('/reports/tag/mark')
class ReportsTagIndexMark(Resource):
    # index
    @admin_ns.doc(
        security='jwt_auth',
        description='チェック済みの報告を全てマークする(マーク済みの場合はtoggleする)',
        body=adminReportsTag
    )
    @jwt_required()
    def post(self):
        if not current_user.role == UserRole.admin:
            return {"status": 403, "message": "Forbidden"}, 403

        ids = request.json["ids"]

        if len(ids):
            reports = ReportTag.query.filter(ReportTag.id.in_(ids)).all()
            for r in reports:
                # toggle
                r.marked = not r.marked
            db.session.commit()

        return {"status": 200, "message": "ok"}


@admin_ns.route('/users/<int:user_id>')
class ReportsUsersShow(Resource):
    # delete
    @admin_ns.doc(
        security='jwt_auth',
        description='対象のユーザーを削除する。(それに伴い対象の報告も全て削除する。)'
    )
    @jwt_required()
    def delete(self, user_id):
        if not current_user.role == UserRole.admin:
            return {"status": 403, "message": "Forbidden"}, 403

        User.query.filter_by(id=user_id).delete()
        db.session.commit()

        return {"status": 200, "message": "ok"}


@admin_ns.route('/tags/<int:tag_id>')
class ReportsUsersShow(Resource):
    # delete
    @admin_ns.doc(
        security='jwt_auth',
        description='対象のタグを削除する。'
    )
    @jwt_required()
    def delete(self, tag_id):
        if not current_user.role == UserRole.admin:
            return {"status": 403, "message": "Forbidden"}, 403

        Tag.query.filter_by(id=tag_id).delete()
        db.session.commit()

        return {"status": 200, "message": "ok"}
