import hashlib
import secrets
import smtplib

from datetime import datetime, timedelta
from email.message import EmailMessage

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database.connection import get_connection
from config import Config


auth = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth"
)


# ============================================================
# REGISTER
# ============================================================

@auth.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if (
            not name
            or not email
            or not password
            or not confirm_password
        ):

            flash(
                "All fields are required.",
                "error"
            )

            return redirect(
                url_for("auth.register")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("auth.register")
            )

        if len(password) < 8:

            flash(
                "Password must contain at least 8 characters.",
                "error"
            )

            return redirect(
                url_for("auth.register")
            )

        connection = None
        cursor = None

        try:

            connection = get_connection()

            cursor = connection.cursor(
                dictionary=True
            )

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:

                flash(
                    "An account with this email already exists.",
                    "error"
                )

                return redirect(
                    url_for("auth.register")
                )

            password_hash = generate_password_hash(
                password
            )

            cursor.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password_hash,
                    email_verified
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    name,
                    email,
                    password_hash,
                    False
                )
            )

            user_id = cursor.lastrowid

            # Invalidate any previous verification tokens.
            cursor.execute(
                """
                UPDATE email_verification_tokens
                SET used_at = NOW()
                WHERE user_id = %s
                AND used_at IS NULL
                """,
                (user_id,)
            )

            # Generate a cryptographically secure verification token.
            raw_token = secrets.token_urlsafe(48)

            token_hash = hashlib.sha256(
                raw_token.encode("utf-8")
            ).hexdigest()

            expires_at = (
                datetime.now()
                + timedelta(hours=1)
            )

            cursor.execute(
                """
                INSERT INTO email_verification_tokens
                (
                    user_id,
                    token_hash,
                    expires_at
                )
                VALUES (%s, %s, %s)
                """,
                (
                    user_id,
                    token_hash,
                    expires_at
                )
            )

            connection.commit()

            verification_url = url_for(
                "auth.verify_email",
                token=raw_token,
                _external=True
            )

            email_sent = send_email_verification(
                email,
                name,
                verification_url
            )

            if not email_sent:

                flash(
                    "Account created, but we could not send the "
                    "verification email. Please use Resend Verification.",
                    "error"
                )

                return redirect(
                    url_for("auth.login")
                )

            flash(
                "Registration successful. "
                "Please check your email and verify your account.",
                "success"
            )

            return redirect(
                url_for("auth.login")
            )

        except Exception as error:

            if connection:
                connection.rollback()

            print(
                "Registration error:",
                error
            )

            flash(
                "Something went wrong. Please try again.",
                "error"
            )

            return redirect(
                url_for("auth.register")
            )

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template(
        "auth/register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            flash(
                "Email and password are required.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )

        connection = None
        cursor = None

        try:

            connection = get_connection()

            cursor = connection.cursor(
                dictionary=True
            )

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    email,
                    password_hash,
                    profile_picture,
                    email_verified
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            user = cursor.fetchone()

            if not user:

                flash(
                    "Invalid email or password.",
                    "error"
                )

                return redirect(
                    url_for("auth.login")
                )

            # OAuth-only accounts do not have a password.
            if not user["password_hash"]:

                flash(
                    "This account uses Google login. "
                    "Please continue with Google.",
                    "error"
                )

                return redirect(
                    url_for("auth.login")
                )

            # Block password login until the email is verified.
            if not user["email_verified"]:

                flash(
                    "Please verify your email before logging in. "
                    "Check your inbox for the verification link.",
                    "error"
                )

                return redirect(
                    url_for("auth.login")
                )

            password_valid = check_password_hash(
                user["password_hash"],
                password
            )

            if not password_valid:

                flash(
                    "Invalid email or password.",
                    "error"
                )

                return redirect(
                    url_for("auth.login")
                )

            # Create a fresh session after successful login.
            session.clear()

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]
            session["profile_picture"] = (
                user["profile_picture"]
            )

            return redirect(
                url_for("dashboard")
            )

        except Exception as error:

            print(
                "Login error:",
                error
            )

            flash(
                "Something went wrong. Please try again.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template(
        "auth/login.html"
    )


