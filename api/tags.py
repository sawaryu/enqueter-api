import http
from datetime import datetime, timedelta
from flask import request
from flask_jwt_extended import jwt_required, current_user
from flask_restx import Namespace, Resource
from sqlalchemy import func, desc
from api.helpers.helper import return_subjects_list, return_posts_list
from api.model.models import db, Tag, Subject, Post, TagCategory, tagrelation, User

tag_ns = Namespace('/tags')


@tag_ns.route('')
class TagsIndex(Resource):
    @tag_ns.doc(
        security='jwt_auth',
        description='タグ一覧画面(初期表示)'
    )
    @jwt_required()
    def get(self):

        objects = db.session.query(Tag, func.count(tagrelation.c.tag_id))\
            .outerjoin(tagrelation, tagrelation.c.tag_id == Tag.id)\
            .group_by(Tag.id).order_by(desc(func.count(tagrelation.c.tag_id))).all()

        tags_list = []

        if len(objects):
            tags_objects = list(map(lambda x: x.Tag, objects))
            for tag in tags_objects:
                is_following = True if current_user.is_following_tag(tag) else False
                tags_list.append(tag.to_dict() | {"subjects_count": len(tag.subjects),
                                                  "follower_count": len(tag.users),
                                                  "is_following": is_following})

        return tags_list


@tag_ns.route('/trend')
class TagsTrend(Resource):
    @tag_ns.doc(
        security='jwt_auth',
        description='トレンドのタグを返す(一週間で統計する)',
        params={'arg': {'type': 'str'}}
    )
    @jwt_required()
    def get(self):
        arg = request.args.get("arg")

        if arg == "follower":
            objects = db.session.query(Tag, func.count(tagrelation.c.tag_id).label("week_count")).join(tagrelation) \
                        .filter(tagrelation.c.created_at > (datetime.now() - timedelta(weeks=1))) \
                        .group_by(Tag.id).order_by(func.count(tagrelation.c.tag_id).desc()).limit(9).all()
        else:
            objects = db.session.query(Tag, func.count(Subject.id).label("week_count")).join(Subject) \
                        .filter(Subject.created_at > (datetime.now() - timedelta(weeks=1))) \
                        .group_by(Tag.id).order_by(desc(func.count(Subject.id))).limit(9).all()

        tags_list = []
        if len(objects):
            for o in objects:
                is_following = True if current_user.is_following_tag(o.Tag) else False
                tags_list.append(o.Tag.to_dict() | {"subjects_count": len(o.Tag.subjects),
                                                    "follower_count": len(o.Tag.users),
                                                    "is_following": is_following,
                                                    "week_count": o.week_count})

        return tags_list


@tag_ns.route('/search/autocomplete')
class TagsSearchAutocomplete(Resource):
    @tag_ns.doc(
        security='jwt_auth',
        description='タグ検索。contain形式でタグを全て検索して返却する。'
    )
    @jwt_required()
    def get(self):
        search = request.args.get('search')
        tags_objects = db.session.query(Tag).filter(Tag.name.like('%\\' + search + '%', escape='\\')).all()

        tags_list = []
        for tag in tags_objects:
            is_following = True if current_user.is_following_tag(tag) else False
            tags_list.append(tag.to_dict() | {"subjects_count": len(tag.subjects),
                                              "follower_count": len(tag.users),
                                              "is_following": is_following})

        return tags_list


@tag_ns.route('/official')
class TagsOfficial(Resource):
    @tag_ns.doc(
        security='jwt_auth',
        description='オフィシャルタグを全て返す。'
    )
    @jwt_required()
    def get(self):

        tags_objects = Tag.query.filter_by(category=TagCategory.official).all()

        tags_list = []
        for tag in tags_objects:
            is_following = True if current_user.is_following_tag(tag) else False
            tags_list.append(tag.to_dict() | {"subjects_count": len(tag.subjects),
                                              "follower_count": len(tag.users),
                                              "is_following": is_following})

        return tags_list


