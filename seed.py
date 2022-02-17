from time import time

from faker import Faker
from sqlalchemy import text

from api.model.aggregate import point
from api.model.confirmation import Confirmation
from api.model.enum.enums import UserRole
from api.model.others import Question
from api.model.user import User
from app import app
from database import db


def main():
    """take in flask app"""
    with app.app_context():
        db.session.begin()
        try:
            """reset the database"""
            app.logger.info("Session begin.")
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            db.session.commit()
            # db.drop_all()
            meta = db.metadata
            for tbl in reversed(meta.sorted_tables):
                app.logger.info(f'{tbl} dropped.')
                db.session.execute(text(f'DROP TABLE IF EXISTS {tbl};'))
                db.session.commit()
            db.create_all()
            app.logger.info("Done drop and create tables. And starting create seed date.")

            """Create users *(range(1, 11) > 1~10)"""
            faker_gen = Faker()
            for n in range(1, 101):
                n = str(n)
                # nickname = ""
                # while not nickname:
                #     faker_name = faker_gen.name()
                #     if len(faker_name) <= 20:
                #         nickname = faker_name
                #         break
                username = f'sample{n + n}'
                email = f"sample{n}@sample.com"
                password = 'passpass'
                introduce = faker_gen.company()
                role = UserRole.admin if n == "1" else UserRole.user

                user = User(
                    username=username,
                    email=email,
                    password=password,
                )
                user.introduce = introduce
                user.role = role
                db.session.add(user)
                db.session.flush()
                confirmation = Confirmation(user.id)
                confirmation.confirmed = True
                db.session.add(confirmation)
                db.session.flush()

                # inset point
                insert_point = point.insert().values(
                    user_id=user.id,
                    point=3
                )
                db.session.execute(insert_point)

            """Create user relationships"""
            first_user = User.query.filter_by(id=1).first()
            target_users = User.query.all()
            for target_user in target_users:
                first_user.follow(target_user)
                target_user.follow(first_user)
                db.session.flush()

            """Create closed questions"""
            for n in range(1, 7):
                content = faker_gen.address() + "?"
                question = Question(
                    content=content,
                    user_id=n
                )
                question.closed_at = time()
                db.session.add(question)
                db.session.flush()

            """Create questions"""
            for n in range(1, 7):
                for n_2 in range(1, 15):
                    content = faker_gen.address() + "?"
                    question = Question(
                        content=content,
                        user_id=n
                    )
                    db.session.add(question)
                    db.session.flush()
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            db.session.commit()
            app.logger.info("Successfully created data.")
        except:
            app.logger.error("Something fatal error occurred and start rollback.")
            db.session.rollback()
            raise
        finally:
            app.logger.info("Session had closed.")
            db.session.close()


if __name__ == '__main__':
    main()
