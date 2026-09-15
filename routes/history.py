from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    request,
    flash
)

from database.connection import get_connection


history = Blueprint(
    "history",
    __name__,
    url_prefix="/history"
)


# ============================================================
# DECISION HISTORY
# ============================================================

@history.route("/")
def decision_history():

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
        # GET FILTER PARAMETERS
        # ====================================================

        search = request.args.get(
            "search",
            ""
        ).strip()

        status = request.args.get(
            "status",
            "all"
        ).strip().lower()

        category = request.args.get(
            "category",
            "all"
        ).strip()

        # Accept only supported status values.
        allowed_statuses = {
            "all",
            "completed",
            "in_progress"
        }

        if status not in allowed_statuses:
            status = "all"

        # ====================================================
        # BUILD DECISION HISTORY QUERY
        # ====================================================

        query = """
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
        """

        params = [
            user_id
        ]

        # ====================================================
        # SEARCH FILTER
        # ====================================================

        if search:

            query += """
                AND (
                    title LIKE %s
                    OR description LIKE %s
                    OR category LIKE %s
                )
            """

            search_value = (
                f"%{search}%"
            )

            params.extend(
                [
                    search_value,
                    search_value,
                    search_value
                ]
            )

        # ====================================================
        # STATUS FILTER
        # ====================================================

        if status == "completed":

            query += """
                AND status = 'completed'
            """

        elif status == "in_progress":

            query += """
                AND (
                    status <> 'completed'
                    OR status IS NULL
                )
            """

        # ====================================================
        # CATEGORY FILTER
        # ====================================================

        if category != "all":

            query += """
                AND category = %s
            """

            params.append(
                category
            )

        # ====================================================
        # SORT BY MOST RECENT
        # ====================================================

        query += """
            ORDER BY created_at DESC
        """

        cursor.execute(
            query,
            tuple(params)
        )

        decisions = cursor.fetchall()

        # ====================================================
        # LOAD AVAILABLE CATEGORIES
        # ====================================================

        cursor.execute(
            """
            SELECT DISTINCT
                category
            FROM decisions
            WHERE user_id = %s
            AND category IS NOT NULL
            AND category <> ''
            ORDER BY category ASC
            """,
            (user_id,)
        )

        category_rows = cursor.fetchall()

        categories = [
            row["category"]
            for row in category_rows
        ]

        # ====================================================
        # DECISION STATISTICS
        # ====================================================

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
                        WHEN status <> 'completed'
                        OR status IS NULL
                        THEN 1
                        ELSE 0
                    END
                ) AS in_progress

            FROM decisions
            WHERE user_id = %s
            """,
            (user_id,)
        )

        stats = cursor.fetchone()

        total = int(
            stats["total"] or 0
        )

        completed = int(
            stats["completed"] or 0
        )

        in_progress = int(
            stats["in_progress"] or 0
        )

        # ====================================================
        # RENDER HISTORY PAGE
        # ====================================================

        return render_template(
            "history.html",

            decisions=decisions,

            categories=categories,

            search=search,

            selected_status=status,

            selected_category=category,

            total=total,

            completed=completed,

            in_progress=in_progress
        )

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as error:

        if connection:
            connection.rollback()

        print(
            "Decision history error:",
            error
        )

        flash(
            "Unable to load decision history.",
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