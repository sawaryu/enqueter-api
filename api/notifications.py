from flask_jwt_extended import current_user, jwt_required
from flask_restx import Namespace, Resource
from api.model.models import User, Notification, db

notification_ns = Namespace('/notifications')


@notification_ns.route('')
class NotificationIndex(Resource):
    @notification_ns.doc(
        security='jwt_auth',
        doc="Get all my notifications."
    )
    @jwt_required()
    def get(self):
        objects = db.session.query(Notification, User) \
            .filter(Notification.passive_id == current_user.id) \
            .join(User, User.id == Notification.active_id) \
            .order_by(Notification.id.desc()) \
            .all()

        return list(map(lambda x: x.Notification.to_dict() | {
            "user": x.User.to_dict()
        }, objects))

    @notification_ns.doc(
        security='jwt_auth',
        doc="Delete all my notifications."
    )
    @jwt_required()
    def delete(self):
        Notification.query.filter_by(passive_id=current_user.id).delete()
        db.session.commit()
        return dict(status=200, message="successfully deleted")

    @notification_ns.doc(
        security='jwt_auth',
        doc="Change statuses of my notifications to watched"
    )
    @jwt_required()
    def put(self):
        for notification in current_user.passive_notifications:
            notification.watched = True
        db.session.commit()
        return dict(status=200, message="successfully changed status to 'watched'")
