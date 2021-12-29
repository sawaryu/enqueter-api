from faker import Faker
from werkzeug.security import generate_password_hash
from api.model.models import User, db, UserRole
from random import randrange
from app import app


def main():
    """take in flask app"""
    with app.app_context():

        """reset the database"""
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

        """Relationship"""
        first_user = User.query.filter_by(id=1).first()
        for n in range(1, 10):
            target_user = User.query.filter_by(id=n + 1).first()
            first_user.follow(target_user)
            target_user.follow(first_user)
            db.session.commit()


if __name__ == '__main__':
    main()
