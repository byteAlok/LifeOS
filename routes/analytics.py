from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    flash
)

from database.connection import get_connection


analytics = Blueprint(
    "analytics",
    __name__,
    url_prefix="/analytics"
)


# ============================================================
# ANALYTICS DASHBOARD
# ============================================================

@analytics.route("/")
def dashboard():

    # User must be logged in.
    if "user_id" not in session:
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

        user_id = session["user_id"]

        # ====================================================
        # OVERALL DECISION STATISTICS
        # ====================================================

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_decisions,

                SUM(
                    CASE
                        WHEN status = 'completed'
                        THEN 1
                        ELSE 0
                    END
                ) AS completed_decisions,

                SUM(
                    CASE
                        WHEN status <> 'completed'
                        OR status IS NULL
                        THEN 1
                        ELSE 0
                    END
                ) AS in_progress_decisions,

                COALESCE(
                    AVG(
                        CASE
                            WHEN status = 'completed'
                            THEN confidence_score
                        END
                    ),
                    0
                ) AS average_confidence,

                COALESCE(
                    AVG(
                        CASE
                            WHEN status = 'completed'
                            THEN final_score
                        END
                    ),
                    0
                ) AS average_final_score

            FROM decisions
            WHERE user_id = %s
            """,
            (user_id,)
        )

        overview = cursor.fetchone()

        total_decisions = int(
            overview["total_decisions"] or 0
        )

        completed_decisions = int(
            overview["completed_decisions"] or 0
        )

        in_progress_decisions = int(
            overview["in_progress_decisions"] or 0
        )

        average_confidence = float(
            overview["average_confidence"] or 0
        )

        average_final_score = float(
            overview["average_final_score"] or 0
        )

        # ====================================================
        # COMPLETION RATE
        # ====================================================

        if total_decisions > 0:

            completion_rate = (
                completed_decisions /
                total_decisions
            ) * 100

        else:

            completion_rate = 0

        completion_rate = round(
            completion_rate,
            1
        )

        # ====================================================
        # DECISIONS BY CATEGORY
        # ====================================================

        cursor.execute(
            """
            SELECT
                category,
                COUNT(*) AS decision_count
            FROM decisions
            WHERE user_id = %s
            GROUP BY category
            ORDER BY decision_count DESC
            """,
            (user_id,)
        )

        category_rows = cursor.fetchall()

        category_labels = []
        category_values = []

        for row in category_rows:

            category_name = (
                row["category"]
                if row["category"]
                else "Uncategorized"
            )

            category_labels.append(
                category_name
            )

            category_values.append(
                int(
                    row["decision_count"] or 0
                )
            )

        # ====================================================
        # RECENT DECISION ACTIVITY
        # ====================================================

        # Fetch the latest 30 activity dates.
        cursor.execute(
            """
            SELECT
                DATE(created_at) AS decision_date,
                COUNT(*) AS decision_count
            FROM decisions
            WHERE user_id = %s
            GROUP BY DATE(created_at)
            ORDER BY decision_date DESC
            LIMIT 30
            """,
            (user_id,)
        )

        activity_rows = cursor.fetchall()

        # Reverse the rows so the chart displays
        # activity from oldest to newest.
        activity_rows.reverse()

        activity_labels = []
        activity_values = []

        for row in activity_rows:

            decision_date = row["decision_date"]

            if decision_date:

                activity_labels.append(
                    decision_date.strftime("%d %b")
                )

            else:

                activity_labels.append(
                    "Unknown"
                )

            activity_values.append(
                int(
                    row["decision_count"] or 0
                )
            )

        # ====================================================
        # COMPLETED DECISION PERFORMANCE
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                title,
                category,
                final_score,
                confidence_score,
                created_at
            FROM decisions
            WHERE user_id = %s
            AND status = 'completed'
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (user_id,)
        )

        completed_list = cursor.fetchall()

        # ====================================================
        # HIGHEST AND LOWEST COMPLETED SCORES
        # ====================================================

        highest_score = None
        lowest_score = None

        if completed_list:

            completed_scores = [
                float(
                    item["final_score"] or 0
                )
                for item in completed_list
            ]

            highest_score = round(
                max(completed_scores),
                2
            )

            lowest_score = round(
                min(completed_scores),
                2
            )

        # ====================================================
        # RISK OVERVIEW
        # ====================================================

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_risks,

                COALESCE(
                    AVG(risk_score),
                    0
                ) AS average_risk

            FROM risk_assessments r

            INNER JOIN decisions d
                ON r.decision_id = d.id

            WHERE d.user_id = %s
            """,
            (user_id,)
        )

        risk_overview = cursor.fetchone()

        total_risks = int(
            risk_overview["total_risks"] or 0
        )

        average_risk = float(
            risk_overview["average_risk"] or 0
        )

        average_risk = round(
            average_risk,
            2
        )

        # ====================================================
        # DECISION HEALTH INSIGHT
        # ====================================================

        if total_decisions == 0:

            insight_title = (
                "Start structuring your first decision."
            )

            insight_text = (
                "Create a decision and compare alternatives "
                "to begin building your LifeOS decision history."
            )

        elif completed_decisions == 0:

            insight_title = (
                "Your decision history needs analysis."
            )

            insight_text = (
                "You have decisions recorded, but none have "
                "completed the full LifeOS analysis pipeline yet."
            )

        elif average_confidence < 20:

            insight_title = (
                "Your recommendations are relatively close."
            )

            insight_text = (
                "The completed decisions show low score separation "
                "between alternatives. Reviewing criteria weights, "
                "scores, and risk assumptions may improve clarity."
            )

        elif average_confidence < 50:

            insight_title = (
                "Your decisions show moderate separation."
            )

            insight_text = (
                "LifeOS is finding useful differences between "
                "alternatives, although some decisions may still "
                "benefit from reviewing their assumptions."
            )

        else:

            insight_title = (
                "Your decisions show strong separation."
            )

            insight_text = (
                "The analyzed alternatives generally show clear "
                "differences under the assumptions you provided."
            )

        # ====================================================
        # RENDER ANALYTICS PAGE
        # ====================================================

        return render_template(
            "analytics.html",

            total_decisions=total_decisions,
            completed_decisions=completed_decisions,
            in_progress_decisions=in_progress_decisions,

            average_confidence=average_confidence,
            average_final_score=average_final_score,
            completion_rate=completion_rate,

            category_labels=category_labels,
            category_values=category_values,

            activity_labels=activity_labels,
            activity_values=activity_values,

            completed_list=completed_list,

            highest_score=highest_score,
            lowest_score=lowest_score,

            total_risks=total_risks,
            average_risk=average_risk,

            insight_title=insight_title,
            insight_text=insight_text
        )

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as error:

        if connection:
            connection.rollback()

        print(
            "Analytics error:",
            error
        )

        flash(
            "Unable to load analytics.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    # ========================================================
    # CLOSE DATABASE RESOURCES
    # ========================================================

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()