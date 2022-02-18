from datetime import datetime
from time import time

from flask_jwt_extended import current_user
from sqlalchemy import String, Integer, Column, DateTime, ForeignKey, UniqueConstraint, Boolean
from database import db

answer = db.Table('answer',
                  db.Column('user_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False),
                  db.Column('question_id', Integer, ForeignKey('question.id', ondelete="CASCADE"), nullable=False),
                  db.Column('is_yes', Boolean, nullable=False),
                  db.Column('created_at', DateTime, nullable=False, default=datetime.now()),
                  UniqueConstraint('user_id', 'question_id', name='answer_unique_key')
                  )

bookmark = db.Table('bookmark',
                    db.Column('user_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False),
                    db.Column('question_id', Integer, ForeignKey('question.id', ondelete="CASCADE"), nullable=False),
                    db.Column('created_at', DateTime, nullable=False, default=datetime.now()),
                    UniqueConstraint('user_id', 'question_id', name='bookmark_unique_key')
                    )


class Question(db.Model):
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    content = Column(String(140), nullable=False)
    closed_at = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    def __init__(self, user_id: int, content: str, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.content = content
        self.closed_at = int(time()) + 604800  # 1 week

    answered_users = db.relationship(
        'User',
        order_by="desc(answer.c.created_at)",
        secondary=answer,
        back_populates="answered_questions",
        lazy="dynamic"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "content": self.content,
            "closed_at": str(self.closed_at),
            "created_at": str(self.created_at),
            "is_open": self.is_open,
            "is_answered": self.is_answered,
            "is_bookmarked": self.is_bookmarked
        }

    def save_to_db(self) -> None:
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self) -> None:
        db.session.delete(self)
        db.session.commit()

    # if the question has been created at before more than a week, it is treated as 'closed' question.
    @property
    def is_open(self) -> bool:
        return time() < self.closed_at

    # whether current_user bookmarked the question.
    @property
    def is_bookmarked(self) -> bool:
        if current_user.is_bookmark_question(self):
            return True
        else:
            return False

    # whether current_user answered the question.
    @property
    def is_answered(self) -> bool:
        if current_user.is_answered_question(self):
            return True
        else:
            return False
