from flask_jwt_extended import current_user
from api.model.models import Rate


def return_posts_list(posts):
    posts_list = []
    for post in posts:
        rate = Rate.query.filter_by(post_id=post.id, user_id=current_user.id).first()
        rate_count = 0
        if rate:
            rate_count = rate.rating
        post_dict = post.to_dict() | {
            "user": post.user.to_dict(),
            "rate_count": rate_count,
            "subject": post.subject.to_dict() | {"user": post.subject.user.to_dict(),
                                                 "tag": post.subject.tag.to_dict()}
        }
        posts_list.append(post_dict)

    return posts_list


def return_post(post):
    if not post:
        return None

    rate = Rate.query.filter_by(post_id=post.id, user_id=current_user.id).first()
    rate_count = 0
    if rate:
        rate_count = rate.rating
    return post.to_dict() | {
        "user": post.user.to_dict(),
        "rate_count": rate_count,
        "subject": post.subject.to_dict() | {"user": post.subject.user.to_dict(),
                                             "tag": post.subject.tag.to_dict()}
    }


def return_subjects_list(subjects):
    subjects_list = list(map(lambda x: x.to_dict() | {
        "post_count": len(x.posts),
        "user": x.user.to_dict(),
        "tag": x.tag.to_dict()
    }, subjects))

    return subjects_list


def return_subject(subject):
    if not subject:
        return None

    return subject.to_dict() | {
        "post_count": len(subject.posts),
        "user": subject.user.to_dict(),
        "tag":  subject.tag.to_dict()
    }
