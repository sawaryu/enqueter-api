from datetime import datetime

from sqlalchemy import Integer, ForeignKey, DateTime

from database import db

point = db.Table('point',
                 db.Column('user_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False),
                 db.Column('point', Integer, nullable=False),
                 db.Column('created_at', DateTime, nullable=False, default=datetime.now()),
                 )

response = db.Table('response',
                    db.Column('user_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False),
                    db.Column('created_at', DateTime, nullable=False, default=datetime.now()),
                    )