# ============================================================
# VERIFY EMAIL
# ============================================================

@auth.route("/verify-email/<token>")
def verify_email(token):

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                expires_at,
                used_at
            FROM email_verification_tokens
            WHERE token_hash = %s
            LIMIT 1
            """,
            (token_hash,)
        )

        verification_record = cursor.fetchone()

        if not verification_record:

            flash(
                "This email verification link is invalid.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )

        if verification_record["used_at"] is not None:

            flash(
                "This email verification link has already been used.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )

        if verification_record["expires_at"] < datetime.now():

            flash(
                "This email verification link has expired. "
                "Please request a new verification email.",
                "error"
            )

            return redirect(
                url_for("auth.resend_verification")
            )

        # Mark the user's email as verified.
        cursor.execute(
            """
            UPDATE users
            SET email_verified = TRUE
            WHERE id = %s
            """,
            (verification_record["user_id"],)
        )

        # Mark the verification token as used.
        cursor.execute(
            """
            UPDATE email_verification_tokens
            SET used_at = NOW()
            WHERE id = %s
            """,
            (verification_record["id"],)
        )

        connection.commit()

        flash(
            "Email verified successfully. You can now login.",
            "success"
        )

        return redirect(
            url_for("auth.login")
        )

    except Exception as error:

        if connection:
            connection.rollback()

        print(
            "Email verification error:",
            error
        )

        flash(
            "Something went wrong while verifying your email.",
            "error"
        )

        return redirect(
            url_for("auth.login")
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# RESEND VERIFICATION EMAIL
# ============================================================

@auth.route(
    "/resend-verification",
    methods=["GET", "POST"]
)
def resend_verification():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        if not email:

            flash(
                "Please enter your email address.",
                "error"
            )

            return redirect(
                url_for("auth.resend_verification")
            )

        connection = None
        cursor = None

        try:

            connection = get_connection()

            cursor = connection.cursor(
                dictionary=True
            )

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    email,
                    password_hash,
                    email_verified
                FROM users
                WHERE email = %s
                LIMIT 1
                """,
                (email,)
            )

            user = cursor.fetchone()

            # Use a generic message to avoid revealing
            # whether an account exists.
            if (
                not user
                or user["email_verified"]
                or not user["password_hash"]
            ):

                flash(
                    "If an unverified account exists for this email, "
                    "a new verification link has been sent.",
                    "success"
                )

                return redirect(
                    url_for("auth.login")
                )

            # Invalidate previous unused verification tokens.
            cursor.execute(
                """
                UPDATE email_verification_tokens
                SET used_at = NOW()
                WHERE user_id = %s
                AND used_at IS NULL
                """,
                (user["id"],)
            )

            # Generate a new secure token.
            raw_token = secrets.token_urlsafe(48)

            token_hash = hashlib.sha256(
                raw_token.encode("utf-8")
            ).hexdigest()

            expires_at = (
                datetime.now()
                + timedelta(hours=1)
            )

            cursor.execute(
                """
                INSERT INTO email_verification_tokens
                (
                    user_id,
                    token_hash,
                    expires_at
                )
                VALUES (%s, %s, %s)
                """,
                (
                    user["id"],
                    token_hash,
                    expires_at
                )
            )

            connection.commit()

            verification_url = url_for(
                "auth.verify_email",
                token=raw_token,
                _external=True
            )

            email_sent = send_email_verification(
                user["email"],
                user["name"],
                verification_url
            )

            if not email_sent:

                flash(
                    "Unable to send the verification email. "
                    "Please try again later.",
                    "error"
                )

                return redirect(
                    url_for("auth.resend_verification")
                )

            flash(
                "If an unverified account exists for this email, "
                "a new verification link has been sent.",
                "success"
            )

            return redirect(
                url_for("auth.login")
            )

        except Exception as error:

            if connection:
                connection.rollback()

            print(
                "Resend verification error:",
                error
            )

            flash(
                "Something went wrong. Please try again.",
                "error"
            )

            return redirect(
                url_for("auth.resend_verification")
            )

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template(
        "auth/resend_verification.html"
    )


