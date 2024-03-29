from datetime import datetime

from flask_jwt_extended import current_user
from sqlalchemy import String, Integer, Column, DateTime, ForeignKey, UniqueConstraint, Enum

from api.model.enum.enums import QuestionOption
from database import db

answer = db.Table('answer',
                  db.Column('user_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False),
                  db.Column('question_id', Integer, ForeignKey('question.id', ondelete="CASCADE"), nullable=False),
                  db.Column('option', Enum(QuestionOption), nullable=False),
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
    """QuestionModel
    """
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    content = Column(String(140), nullable=False)
    option_first = Column(String(15), nullable=False)
    option_second = Column(String(15), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    def __init__(self, user_id: int, content: str, option_first: str, option_second: str, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.content = content
        self.option_first = option_first
        self.option_second = option_second

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
            "option_first": self.option_first,
            "option_second": self.option_second,
            "created_at": str(self.created_at),
            "is_answered": self.is_answered,
            "answered_count": len(self.answered_users.all()),
            "is_bookmarked": self.is_bookmarked
        }

    @classmethod
    def find_by_id(cls, _id: int) -> "Question":
        return cls.query.filter_by(id=_id).first()

    def save_to_db(self) -> None:
        db.session.add(self)
        db.session.commit()

    def delete_from_db(self) -> None:
        db.session.delete(self)
        db.session.commit()

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

