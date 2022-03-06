import click
from faker import Faker
from sqlalchemy import text

from api.model.aggregate import point
from api.model.confirmation import Confirmation
from api.model.enum.enums import UserRole
from api.model.question import Question
from api.model.user import User
from app import app
from database import db

"""
# * How to execute *
$ export FLASK_APP=seed.py
$ flask seed_execute --stop
        or
$ flask seed_execute --no-stop 
"""


@app.cli.command('seed_execute')
@click.option('--stop/--no-stop', default=False)
def seed_execute(stop: bool):
    try:
        """reset the database"""
        execute_type = "Only drop." if stop else "All processes"
        app.logger.info(f"Session begin. execute type is '{execute_type}'")
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        db.session.flush()
        tables = db.session.execute(text("show tables;"))
        for tbl in tables:
            # ex: ('user',) > user
            tbl = str(tbl).replace("('", "").replace("',)", "")
            db.session.execute(text(f'DROP TABLE IF EXISTS {tbl};'))
            db.session.flush()
            app.logger.info(f'{tbl} dropped.')
        if stop:
            app.logger.info("Drop All models completely and seed processes had been stopped.")
            return

        db.create_all()
        app.logger.info("Done drop and create tables completely. And starting create seed date.")

        """Create users *ex: (range(1, 11) > 1~10)"""
        faker_gen = Faker()
        for n in range(1, 51):
            n = str(n)
            username = f'sample{n + n}'
            email = f"sample{n}@sample.com"
            password = 'passpass'
            introduce = faker_gen.company()
            role = UserRole.user

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

        """Admin User"""
        username = 'testuser'
        email = 'test@test.com'
        password = 'changeafter'
        introduce = "Hi, I'm test user."
        role = UserRole.admin
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

        """Create user relationships"""
        first_user = User.query.filter_by(id=1).first()
        target_users = User.query.all()
        for target_user in target_users:
            first_user.follow(target_user)
            target_user.follow(first_user)
            db.session.flush()

        """Create questions"""
        for n in range(1, 7):
            for n_2 in range(1, 15):
                content = faker_gen.address() + "?"
                option_first = "option1"
                option_second = "option2"
                question = Question(
                    content=content,
                    user_id=n,
                    option_first=option_first,
                    option_second=option_second
                )
                db.session.add(question)
                db.session.flush()
        app.logger.info("Successfully created data.")
    except:
        app.logger.error("Something fatal error occurred and start rollback.")
        db.session.rollback()
        raise
    finally:
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        db.session.commit()
        db.session.close()
        app.logger.info("Session had closed.")
