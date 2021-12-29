import enum


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"

    @classmethod
    def get_value_list(cls):
        return list(map(lambda x: x.value, cls))
