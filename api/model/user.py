import os
from datetime import datetime
from random import randrange
from time import time

from flask import Response, render_template
from flask_jwt_extended import current_user
from sqlalchemy import String, Integer, Column, DateTime, Enum
from werkzeug.security import generate_password_hash

from api.libs.mailgun import MailGun
from api.model.confirmation import Confirmation, UpdateConfirmation

from api.model.enum.enums import UserRole, NotificationCategory
from api.model.others import Notification, bookmark, answer, \
    user_relationship
from database import db

CONFIRMATION_EXPIRE_DELTA = 1800  # 30minutes


class User(db.Model):
    # basic
    id = Column(Integer, primary_key=True)
    username = Column(String(15), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.user)

    # password reset
    reset_digest = Column(String(255), default=None)
    reset_expired_at = Column(Integer, default=None)

    # others
    nickname = Column(String(20), nullable=False)
    nickname_replaced = Column(String(20), nullable=False)
    introduce = Column(String(140), nullable=False, default="")
    avatar = Column(String(255), nullable=False, default=f"egg_{randrange(1, 11)}.png'")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def __init__(self, username: str, email: str, nickname: str, password: str, **kwargs):
        super().__init__(**kwargs)
        self.username = username
        self.email = email
        self.password = generate_password_hash(password, method='sha256')
        self.nickname = nickname
        self.nickname_replaced = nickname.replace(' ', '').replace('　', '')

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "nickname": self.nickname,
            "introduce": self.introduce,
            "avatar": self.avatar,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "is_following": True if current_user.is_following(self) else False,
            "role": self.role
        }

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
        'User', secondary='user_relationship',
        primaryjoin=(user_relationship.c.followed_id == id),
        secondaryjoin=(user_relationship.c.following_id == id),
        order_by="desc(user_relationship.c.created_at)",
        back_populates='followings')
    followings = db.relationship(
        'User', secondary='user_relationship',
        primaryjoin=(user_relationship.c.following_id == id),
        secondaryjoin=(user_relationship.c.followed_id == id),
        order_by="desc(user_relationship.c.created_at)",
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

    @classmethod
    def find_by_id(cls, _id: int) -> "User":
        return cls.query.filter_by(id=_id).first()

    @classmethod
    def find_by_email(cls, email: str) -> "User":
        return cls.query.filter_by(email=email).first()

    def save_to_db(self) -> None:
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self) -> None:
        db.session.delete(self)
        db.session.commit()

    @property
    def is_reset_expired(self) -> bool:
        return time() > self.reset_expired_at

    def create_reset_password_resource(self, token: str) -> None:
        self.reset_digest = generate_password_hash(token, method='sha256')
        self.reset_expired_at = int(time()) + CONFIRMATION_EXPIRE_DELTA
        db.session.commit()

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
        text = f"Hi,{self.nickname}. Please click the link to confirm your account {link}"
        html = render_template("confirm.html", name=self.nickname, link=link)
        return MailGun.send_email([self.email], subject, text, html)

    @property
    def most_recent_update_confirmation(self) -> UpdateConfirmation:
        return self.update_confirmations.order_by(UpdateConfirmation.expire_at.desc()).first()

    def send_update_confirmation_email(self) -> Response:
        update_confirmation = self.most_recent_update_confirmation
        subject = "Update E-mail."
        token = update_confirmation.id
        text = f"Hi,{self.nickname}. Please enter the token to Enqueter for confirming the new E-mail. token: {token}"
        html = render_template("confirm_update.html", name=self.nickname, token=token)
        return MailGun.send_email([update_confirmation.email], subject, text, html)

    # relationship
    def follow(self, user) -> None:
        if not self.is_following(user) and not self.id == user.id:
            self.followings.append(user)

    def unfollow(self, user) -> None:
        if self.is_following(user):
            self.followings.remove(user)

    def is_following(self, user) -> list:
        return list(filter(lambda x: x.id == user.id, self.followings))

    # is already answered
    def is_answered_question(self, question) -> list:
        return list(filter(lambda x: x.id == question.id, self.answered_questions))

    # bookmark
    def bookmark_question(self, question) -> None:
        if not self.is_bookmark_question(question):
            self.bookmarks.append(question)

    def un_bookmark_question(self, question) -> None:
        if self.is_bookmark_question(question):
            self.bookmarks.remove(question)

    def is_bookmark_question(self, question) -> list:
        return list(filter(lambda x: x.id == question.id, self.bookmarks))

    # notification
    def create_follow_notification(self, user) -> None:
        if not self.is_same_notification(user.id, NotificationCategory.follow) and not self.id == user.id:
            db.session.add(Notification(
                passive_id=user.id,
                active_id=self.id,
                category=NotificationCategory.follow,
            ))

    def create_answer_notification(self, question) -> None:
        if not self.is_same_notification(question.user_id, NotificationCategory.answer, question_id=question.id) \
                and not self.id == question.user_id:
            db.session.add(Notification(
                passive_id=question.user_id,
                active_id=self.id,
                category=NotificationCategory.answer,
                question_id=question.id
            ))

    def is_same_notification(self, user_id, category, question_id=None) -> list:
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