# ============================================================
# SEND EMAIL VERIFICATION
# ============================================================

def send_email_verification(
    recipient_email,
    recipient_name,
    verification_url
):

    try:

        message = EmailMessage()

        message["Subject"] = (
            "Verify Your LifeOS Email"
        )

        message["From"] = Config.MAIL_USERNAME

        message["To"] = recipient_email

        message.set_content(
            f"""
Hello {recipient_name},

Welcome to LifeOS.

Please verify your email address by clicking the link below:

{verification_url}

This verification link will expire in 1 hour.

If you did not create a LifeOS account, you can safely ignore this email.

Regards,
LifeOS Team
"""
        )

        with smtplib.SMTP(
            Config.MAIL_SERVER,
            Config.MAIL_PORT
        ) as smtp:

            smtp.ehlo()

            if Config.MAIL_USE_TLS:

                smtp.starttls()

                smtp.ehlo()

            smtp.login(
                Config.MAIL_USERNAME,
                Config.MAIL_PASSWORD
            )

            smtp.send_message(
                message
            )

        return True

    except Exception as error:

        print(
            "Email verification error:",
            error
        )

        return False


# ============================================================
# FORGOT PASSWORD
# ============================================================

@auth.route(
    "/forgot-password",
    methods=["GET", "POST"]
)
def forgot_password():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        if not email:

            flash(
                "Please enter your email address.",
                "error"
            )

            return redirect(
                url_for("auth.forgot_password")
            )

        connection = None
        cursor = None

        try:

            connection = get_connection()

            cursor = connection.cursor(
                dictionary=True
            )

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    email,
                    password_hash
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            user = cursor.fetchone()

            # Always show the same message to avoid
            # revealing whether an email exists.
            if not user:

                flash(
                    "If an account exists for this email, "
                    "a password reset link has been sent.",
                    "success"
                )

                return redirect(
                    url_for("auth.forgot_password")
                )

            # Google-only accounts do not have a local password.
            if not user["password_hash"]:

                flash(
                    "This account uses Google login. "
                    "Please continue with Google.",
                    "error"
                )

                return redirect(
                    url_for("auth.forgot_password")
                )

            # Invalidate previous unused reset tokens.
            cursor.execute(
                """
                UPDATE password_reset_tokens
                SET used_at = NOW()
                WHERE user_id = %s
                AND used_at IS NULL
                """,
                (user["id"],)
            )

            # Generate a cryptographically secure token.
            raw_token = secrets.token_urlsafe(48)

            token_hash = hashlib.sha256(
                raw_token.encode("utf-8")
            ).hexdigest()

            expires_at = (
                datetime.now()
                + timedelta(hours=1)
            )

            cursor.execute(
                """
                INSERT INTO password_reset_tokens
                (
                    user_id,
                    token_hash,
                    expires_at
                )
                VALUES (%s, %s, %s)
                """,
                (
                    user["id"],
                    token_hash,
                    expires_at
                )
            )

            connection.commit()

            reset_url = url_for(
                "auth.reset_password",
                token=raw_token,
                _external=True
            )

            email_sent = send_password_reset_email(
                user["email"],
                user["name"],
                reset_url
            )

            if not email_sent:

                flash(
                    "Unable to send the reset email. "
                    "Please try again later.",
                    "error"
                )

                return redirect(
                    url_for("auth.forgot_password")
                )

            flash(
                "If an account exists for this email, "
                "a password reset link has been sent.",
                "success"
            )

            return redirect(
                url_for("auth.forgot_password")
            )

        except Exception as error:

            if connection:
                connection.rollback()

            print(
                "Forgot password error:",
                error
            )

            flash(
                "Something went wrong. Please try again.",
                "error"
            )

            return redirect(
                url_for("auth.forgot_password")
            )

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template(
        "auth/forgot_password.html"
    )


