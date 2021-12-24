import enum


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"

    @classmethod
    def get_value_list(cls):
        return list(map(lambda x: x.value, cls))


class TagCategory(str, enum.Enum):
    official = "official"
    general = "general"

    @classmethod
    def get_value_list(cls):
        return list(map(lambda x: x.value, cls))


class PostColorId(int, enum.Enum):
    grey = 1
    white = 2
    pink = 3
    navy = 4
    orange = 5
    blue = 6
    mint = 7

    @classmethod
    def get_value_list(cls):
        return list(map(lambda x: x.value, cls))


class PostFontId(int, enum.Enum):
    one = 1
    two = 2
    three = 3
    four = 4
    five = 5
    six = 6
    seven = 7

    @classmethod
    def get_value_list(cls):
        return list(map(lambda x: x.value, cls))


class NotificationCategory(str, enum.Enum):
    followed = "followed"
    rated = "rated"
    posted = "posted"

    @classmethod
    def get_value_list(cls):
        return list(map(lambda x: x.value, cls))


class ReportCategory(str, enum.Enum):
    improper = "improper"
    slandering = "slandering"
    impersonation = "impersonation"
    other = "other"

    @classmethod
    def get_value_list(cls):
        return list(map(lambda x: x.value, cls))


class ReportTagCategory(str, enum.Enum):
    name = "name"
    image = "image"
    other = "other"

    @classmethod
    def get_value_list(cls):
        return list(map(lambda x: x.value, cls))
