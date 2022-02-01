from faker import Faker
from api.model.confirmation import Confirmation
from api.model.enum.enums import UserRole
from api.model.others import Question
from api.model.user import User
from app import app
from database import db


def main():
    """take in flask app"""
    with app.app_context():

        """reset the database"""
        db.drop_all()
        db.create_all()

        """Create faker instance"""
        faker_gen = Faker()

        """Create users"""
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
            username = f'sample{n + n}'
            email = f"sample{n}@sample.com"
            password = 'passpass'
            introduce = faker_gen.company()
            role = UserRole.admin if n == "1" else UserRole.user

            user = User(
                username=username,
                email=email,
                nickname=nickname,
                password=password,
            )
            user.introduce = introduce
            user.role = role
            user.save_to_db()

            confirmation = Confirmation(user.id)
            confirmation.confirmed = True
            confirmation.save_to_db()

        """Create user relationships"""
        first_user = User.query.filter_by(id=1).first()
        for n in range(1, 10):
            target_user = User.query.filter_by(id=n + 1).first()
            first_user.follow(target_user)
            target_user.follow(first_user)
            db.session.commit()

        """Create questions"""
        for n in range(1, 7):
            for n_2 in range(1, 15):
                content = faker_gen.address() + "?"
                question = Question(
                    content=content,
                    user_id=n
                )
                question.save_to_db()

        """Create closed questions"""
        # for n in range(1, 7):
        #     content = faker_gen.address() + "?"
        #     question = Question(
        #         content=content,
        #         user_id=n
        #     )
        #     question.save_to_db()


if __name__ == '__main__':
    main()
