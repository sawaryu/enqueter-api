from time import time
from uuid import uuid4
from sqlalchemy import String, Integer, Column, ForeignKey, Boolean

from database import db

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