@tag_ns.route('/<int:tag_id>')
class TagShow(Resource):
    @tag_ns.doc(
        security='jwt_auth',
        description='タグを一件と必要な情報を取得する。'
    )
    @jwt_required()
    def get(self, tag_id):
        tag = Tag.query.filter_by(id=tag_id).first()
        if not tag:
            return dict(status=404, message="お探しのページが見つかりませんでした。"), http.HTTPStatus.NOT_FOUND

        # 現在ユーザーがフォローしているかどうか。
        is_following = True if current_user.is_following_tag(tag) else False

        # 最終編集者を取得する。
        edit_user = None
        if tag.who_edit:
            edit_user = User.query.filter_by(id=tag.who_edit).one_or_none()
            if edit_user:
                edit_user = edit_user.to_dict()

        return tag.to_dict() | {"subjects_count": len(tag.subjects),
                                "follower_count": len(tag.users),
                                "edit_user": edit_user,
                                "is_following": is_following}


@tag_ns.route('/<int:tag_id>/contributors')
class TagContributors(Resource):
    @tag_ns.doc(
        security='jwt_auth',
        description='タグ一件の貢献者を10件返す。(期間別)',
        params={'period': {'type': 'str'}}
    )
    @jwt_required()
    def get(self, tag_id):
        period = request.args.get("period")
        d = {}
        if period == "week":
            d = {"weeks": 1}
        elif period == "month":
            d = {"days": 30}
        elif period == "all":
            # 100年として全て取得する。
            d = {"days": 365*100}

        tag = Tag.query.filter_by(id=tag_id).first()
        if not tag:
            return dict(status=404, message="お探しのページが見つかりませんでした。"), http.HTTPStatus.NOT_FOUND

        sql_objects = db.session.query(User, func.count(Subject.id).label("subjects_count")) \
            .join(Subject) \
            .filter(Subject.tag_id == tag_id) \
            .filter(Subject.created_at > (datetime.now() - timedelta(**d))) \
            .group_by(User.id).order_by(func.count(Subject.id).desc()).limit(10).all()

        users = list(map(lambda x: x.User.to_dict() | {"subjects_count": x.subjects_count}, sql_objects))

        return users


@tag_ns.route('/<int:tag_id>/subjects')
class TagSubjects(Resource):
    @tag_ns.doc(
        security='jwt_auth',
        description='タグに対応するsubjectsを全て返す。',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self, tag_id):
        page = int(request.args.get('page'))
        tag = Tag.query.filter_by(id=tag_id).first()

        if not tag:
            return dict(status=404, message="お探しのページが見つかりませんでした。"), 404

        subject_objects = Subject.query.filter_by(tag_id=tag_id)\
            .order_by(Subject.id.desc()).paginate(page=page, per_page=20, error_out=False).items

        return return_subjects_list(subject_objects)


@tag_ns.route('/<int:tag_id>/posts')
class TagPosts(Resource):
    @tag_ns.doc(
        security='jwt_auth',
        description='タグに対応するpostsを全て返す。',
        params={'page': {'type': 'str'}}
    )
    @jwt_required()
    def get(self, tag_id):
        page = int(request.args.get('page'))
        tag = Tag.query.filter_by(id=tag_id).first()

        if not tag:
            return dict(status=404, message="お探しのページが見つかりませんでした。"), 404

        post_objects = Post.query.join(Subject).filter(Subject.tag_id == tag_id)\
            .order_by(Post.id.desc()).paginate(page=page, per_page=20, error_out=False).items

        return return_posts_list(post_objects)


@tag_ns.route('/<int:tag_id>/relationships')
class TagRelation(Resource):
    @tag_ns.doc(
        security='jwt_auth',
        description='タグをフォローする。'
    )
    @jwt_required()
    def post(self, tag_id):
        tag = Tag.query.filter_by(id=tag_id).first()
        if not tag:
            return dict(status=404, message="お探しのページが見つかりませんでした。"), 404

        current_user.follow_tag(tag)
        db.session.commit()

        return dict(status=200, messaeg="successfully follow the tag.")

    @tag_ns.doc(
        security='jwt_auth',
        description='タグをアンフォローする。'
    )
    @jwt_required()
    def delete(self, tag_id):
        tag = Tag.query.filter_by(id=tag_id).first()
        if not tag:
            return dict(status=409, message="conflict error."), 409

        current_user.unfollow_tag(tag)
        db.session.commit()

        return dict(status=200, messaeg="successfully unfollow the tag.")
