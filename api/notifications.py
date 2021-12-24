from flask import jsonify
from flask_jwt_extended import jwt_required, current_user
from flask_restx import Namespace, Resource

from api.model.models import db, User, Notification

notification_ns = Namespace('/notifications')


@notification_ns.route('')
class NotificationGet(Resource):
    @notification_ns.doc(
        security='jwt_auth',
        doc="get all my notifications."
    )
    @jwt_required()
    def get(self):
        notifications = []
        for notification in current_user.passive_notifications:
            active_user = User.query.filter_by(id=notification.active_id).first()
            if active_user:
                notifications.append(
                    notification.to_dict() | {
                        "user": active_user.to_dict()
                    }
                )

        return jsonify(notifications)

    @notification_ns.doc(
        security='jwt_auth',
        doc="delete all my notifications."
    )
    @jwt_required()
    def delete(self):
        Notification.query.filter_by(passive_id=current_user.id).delete()
        db.session.commit()
        return dict(status=200, message="successfully deleted")

    @notification_ns.doc(
        security='jwt_auth',
        doc="change statuses of my notifications to watched"
    )
    @jwt_required()
    def put(self):
        for notification in current_user.passive_notifications:
            notification.watched = True
        db.session.commit()
        return dict(status=200, message="successfully changed status to 'watched'")
