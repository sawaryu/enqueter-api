from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy import String, Integer, Column, DateTime, ForeignKey, UniqueConstraint, Boolean, Enum

from api.model.enums import UserRole, TagCategory, ReportCategory, ReportTagCategory, NotificationCategory, PostColorId, \
    PostFontId

"""メモ:
・一度のクエリで必要な情報を全て取得するには生のクエリの記述が恐らく頻繁に必要になる（join等）
・設計方針としては基本的にmodelのボリュームを増やす、apiビジネスロジックのコード量を減らす。
・親テーブル削除後に子テーブルのレコードを削除するには、relationshipを定義後に(cascade='all, delete-orphan')の設定が必要
・マッピングテーブルrecは親テーブルrecが削除された場合、特に設定がなくとも削除される。 
・backref,back_populatesの違い
(1)backrefを使用した場合
双方向のリレーションを自動的に組んでくれる。
(2)back_populatesを使用した場合
双方向のリレーションを自分で組む必要がある。
.lazy="True", lazy="dynamic"の違い
(1)lazy="True"を使用した場合
・例えば`user.subjects`にてモデルをそのまま取得できる
(2)lazy="dunamic"の場合
・`user.subjects.filter_by(id=3)などのようにクエリをチェーンすることができる。`
・idはdb.session.commit()した後に決定するので注意する
"""

db = SQLAlchemy()
ma = Marshmallow()

relationship = db.Table('relationship',
                        db.Column('following_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False),
                        db.Column('followed_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False),
                        UniqueConstraint('following_id', 'followed_id', name='relationship_unique_key')
                        )

tagrelation = db.Table('tagrelation',
                       db.Column('user_id', Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False),
                       db.Column('tag_id', Integer, ForeignKey('tag.id', ondelete="CASCADE"), nullable=False),
                       db.Column('created_at', DateTime, nullable=False, default=datetime.now),
                       UniqueConstraint('user_id', 'tag_id', name='tagrelation_unique_key')
                       )


class TokenBlocklist(db.Model):
    id = Column(Integer, primary_key=True)
    jti = Column(String(36), nullable=False)
    created_at = Column(DateTime, nullable=False)


class Rate(db.Model):
    __table_args__ = (UniqueConstraint('user_id', 'post_id'), {})
    id = Column(Integer, primary_key=True)
    rating = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    post_id = Column(Integer, ForeignKey('post.id', ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class Notification(db.Model):
    id = Column(Integer, primary_key=True)
    passive_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"))
    active_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"))
    category = Column(Enum(NotificationCategory), nullable=False)
    post_id = Column(Integer, default=None)
    subject_id = Column(Integer, default=None)
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
            "post_id": self.post_id,
            "subject_id": self.subject_id,
            "watched": self.watched,
            "created_at": str(self.created_at)
        }


class User(db.Model):
    id = Column(Integer, primary_key=True)
    public_id = Column(String(15), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    name = Column(String(20), nullable=False)
    # 検索用の名前
    name_replaced = Column(String(20), nullable=False)
    introduce = Column(String(140), nullable=False, default="")
    avatar = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.user)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    posts = db.relationship('Post', order_by="desc(Post.created_at)", backref='user', lazy=True,
                            cascade='all, delete-orphan')
    subjects = db.relationship('Subject', order_by="desc(Subject.created_at)", backref='user', lazy=True,
                               cascade='all, delete-orphan')
    rates = db.relationship('Rate', backref='user', lazy=True, cascade='all, delete-orphan')
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
    from_reports = db.relationship(
        'Report',
        primaryjoin='Report.from_id==User.id',
        order_by="desc(Report.created_at)", lazy=True,
        back_populates='from_user'
    )
    target_reports = db.relationship(
        'Report',
        primaryjoin='Report.target_id==User.id',
        order_by="desc(Report.created_at)", lazy=True, cascade='all, delete-orphan',
        back_populates='target_user'
    )
    tags = db.relationship(
        'Tag',
        secondary=tagrelation,
        backref="users"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "public_id": self.public_id,
            "name": self.name,
            "introduce": self.introduce,
            "avatar": self.avatar,
            "created_at": str(self.created_at),
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

    def follow_tag(self, tag):
        if not self.is_following_tag(tag):
            self.tags.append(tag)

    def unfollow_tag(self, tag):
        if self.is_following_tag(tag):
            self.tags.remove(tag)

    def is_following_tag(self, tag):
        return list(filter(lambda x: x.id == tag.id, self.tags))


class Subject(db.Model):
    id = Column(Integer, primary_key=True)
    content = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    tag_id = Column(Integer, ForeignKey('tag.id', ondelete="CASCADE"), nullable=False)

    posts = db.relationship('Post', order_by="desc(Post.created_at)", backref='subject',
                            lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "user_id": self.user_id,
            "tag_id": self.tag_id,
            "created_at": str(self.created_at)
        }


class Tag(db.Model):
    __table_args__ = (UniqueConstraint('name'), {})
    id = Column(Integer, primary_key=True)
    name = Column(String(15), nullable=False)
    avatar = Column(String(255), default=None)
    who_edit = Column(Integer, default=None)
    category = Column(Enum(TagCategory), default=TagCategory.general)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    subjects = db.relationship('Subject', order_by="desc(Subject.id)", backref='tag', lazy=True,
                               cascade='all, delete-orphan')
    reports = db.relationship('ReportTag', order_by="desc(ReportTag.id)", backref='tag', lazy=True,
                              cascade='all, delete-orphan')

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "avatar": self.avatar,
            "who_edit": self.who_edit,
            "category": self.category,
            "created_at": str(self.created_at)
        }


class Post(db.Model):
    id = Column(Integer, primary_key=True)
    content = Column(String(100), nullable=False)
    color_id = Column(Enum(PostColorId), nullable=False)
    font_id = Column(Enum(PostFontId), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey('subject.id', ondelete="CASCADE"), nullable=False)

    rates = db.relationship('Rate', backref='post', lazy=True, cascade='all, delete-orphan')

    def sum_rating(self):
        result = 0
        for rate in self.rates:
            result = result + rate.rating

        return result

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "color_id": self.color_id,
            "font_id": self.font_id,
            "user_id": self.user_id,
            "subject_id": self.subject_id,
            "created_at": str(self.created_at),
            "sum_rating": self.sum_rating()
        }


class Report(db.Model):
    id = Column(Integer, primary_key=True)
    from_id = Column(Integer, ForeignKey('user.id'))
    target_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"))
    category = Column(Enum(ReportCategory), nullable=False)
    content = Column(String(200))
    marked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    from_user = db.relationship("User", foreign_keys=[from_id], back_populates='from_reports')
    target_user = db.relationship("User", foreign_keys=[target_id], back_populates='target_reports')

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "content": self.content,
            "from_id": self.from_id,
            "target_id": self.target_id,
            "marked": self.marked,
            "created_at": str(self.created_at)
        }


class ReportTag(db.Model):
    id = Column(Integer, primary_key=True)
    from_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    target_id = Column(Integer, ForeignKey('tag.id', ondelete="CASCADE"), nullable=False)
    category = Column(Enum(ReportTagCategory), nullable=False)
    content = Column(String(200))
    marked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "content": self.content,
            "from_id": self.from_id,
            "target_id": self.target_id,
            "marked": self.marked,
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
