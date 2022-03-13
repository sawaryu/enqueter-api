from faker import Faker
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
$ flask seed_execute
"""


@app.cli.command('seed_execute')
def seed_execute() -> None:
    """Insert seed data."""
    try:
        app.logger.info("---START---")

        """Test Users"""
        test_users: list[User] = []
        for n in range(1, 6):
            username = f'test{n}'
            email = f'test{n}@example.com'
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
            test_users.append(user)

        """Sample users *ex: (range(1, 11) > 1~10)"""
        faker_gen = Faker()
        for n in range(1, 31):
            n = str(n)
            username = f'sample{n + n}'
            email = f"sample{n}@example.com"
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

            # insert point
            insert_point = point.insert().values(
                user_id=user.id,
                point=3
            )
            db.session.execute(insert_point)

        """Create user relationships"""
        all_users = User.query.all()
        for normal_user in all_users:
            for test_user in test_users:
                test_user.follow(normal_user)
                normal_user.follow(test_user)
                db.session.flush()

        """Create questions"""
        for (index, q) in enumerate(question_samples):
            question = Question(
                content=q["content"],
                user_id=index + 1,
                option_first=q["option_first"],
                option_second=q["option_second"]
            )
            db.session.add(question)
            db.session.flush()
        db.session.commit()
        app.logger.info("Successfully created data.")
    except:
        app.logger.error("Something fatal error occurred and start rollback.")
        db.session.rollback()
        raise
    finally:
        db.session.close()
        app.logger.info("---END---")


question_samples: list[object] = [
    {"content": "たけのこの里orきのこの山", "option_first": "たけのこの里", "option_second": "きのこの山"},
    {"content": "好きな女優はどっち？", "option_first": "浜辺美波", "option_second": "広瀬すず"},
    {"content": "iPhone? Android?", "option_first": "iPhone", "option_second": "Android"},
    {"content": "Ruby or Python", "option_first": "Ruby", "option_second": "Python"},
    {"content": "Mac or Windows", "option_first": "Mac", "option_second": "Windows"},
    {"content": "分譲と賃貸どっちがいい？", "option_first": "分譲", "option_second": "賃貸"},
    {"content": "生まれ変わるなら？", "option_first": "女性", "option_second": "男性"},
    {"content": "洋画をみるとき", "option_first": "字幕", "option_second": "吹替"},
    {"content": "眠いときはどっちを飲む？", "option_first": "レッドブル", "option_second": "モンスターエナジー"},
    {"content": "どっち派？", "option_first": "明日花キララ", "option_second": "三上悠亜"},
    {"content": "どっち派？", "option_first": "欅坂", "option_second": "乃木坂"},
    {"content": "値段は関係なくうまいのは？", "option_first": "マック", "option_second": "モスバーガー"},
    {"content": "Nike vs Adidas", "option_first": "Nike", "option_second": "Adidas"},
    {"content": "寝る前スマホをみる？", "option_first": "yes", "option_second": "no"},
    {"content": "夏といえば？", "option_first": "TUBE", "option_second": "サザンオールスターズ"},
    {"content": "Twitter vs Instagram", "option_first": "Twitter", "option_second": "Instagram"},
    {"content": "B'zの代表曲", "option_first": "UltraSoul", "option_second": "Ocean"},
    {"content": "How are you?", "option_first": "Good!", "option_second": "I’m sick"},
    {"content": "野球？サッカー？", "option_first": "野球", "option_second": "サッカー"},
    {"content": "ペプシとコーラ美味しいのは？", "option_first": "ペプシ", "option_second": "コーラ"},
]