# ============================================================
# SEND PASSWORD RESET EMAIL
# ============================================================

def send_password_reset_email(
    recipient_email,
    recipient_name,
    reset_url
):

    try:

        message = EmailMessage()

        message["Subject"] = (
            "Reset Your LifeOS Password"
        )

        message["From"] = Config.MAIL_USERNAME

        message["To"] = recipient_email

        message.set_content(
            f"""
Hello {recipient_name},

We received a request to reset your LifeOS password.

Use the link below to create a new password:

{reset_url}

This link will expire in 1 hour.

If you did not request a password reset,
you can safely ignore this email.

Regards,
LifeOS Team
"""
        )

        with smtplib.SMTP(
            Config.MAIL_SERVER,
            Config.MAIL_PORT
        ) as smtp:

            smtp.ehlo()

            if Config.MAIL_USE_TLS:

                smtp.starttls()

                smtp.ehlo()

            smtp.login(
                Config.MAIL_USERNAME,
                Config.MAIL_PASSWORD
            )

            smtp.send_message(
                message
            )

        return True

    except Exception as error:

        print(
            "Password reset email error:",
            error
        )

        return False


# ============================================================
# RESET PASSWORD
# ============================================================

@auth.route(
    "/reset-password/<token>",
    methods=["GET", "POST"]
)
def reset_password(token):

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                expires_at,
                used_at
            FROM password_reset_tokens
            WHERE token_hash = %s
            LIMIT 1
            """,
            (token_hash,)
        )

        reset_record = cursor.fetchone()

        if not reset_record:

            flash(
                "This password reset link is invalid.",
                "error"
            )

            return redirect(
                url_for("auth.forgot_password")
            )

        if reset_record["used_at"] is not None:

            flash(
                "This password reset link has already been used.",
                "error"
            )

            return redirect(
                url_for("auth.forgot_password")
            )

        if reset_record["expires_at"] < datetime.now():

            flash(
                "This password reset link has expired.",
                "error"
            )

            return redirect(
                url_for("auth.forgot_password")
            )

        if request.method == "POST":

            password = request.form.get(
                "password",
                ""
            )

            confirm_password = request.form.get(
                "confirm_password",
                ""
            )

            if not password or not confirm_password:

                flash(
                    "Both password fields are required.",
                    "error"
                )

                return render_template(
                    "auth/reset_password.html"
                )

            if password != confirm_password:

                flash(
                    "Passwords do not match.",
                    "error"
                )

                return render_template(
                    "auth/reset_password.html"
                )

            if len(password) < 8:

                flash(
                    "Password must contain at least 8 characters.",
                    "error"
                )

                return render_template(
                    "auth/reset_password.html"
                )

            password_hash = generate_password_hash(
                password
            )

            cursor.execute(
                """
                UPDATE users
                SET password_hash = %s
                WHERE id = %s
                """,
                (
                    password_hash,
                    reset_record["user_id"]
                )
            )

            cursor.execute(
                """
                UPDATE password_reset_tokens
                SET used_at = NOW()
                WHERE id = %s
                """,
                (reset_record["id"],)
            )

            connection.commit()

            flash(
                "Your password has been reset successfully. "
                "Please login.",
                "success"
            )

            return redirect(
                url_for("auth.login")
            )

        return render_template(
            "auth/reset_password.html"
        )

    except Exception as error:

        if connection:
            connection.rollback()

        print(
            "Reset password error:",
            error
        )

        flash(
            "Something went wrong. Please try again.",
            "error"
        )

        return redirect(
            url_for("auth.forgot_password")
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# LOGOUT
# ============================================================

@auth.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("auth.login")
    )