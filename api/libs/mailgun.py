import os

from flask import Response
from requests import post


class MailGunException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class MailGun:
    MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
    MAILGUN_DOMAIN_NAME = os.getenv("MAILGUN_DOMAIN_NAME")

    @classmethod
    def send_email(cls, email: list[str], subject: str, text: str) -> Response:

        if cls.MAILGUN_API_KEY is None:
            raise MailGunException("Failed to load MailGun API key.")
        if cls.MAILGUN_DOMAIN_NAME is None:
            raise MailGunException("Failed to load MailGun domain name.")

        response = post(
            f"https://api.mailgun.net/v3/{cls.MAILGUN_DOMAIN_NAME}/messages",
            auth=("api", cls.MAILGUN_API_KEY),
            data={"from": f"Enqueter <mailgun@{cls.MAILGUN_DOMAIN_NAME}>",
                  "to": email,
                  "subject": subject,
                  "text": text}
        )

        if response.status_code != 200:
            raise MailGunException("Error in sending confirmation email, user registration failed.")

        return response
