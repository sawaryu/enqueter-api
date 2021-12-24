import random

from faker import Faker
from werkzeug.security import generate_password_hash
from api.model.models import User, db, Subject, Post, Tag, TagCategory, UserRole
from random import randrange
from app import app
from api.model.enums import PostColorId, PostFontId

""""
※実行する前にモデルなどよく確認する。
※実行ファイルが`app.py`の場合は自動で認識しれくれるため環境変数の指定は不要
$ FLASK_APP=main.py flask shell
>> from seed import main    
>> main()
>> exit()
"""


# db create all and seed
def main():
    """take in flask app"""
    with app.app_context():
        #
        # """db create all"""
        db.drop_all()
        db.create_all()

        """faker インスタンス作成"""
        faker_gen = Faker('ja_JP')

        """User"""
        # create 1~10 users.
        for n in range(1, 11):
            n = str(n)
            name = faker_gen.name()
            name_replaced = name.replace(' ', '').replace('　', '')
            public_id = f'sample{n + n}'
            password = 'passpass'
            avatar = f'egg_{randrange(1, 11)}.png'
            introduce = faker_gen.company()
            role = UserRole.admin if n == "1" else UserRole.user

            new_user = User(
                name=name,
                name_replaced=name_replaced,
                public_id=public_id,
                password=generate_password_hash(password, method='sha256'),
                avatar=avatar,
                introduce=introduce,
                role=role
            )
            db.session.add(new_user)
            db.session.commit()

        # tag
        tag_1 = Tag(name="恋愛", category=TagCategory.official)
        tag_2 = Tag(name="悩み", category=TagCategory.official)
        tag_3 = Tag(name="学問", category=TagCategory.official)
        tag_4 = Tag(name="昆虫", category=TagCategory.official)
        tag_5 = Tag(name="芸能", category=TagCategory.official)
        tag_6 = Tag(name="タバコ", category=TagCategory.official)
        tag_7 = Tag(name="酒", category=TagCategory.official)
        tag_8 = Tag(name="モテたい", category=TagCategory.official)
        tag_9 = Tag(name="映画", category=TagCategory.official)
        tag_10 = Tag(name="ゲーム", category=TagCategory.official)
        tag_11 = Tag(name="YouTube", category=TagCategory.official)
        db.session.add(tag_1)
        db.session.add(tag_2)
        db.session.add(tag_3)
        db.session.add(tag_4)
        db.session.add(tag_5)
        db.session.add(tag_6)
        db.session.add(tag_7)
        db.session.add(tag_8)
        db.session.add(tag_9)
        db.session.add(tag_10)
        db.session.add(tag_11)
        db.session.commit()

        # subject
        for n in range(1, 7):
            for n_2 in range(1, 5):
                content = faker_gen.building_name() + "？"

                new_subject = Subject(
                    content=content,
                    user_id=n,
                    tag_id=randrange(1, 10)
                )
                db.session.add(new_subject)
            db.session.commit()

        # post
        for n in range(1, 30):
            subject_id = randrange(1, 20)
            color_id = random.choice(PostColorId.get_value_list())
            font_id = random.choice(PostFontId.get_value_list())
            content = faker_gen.country()
            user_id = randrange(2, 9)

            target_subject = Subject.query.filter_by(id=subject_id).first()
            if target_subject.user_id == user_id:
                pass
            else:
                new_post = Post(
                    content=content,
                    color_id=color_id,
                    font_id=font_id,
                    subject_id=subject_id,
                    user_id=user_id
                )
                db.session.add(new_post)
        db.session.commit()

        """Relationship"""
        first_user = User.query.filter_by(id=1).first()
        for n in range(1, 10):
            target_user = User.query.filter_by(id=n + 1).first()
            first_user.follow(target_user)
            target_user.follow(first_user)
            db.session.commit()


if __name__ == '__main__':
    main()
