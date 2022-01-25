from datetime import datetime, timedelta

from faker import Faker
from werkzeug.security import generate_password_hash

from api.model.confirmation import Confirmation
from api.model.enum.enums import UserRole
from api.model.others import Question
from api.model.user import User
from random import randrange
from app import app
from database import db


def main():
    """take in flask app"""
    with app.app_context():

        """reset the database"""
        db.drop_all()
        db.create_all()

        """faker インスタンス作成"""
        # faker_gen = Faker('ja_JP')
        faker_gen = Faker()  # english

        """User"""
        # create 1~10 users.
        for n in range(1, 11):
            n = str(n)
            # continue while faker_name > 20;
            nickname = ""
            while not nickname:
                faker_name = faker_gen.name()
                if len(faker_name) <= 20:
                    nickname = faker_name
                    break
            nickname_replaced = nickname.replace(' ', '').replace('　', '')
            username = f'sample{n + n}'
            email = f"sample{n}@sample.com"
            password = 'passpass'
            avatar = f'egg_{randrange(1, 11)}.png'
            introduce = faker_gen.company()
            role = UserRole.admin if n == "1" else UserRole.user

            new_user = User(
                username=username,
                email=email,
                nickname=nickname,
                nickname_replaced=nickname_replaced,
                password=generate_password_hash(password, method='sha256'),
                avatar=avatar,
                introduce=introduce,
                role=role
            )
            db.session.add(new_user)
            db.session.commit()

            # confirmation
            confirmation = Confirmation(new_user.id)
            confirmation.confirmed = True
            db.session.add(confirmation)
            db.session.commit()

        """Relationship"""
        first_user = User.query.filter_by(id=1).first()
        for n in range(1, 10):
            target_user = User.query.filter_by(id=n + 1).first()
            first_user.follow(target_user)
            target_user.follow(first_user)
            db.session.commit()

        """Question"""
        for n in range(1, 7):
            for n_2 in range(1, 5):
                content = faker_gen.address() + "?"
                question = Question(
                    content=content,
                    user_id=n
                )
                db.session.add(question)
        db.session.commit()

        """Closed Question"""
        for n in range(1, 7):
            content = faker_gen.address() + "?"
            question = Question(
                content=content,
                user_id=n,
                closed_at=datetime.now(),
                created_at=datetime.now() - timedelta(days=7)
            )
            db.session.add(question)

        db.session.commit()


if __name__ == '__main__':
    main()
