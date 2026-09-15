from flask import Blueprint, redirect, url_for, session, flash
from authlib.integrations.flask_client import OAuth

from config import Config
from database.connection import get_connection


oauth = OAuth()


google_auth = Blueprint(
    "google_auth",
    __name__,
    url_prefix="/auth"
)


def register_google(app):

    oauth.init_app(app)

    oauth.register(
        name="google",
        client_id=Config.GOOGLE_CLIENT_ID,
        client_secret=Config.GOOGLE_CLIENT_SECRET,
        server_metadata_url=(
            "https://accounts.google.com/"
            ".well-known/openid-configuration"
        ),
        client_kwargs={
            "scope": "openid profile email"
        }
    )


@google_auth.route("/google")
def google_login():

    redirect_uri = url_for(
        "google_auth.google_callback",
        _external=True
    )

    return oauth.google.authorize_redirect(
        redirect_uri
    )


@google_auth.route("/google/callback")
def google_callback():

    connection = None
    cursor = None

    try:

        token = oauth.google.authorize_access_token()

        userinfo = token.get("userinfo")

        if not userinfo:

            flash(
                "Google user information could not be retrieved.",
                "error"
            )

            return redirect(url_for("auth.login"))

        google_id = userinfo.get("sub")
        email = userinfo.get("email")
        name = userinfo.get("name")
        picture = userinfo.get("picture")
        email_verified = userinfo.get("email_verified", False)

        if not google_id or not email:

            flash(
                "Google account information is incomplete.",
                "error"
            )

            return redirect(url_for("auth.login"))

        if not email_verified:

            flash(
                "Your Google email address is not verified.",
                "error"
            )

            return redirect(url_for("auth.login"))

        email = email.strip().lower()

        connection = get_connection()

        cursor = connection.cursor(dictionary=True)

        # Check whether this Google account is already linked.
        cursor.execute(
            """
            SELECT
                u.id,
                u.name,
                u.email,
                u.profile_picture
            FROM oauth_accounts oa
            INNER JOIN users u
                ON oa.user_id = u.id
            WHERE oa.provider = %s
            AND oa.provider_user_id = %s
            """,
            (
                "google",
                google_id
            )
        )

        linked_user = cursor.fetchone()

        if linked_user:

            user = linked_user

        else:

            # Check whether a normal LifeOS account already exists.
            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    email,
                    profile_picture
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:

                # Link the verified Google account to the existing user.
                cursor.execute(
                    """
                    INSERT INTO oauth_accounts
                    (
                        user_id,
                        provider,
                        provider_user_id
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (
                        existing_user["id"],
                        "google",
                        google_id
                    )
                )

                # Update profile picture if Google provides one.
                if picture:

                    cursor.execute(
                        """
                        UPDATE users
                        SET profile_picture = %s
                        WHERE id = %s
                        """,
                        (
                            picture,
                            existing_user["id"]
                        )
                    )

                    existing_user["profile_picture"] = picture

                connection.commit()

                user = existing_user

            else:

                # Create a new OAuth-only LifeOS account.
                cursor.execute(
                    """
                    INSERT INTO users
                    (
                        name,
                        email,
                        password_hash,
                        profile_picture
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        name or "Google User",
                        email,
                        None,
                        picture
                    )
                )

                user_id = cursor.lastrowid

                cursor.execute(
                    """
                    INSERT INTO oauth_accounts
                    (
                        user_id,
                        provider,
                        provider_user_id
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (
                        user_id,
                        "google",
                        google_id
                    )
                )

                connection.commit()

                user = {
                    "id": user_id,
                    "name": name or "Google User",
                    "email": email,
                    "profile_picture": picture
                }

        # Create a fresh LifeOS session.
        session.clear()

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["profile_picture"] = user["profile_picture"]

        flash(
            "Google login successful.",
            "success"
        )

        return redirect(url_for("dashboard"))

    except Exception as error:

        if connection:
            connection.rollback()

        print("Google login error:", error)

        flash(
            "Google login failed. Please try again.",
            "error"
        )

        return redirect(url_for("auth.login"))

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()