from datetime import datetime
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
                  UniqueConstraint('user_id', 'question_id', name='answer_unique_key')
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

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "content": self.content,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "is_open": self.is_open()
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
