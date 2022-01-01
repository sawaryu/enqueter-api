from datetime import datetime

from flask_jwt_extended import current_user
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy import String, Integer, Column, DateTime, ForeignKey, UniqueConstraint, Boolean, Enum
from datetime import timedelta

from api.model.enums import UserRole

db = SQLAlchemy()
ma = Marshmallow()

relationship = db.Table('relationship',
                        db.Column('following_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False),
                        db.Column('followed_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False),
                        UniqueConstraint('following_id', 'followed_id', name='relationship_unique_key')
                        )

answer = db.Table('answer',
                  db.Column('user_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False),
                  db.Column('question_id', Integer, ForeignKey('question.id', ondelete="CASCADE"), nullable=False),
                  db.Column('is_yes', Boolean, nullable=False),
                  db.Column('is_collect', Boolean, nullable=False),
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


class User(db.Model):
    id = Column(Integer, primary_key=True)
    public_id = Column(String(15), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    name = Column(String(20), nullable=False)
    name_replaced = Column(String(20), nullable=False)
    introduce = Column(String(140), nullable=False, default="")
    avatar = Column(String(255), nullable=False)
    point = Column(Integer, nullable=False, default=0)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.user)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    questions = db.relationship('Question', order_by="desc(Question.created_at)", backref='user', lazy=True,
                                cascade='all, delete-orphan')

    answers = db.relationship(
        'Question',
        order_by="desc(answer.c.created_at)",
        secondary=answer,
        backref="answered_users",
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
        back_populates='followings')

    followings = db.relationship(
        'User', secondary='relationship',
        primaryjoin=(relationship.c.following_id == id),
        secondaryjoin=(relationship.c.followed_id == id),
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

    def to_dict(self):
        return {
            "id": self.id,
            "public_id": self.public_id,
            "name": self.name,
            "introduce": self.introduce,
            "avatar": self.avatar,
            "point": self.point,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "is_following": True if current_user.is_following(self) else False,
            "role": self.role
        }

    def follow(self, user):
        if not self.is_following(user) and not self.id == user.id:
            self.followings.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followings.remove(user)

    def is_following(self, user):
        return list(filter(lambda x: x.id == user.id, self.followings))

    def answer_question(self, question):
        if not self.is_answered_question(question):
            self.answers.append(question)

    def is_answered_question(self, question):
        return list(filter(lambda x: x.id == question.id, self.answers))

    def bookmark_question(self, question):
        if not self.is_bookmark_question(question):
            self.bookmarks.append(question)

    def un_bookmark_question(self, question):
        if self.is_bookmark_question(question):
            self.bookmarks.remove(question)

    def is_bookmark_question(self, question):
        return list(filter(lambda x: x.id == question.id, self.bookmarks))


class Question(db.Model):
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    content = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # if the question has been created at more than before a week, it is treated as closed question.
    def is_open(self):
        if (datetime.now() - self.created_at) > timedelta(days=7):
            return False
        else:
            return True

    # whether bookmarked by current user
    def is_bookmarked(self):
        if current_user.is_bookmark_question(self):
            return True
        else:
            return False

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "content": self.content,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "is_open": self.is_open(),
            "is_bookmarked": self.is_bookmarked()
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
