import os

from dotenv import load_dotenv


load_dotenv(override=True)


def get_required_env(name):
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value


class Config:

    # Flask configuration
    SECRET_KEY = get_required_env(
        "SECRET_KEY"
    )

    # MySQL configuration
    DB_HOST = get_required_env(
        "DB_HOST"
    )

    DB_PORT = int(
        os.getenv(
            "DB_PORT",
            "3306"
        )
    )

    DB_USER = get_required_env(
        "DB_USER"
    )

    DB_PASSWORD = get_required_env(
        "DB_PASSWORD"
    )

    DB_NAME = get_required_env(
        "DB_NAME"
    )

    # Google OAuth configuration
    GOOGLE_CLIENT_ID = get_required_env(
        "GOOGLE_CLIENT_ID"
    )

    GOOGLE_CLIENT_SECRET = get_required_env(
        "GOOGLE_CLIENT_SECRET"
    )

    # Email configuration
    MAIL_SERVER = os.getenv(
        "MAIL_SERVER",
        "smtp.gmail.com"
    )

    MAIL_PORT = int(
        os.getenv(
            "MAIL_PORT",
            "587"
        )
    )

    MAIL_USERNAME = get_required_env(
        "MAIL_USERNAME"
    )

    MAIL_PASSWORD = get_required_env(
        "MAIL_PASSWORD"
    )

    MAIL_USE_TLS = (
        os.getenv(
            "MAIL_USE_TLS",
            "True"
        ).lower()
        == "true"
    )