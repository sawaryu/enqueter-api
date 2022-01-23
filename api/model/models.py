import os
from datetime import datetime
from time import time
from uuid import uuid4
from flask import Response, render_template
from flask_jwt_extended import current_user
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy import String, Integer, Column, DateTime, ForeignKey, UniqueConstraint, Boolean, Enum
from datetime import timedelta
from api.libs.mailgun import MailGun

from api.model.enums import UserRole, NotificationCategory

db = SQLAlchemy()
ma = Marshmallow()

relationship = db.Table('relationship',
                        db.Column('following_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False),
                        db.Column('followed_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False),
                        db.Column('created_at', DateTime, nullable=False, default=datetime.now()),
                        UniqueConstraint('following_id', 'followed_id', name='relationship_unique_key')
                        )

answer = db.Table('answer',
                  db.Column('user_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False),
                  db.Column('question_id', Integer, ForeignKey('question.id', ondelete="CASCADE"), nullable=False),
                  db.Column('is_yes', Boolean, nullable=False),
                  db.Column('result_point', Integer, nullable=False),
                  db.Column('created_at', DateTime, nullable=False, default=datetime.now()),
                  UniqueConstraint('user_id', 'question_id', name='answer_unique_key')
                  )

bookmark = db.Table('bookmark',
                    db.Column('user_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False),
                    db.Column('question_id', Integer, ForeignKey('question.id', ondelete="CASCADE"), nullable=False),
                    db.Column('created_at', DateTime, nullable=False, default=datetime.now()),
                    UniqueConstraint('user_id', 'question_id', name='bookmark_unique_key')
                    )


class TokenBlocklist(db.Model):
    id = Column(Integer, primary_key=True)
    jti = Column(String(36), nullable=False)
    created_at = Column(DateTime, nullable=False)


CONFIRMATION_EXPIRE_DELTA = 1800  # 30minutes


class UpdateConfirmation(db.Model):
    id = Column(String(50), primary_key=True)
    expire_at = Column(Integer, nullable=False)
    email = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"))

    def __init__(self, user_id: int, email: str, **kwargs):
        super().__init__(**kwargs)
        self.id = uuid4().hex
        self.user_id = user_id
        self.email = email
        self.expire_at = int(time()) + CONFIRMATION_EXPIRE_DELTA

    @classmethod
    def find_by_if(cls, _id) -> "UpdateConfirmation":
        return cls.query.filter_by(id=_id).first()

    @property
    def is_expired(self) -> bool:
        return time() > self.expire_at

    def force_to_expire(self) -> None:
        if not self.is_expired:
            self.expire_at = time()
            db.session.commit()


class Confirmation(db.Model):
    id = Column(String(50), primary_key=True)
    expire_at = Column(Integer, nullable=False)
    confirmed = Column(Boolean, nullable=False, default=False)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"))

    def __init__(self, user_id: int, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.id = uuid4().hex
        self.expire_at = int(time()) + CONFIRMATION_EXPIRE_DELTA
        self.confirmed = False

    @classmethod
    def find_by_if(cls, _id) -> "Confirmation":
        return cls.query.filter_by(id=_id).first()

    # treat as like property. not using bracket when calling.
    # "time()" is the UNIX elapsed time.
    @property
    def is_expired(self) -> bool:
        return time() > self.expire_at

    def force_to_expire(self) -> None:
        if not self.is_expired:
            self.expire_at = time()
            db.session.commit()


class User(db.Model):
    id = Column(Integer, primary_key=True)
    public_id = Column(String(15), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    name = Column(String(20), nullable=False)
    name_replaced = Column(String(20), nullable=False)
    introduce = Column(String(140), nullable=False, default="")
    avatar = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.user)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    confirmations = db.relationship('Confirmation', backref='user', lazy="dynamic", cascade='all, delete-orphan')
    update_confirmations = db.relationship('UpdateConfirmation', backref='user', lazy="dynamic",
                                           cascade='all, delete-orphan')

    questions = db.relationship('Question', order_by="desc(Question.created_at)", backref='user', lazy=True,
                                cascade='all, delete-orphan')

    answered_questions = db.relationship(
        'Question',
        order_by="desc(answer.c.created_at)",
        secondary=answer,
        back_populates="answered_users",
        lazy="dynamic"
    )

    bookmarks = db.relationship(
        'Question',
        order_by="desc(bookmark.c.created_at)",
        secondary=bookmark,
        backref="bookmarked_users",
        lazy="dynamic"
    )

    follower = db.relationship(
        'User', secondary='relationship',
        primaryjoin=(relationship.c.followed_id == id),
        secondaryjoin=(relationship.c.following_id == id),
        order_by="desc(relationship.c.created_at)",
        back_populates='followings')

    followings = db.relationship(
        'User', secondary='relationship',
        primaryjoin=(relationship.c.following_id == id),
        secondaryjoin=(relationship.c.followed_id == id),
        order_by="desc(relationship.c.created_at)",
        back_populates='follower')

    histories = db.relationship(
        'SearchHistory',
        primaryjoin='SearchHistory.user_id==User.id',
        order_by="desc(SearchHistory.created_at)", lazy=True, cascade='all, delete-orphan',
        back_populates='from_user'
    )

    histories_passive = db.relationship(
        'SearchHistory',
        primaryjoin='SearchHistory.target_id==User.id',
        order_by="desc(SearchHistory.created_at)", lazy=True, cascade='all, delete-orphan',
        back_populates='target_user'
    )

    passive_notifications = db.relationship(
        'Notification',
        primaryjoin='Notification.passive_id==User.id',
        order_by="desc(Notification.created_at)", lazy=True, cascade='all, delete-orphan',
        back_populates='passive_user'
    )

    active_notifications = db.relationship(
        'Notification',
        primaryjoin='Notification.active_id==User.id',
        order_by="desc(Notification.created_at)", lazy=True, cascade='all, delete-orphan',
        back_populates='active_user'
    )

    # json
    def to_dict(self):
        return {
            "id": self.id,
            "public_id": self.public_id,
            "email": self.email,
            "name": self.name,
            "introduce": self.introduce,
            "avatar": self.avatar,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "is_following": True if current_user.is_following(self) else False,
            "role": self.role
        }

    @property
    def most_recent_confirmation(self) -> Confirmation:
        # Because of setting dynamic to "confirmations", it can be to take sequence of querying.
        return self.confirmations.order_by(Confirmation.expire_at.desc()).first()

    def send_confirmation_email(self) -> Response:
        # ex: https://127.0.0.1:5000/ > https://127.0.0.1:5000
        # link = request.url_root[0:-1] + f"/api/v1/auth/{self.most_recent_confirmation.id}/confirm"
        link = os.getenv("FRONT_WELCOME_URL") + f"?=confirm={self.most_recent_confirmation.id}"
        subject = "Registration confirmation"
        # for medias not compatible with html.
        text = f"Hi,{self.name}. Please click the link to confirm your account {link}"
        html = render_template("confirm.html", name=self.name, link=link)
        return MailGun.send_email([self.email], subject, text, html)

    @property
    def most_recent_update_confirmation(self) -> UpdateConfirmation:
        return self.update_confirmations.order_by(UpdateConfirmation.expire_at.desc()).first()

    def send_update_confirmation_email(self) -> Response:
        update_confirmation = self.most_recent_update_confirmation
        subject = "Update E-mail."
        token = update_confirmation.id
        text = f"Hi,{self.name}. Please enter the token to Enqueter for confirming the new E-mail. token: {token}"
        html = render_template("confirm_update.html", name=self.name, token=token)
        return MailGun.send_email([update_confirmation.email], subject, text, html)

    # relationship
    def follow(self, user):
        if not self.is_following(user) and not self.id == user.id:
            self.followings.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followings.remove(user)

    def is_following(self, user):
        return list(filter(lambda x: x.id == user.id, self.followings))

    # is already answered
    def is_answered_question(self, question):
        return list(filter(lambda x: x.id == question.id, self.answered_questions))

    # bookmark
    def bookmark_question(self, question):
        if not self.is_bookmark_question(question):
            self.bookmarks.append(question)

    def un_bookmark_question(self, question):
        if self.is_bookmark_question(question):
            self.bookmarks.remove(question)

    def is_bookmark_question(self, question):
        return list(filter(lambda x: x.id == question.id, self.bookmarks))

    # notification
    def create_follow_notification(self, user):
        if not self.is_same_notification(user.id, NotificationCategory.follow) and not self.id == user.id:
            db.session.add(Notification(
                passive_id=user.id,
                active_id=self.id,
                category=NotificationCategory.follow,
            ))

    def create_answer_notification(self, question):
        if not self.is_same_notification(question.user_id, NotificationCategory.answer, question_id=question.id) \
                and not self.id == question.user_id:
            db.session.add(Notification(
                passive_id=question.user_id,
                active_id=self.id,
                category=NotificationCategory.answer,
                question_id=question.id
            ))

    def is_same_notification(self, user_id, category, question_id=None):
        # in case of 'follow'
        if category == NotificationCategory.follow:
            return list(
                filter(lambda x: x.passive_id == user_id and x.category == category, self.active_notifications))
        # in case of 'answer'
        elif category == NotificationCategory.answer and question_id:
            return list(
                filter(
                    lambda x: x.passive_id == user_id and x.category == category and x.question_id == question_id,
                    self.active_notifications))


class Question(db.Model):
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    content = Column(String(140), nullable=False)
    closed_at = Column(DateTime, nullable=False, default=(datetime.now() + timedelta(weeks=1)))
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    answered_users = db.relationship(
        'User',
        order_by="desc(answer.c.created_at)",
        secondary=answer,
        back_populates="answered_questions",
        lazy="dynamic"
    )

    # if the question has been created at before more than a week, it is treated as 'closed' question.
    def is_open(self):
        return datetime.now() < self.closed_at

    # whether current_user bookmarked the question.
    def is_bookmarked(self):
        if current_user.is_bookmark_question(self):
            return True
        else:
            return False

    # whether current_user answered the question.
    def is_answered(self):
        if current_user.is_answered_question(self):
            return True
        else:
            return False

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "content": self.content,
            "closed_at": str(self.closed_at),
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "is_open": self.is_open(),
            "is_answered": self.is_answered(),
            "is_bookmarked": self.is_bookmarked()
        }


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
