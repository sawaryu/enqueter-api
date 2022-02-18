from datetime import datetime
from sqlalchemy import String, Integer, Column, DateTime, ForeignKey, UniqueConstraint, Boolean, Enum

from api.model.enum.enums import NotificationCategory
from database import db

user_relationship = db.Table('user_relationship',
                             db.Column('following_id', Integer, ForeignKey('user.id', ondelete="CASCADE"),
                                       nullable=False),
                             db.Column('followed_id', Integer, ForeignKey('user.id', ondelete="CASCADE"),
                                       nullable=False),
                             db.Column('created_at', DateTime, nullable=False, default=datetime.now()),
                             UniqueConstraint('following_id', 'followed_id', name='user_relationship_unique_key')
                             )


class TokenBlocklist(db.Model):
    id = Column(Integer, primary_key=True)
    jti = Column(String(36), nullable=False)
    created_at = Column(DateTime, nullable=False)


class Notification(db.Model):
    id = Column(Integer, primary_key=True)
    passive_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"))
    active_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"))
    category = Column(Enum(NotificationCategory), nullable=False)
    question_id = Column(Integer, default=None)
    watched = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    passive_user = db.relationship("User", foreign_keys=[passive_id], back_populates='passive_notifications')
    active_user = db.relationship("User", foreign_keys=[active_id], back_populates='active_notifications')

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "passive_id": self.passive_id,
            "active_id": self.active_id,
            "question_id": self.question_id,
            "watched": self.watched,
            "created_at": str(self.created_at)
        }


class SearchHistory(db.Model):
    __table_args__ = (UniqueConstraint('user_id', 'target_id'), {})
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"))
    target_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"))
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    from_user = db.relationship("User", foreign_keys=[user_id], back_populates='histories')
    target_user = db.relationship("User", foreign_keys=[target_id], back_populates='histories_passive')

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "target_id": self.target_id,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at)
        }
