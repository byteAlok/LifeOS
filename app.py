from flask import Flask, redirect, url_for, session, render_template

from config import Config
from database.connection import get_connection

from routes.auth import auth
from routes.oauth import google_auth, register_google
from routes.decisions import decisions
from routes.criteria import criteria
from routes.scoring import scoring
from routes.analysis import analysis
from routes.risk_analysis import risk_analysis
from routes.risk_adjusted import risk_adjusted
from routes.what_if import what_if
from routes.analytics import analytics
from routes.history import history
from routes.sensitivity import sensitivity


app = Flask(__name__)

app.config.from_object(Config)


# ============================================================
# REGISTER BLUEPRINTS
# ============================================================

app.register_blueprint(auth)

register_google(app)

app.register_blueprint(google_auth)
app.register_blueprint(decisions)
app.register_blueprint(criteria)
app.register_blueprint(scoring)
app.register_blueprint(analysis)
app.register_blueprint(risk_analysis)
app.register_blueprint(risk_adjusted)
app.register_blueprint(what_if)
app.register_blueprint(analytics)
app.register_blueprint(history)
app.register_blueprint(sensitivity)


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    if "user_id" in session:
        return redirect(
            url_for("auth.login")
        )

    return redirect(
        url_for("auth.register")
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(
            url_for("auth.login")
        )

    user_id = session["user_id"]

    connection = None
    cursor = None

    stats = {
        "total": 0,
        "completed": 0,
        "in_progress": 0,
        "average_confidence": 0
    }

    recent_decisions = []

    try:

        connection = get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        # Get overall decision statistics.
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,

                SUM(
                    CASE
                        WHEN status = 'completed'
                        THEN 1
                        ELSE 0
                    END
                ) AS completed,

                SUM(
                    CASE
                        WHEN status != 'completed'
                        OR status IS NULL
                        THEN 1
                        ELSE 0
                    END
                ) AS in_progress,

                COALESCE(
                    ROUND(
                        AVG(confidence_score),
                        1
                    ),
                    0
                ) AS average_confidence

            FROM decisions

            WHERE user_id = %s
            """,
            (user_id,)
        )

        stats_result = cursor.fetchone()

        if stats_result:

            stats["total"] = (
                stats_result["total"] or 0
            )

            stats["completed"] = (
                stats_result["completed"] or 0
            )

            stats["in_progress"] = (
                stats_result["in_progress"] or 0
            )

            stats["average_confidence"] = (
                stats_result["average_confidence"] or 0
            )

        # Get recent decisions.
        cursor.execute(
            """
            SELECT
                id,
                title,
                category,
                description,
                status,
                final_score,
                confidence_score,
                created_at

            FROM decisions

            WHERE user_id = %s

            ORDER BY created_at DESC

            LIMIT 8
            """,
            (user_id,)
        )

        recent_decisions = cursor.fetchall()

    except Exception as error:

        print(
            "Dashboard error:",
            error
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()

    return render_template(
        "dashboard.html",
        user_name=session.get("user_name"),
        user_email=session.get("user_email"),
        stats=stats,
        recent_decisions=recent_decisions
    )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )