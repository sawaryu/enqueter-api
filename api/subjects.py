from datetime import timedelta, datetime

from flask import request
from flask_jwt_extended import current_user, jwt_required
from flask_restx import Namespace, Resource, fields
from sqlalchemy.sql.functions import func
from api.model.models import Subject, db, Post, Rate, User, Tag
from api.helpers.helper import return_subjects_list, return_posts_list, return_post, return_subject

subject_ns = Namespace('/subjects')
tagModel = subject_ns.model('Tag', {
    'name': fields.String(required=True, max_length=15, pattern=r'\S')
})

subjectCreate = subject_ns.model('SubjectCreate', {
    'content': fields.String(required=True, max_length=100, pattern=r'\S'),
    'tag': fields.Nested(tagModel, required=True)
})


# TODO: subjects, yourPostを分割する。
@subject_ns.route('/<int:subject_id>')
class SubjectShow(Resource):
    # show
    @subject_ns.doc(
        security='jwt_auth',
        description='Subjectを一つとあなたの最新のPostを返します。'
    )
    @jwt_required()
    def get(self, subject_id):
        subject = Subject.query.filter_by(id=subject_id).first()
        if not subject:
            return {
                       'status': 404,
                       'message': 'the page you want was not founded.'
                   }, 404

        your_post = Post.query.filter_by(user_id=current_user.id, subject_id=subject_id)\
            .order_by(Post.created_at.desc()).first()

        return dict(subject=return_subject(subject), your_post=return_post(your_post))


@subject_ns.route('/<int:subject_id>/posts/latest')
class SubjectLatestPosts(Resource):
    @subject_ns.doc(
        security='jwt_auth',
        description='Subject一つに対して新しい順のPostリストを返す。'
    )
    @jwt_required()
    def get(self, subject_id):
        page = int(request.args.get('page'))

        posts = Post.query.filter_by(subject_id=subject_id) \
            .order_by(Post.id.desc()) \
            .paginate(page=page, per_page=20, error_out=False).items

        return return_posts_list(posts)


@subject_ns.route('/<int:subject_id>/posts/old')
class SubjectOldPosts(Resource):
    @subject_ns.doc(
        security='jwt_auth',
        description='Subject一つに対して古い順のPostリストを返す。'
    )
    @jwt_required()
    def get(self, subject_id):
        page = int(request.args.get('page'))

        posts = Post.query.filter_by(subject_id=subject_id) \
            .paginate(page=page, per_page=20, error_out=False).items

        return return_posts_list(posts)


@subject_ns.route('/<int:subject_id>/posts/popular')
class SubjectPopularPosts(Resource):
    @subject_ns.doc(
        security='jwt_auth',
        description='Subject一つに対して人気順のPostリストを返す。※ただし内部結合にて取得し、評価のないpostは取得しないものとする。'
    )
    @jwt_required()
    def get(self, subject_id):
        page = int(request.args.get('page'))

        sql_objects = db.session.query(Post, func.sum(Rate.rating)).join(Rate)\
            .filter(Post.subject_id == subject_id).group_by(Post.id).order_by(func.sum(Rate.rating).desc())\
            .paginate(page=page, per_page=20, error_out=False).items

        posts = []
        for post in sql_objects:
            posts.append(post.Post)

        return return_posts_list(posts)


@subject_ns.route('')
class SubjectsIndex(Resource):
    # create
    @subject_ns.doc(
        security='jwt_auth',
        body=subjectCreate,
        description='Subjectを一つ作成します。(content)'
    )
    @jwt_required()
    def post(self):
        if current_user.subjects and (current_user.subjects[0].created_at + timedelta(minutes=3)) > datetime.now():
            return {
                       "status": 400,
                       "message": "最新の質問投稿からまだ３分が経過していません。"
                   }, 400

        content = request.json['content'].strip()
        name = request.json['tag']["name"].strip()

        tag = Tag.query.filter_by(name=name).first()
        if not tag:
            tag = Tag(name=name)
            db.session.add(tag)
            db.session.commit()

        subject = Subject(content=content, user_id=current_user.id, tag_id=tag.id)

        db.session.add(subject)
        db.session.commit()

        return return_subject(subject)


@subject_ns.route('/contributors')
class SubjectsContributors(Resource):
    # index
    @subject_ns.doc(
        security='jwt_auth',
        description='回答獲得数の多いユーザーを返す',
        params={'period': {'type': 'str', 'description': 'week, month, all'}}
    )
    @jwt_required()
    def get(self):
        period = request.args.get("period")
        d = {}
        if period == "week":
            d = {"weeks": 1}
        elif period == "month":
            d = {"days": 30}
        elif period == "all":
            # 100年として全て取得する。
            d = {"days": 365*100}

        sql_objects = db.session.query(User, func.count(Post.id).label("posts_count")) \
            .join(Subject, Subject.user_id == User.id).join(Post, Post.subject_id == Subject.id)\
            .filter(Post.created_at > (datetime.now() - timedelta(**d))) \
            .group_by(User.id).order_by(func.count(Post.id).desc()).limit(10).all()

        users = list(map(lambda x: x.User.to_dict() | {"posts_count": x.posts_count}, sql_objects))

        return users


@subject_ns.route('/latest')
class SubjectsLatest(Resource):
    @subject_ns.doc(
        security='jwt_auth',
        description='質問一覧の最新項目を一定件数ずつページネーションして返す。postの無い投稿も取得したいので外部結合',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self):
        page = int(request.args.get('page'))

        items = db.session.query(Subject, User, func.count(Post.id).label("post_count")) \
            .outerjoin(Post, Post.subject_id == Subject.id).join(User, User.id == Subject.user_id) \
            .group_by(Subject.id).order_by(Subject.id.desc()).paginate(page=page, per_page=20, error_out=False).items

        subjects = list(map(lambda x: x.Subject, items))
        return return_subjects_list(subjects)


@subject_ns.route('/feed')
class SubjectsFeed(Resource):
    @subject_ns.doc(
        security='jwt_auth',
        description='質問一覧のfeed項目を一定件数ずつページネーションして返す。',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self):
        page = int(request.args.get('page'))

        following_ids = [current_user.id]
        for user in current_user.followings:
            following_ids.append(user.id)

        subjects = Subject.query.filter(Subject.user_id.in_(following_ids)).order_by(
            Subject.id.desc()).paginate(page=page, per_page=20,
                                        error_out=False).items

        return return_subjects_list(subjects)


@subject_ns.route('/popular/<string:period>')
class SubjectsPopular(Resource):
    @subject_ns.doc(
        security='jwt_auth',
        description='質問一覧のpopular項目を一定件数ずつページネーションして返す。postの無い投稿が表示しないので内部結合',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self, period):
        page = int(request.args.get('page'))
        if period == "week":
            d = {"weeks": 1}
        elif period == "month":
            d = {"days": 30}
        else:
            d = {"days": 365*100}

        items = db.session.query(Subject, func.count(Post.id)).join(Post) \
            .filter(Subject.created_at > (datetime.now() - timedelta(**d))) \
            .group_by(Subject.id) \
            .order_by(func.count(Post.id).desc()) \
            .paginate(page=page, per_page=20, error_out=False).items

        subjects = list(map(lambda x: x.Subject, items))
        return return_subjects_list(subjects)
