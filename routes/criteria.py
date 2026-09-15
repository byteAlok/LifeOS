from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from database.connection import get_connection


criteria = Blueprint(
    "criteria",
    __name__,
    url_prefix="/decisions"
)


@criteria.route("/<int:decision_id>/criteria", methods=["GET", "POST"])
def manage_criteria(decision_id):

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        # Verify that the decision belongs to the logged-in user.
        cursor.execute(
            """
            SELECT
                id,
                title,
                category,
                description
            FROM decisions
            WHERE id = %s
            AND user_id = %s
            """,
            (
                decision_id,
                session["user_id"]
            )
        )

        decision = cursor.fetchone()

        if not decision:
            flash(
                "Decision not found.",
                "error"
            )

            return redirect(
                url_for("dashboard")
            )

        if request.method == "POST":

            name = request.form.get(
                "name",
                ""
            ).strip()

            description = request.form.get(
                "description",
                ""
            ).strip()

            weight = request.form.get(
                "weight",
                "0"
            ).strip()

            if not name:
                flash(
                    "Criterion name is required.",
                    "error"
                )

                return redirect(
                    url_for(
                        "criteria.manage_criteria",
                        decision_id=decision_id
                    )
                )

            try:
                weight_value = float(weight)
            except ValueError:
                weight_value = -1

            if weight_value < 0 or weight_value > 100:
                flash(
                    "Weight must be between 0 and 100.",
                    "error"
                )

                return redirect(
                    url_for(
                        "criteria.manage_criteria",
                        decision_id=decision_id
                    )
                )

            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(weight), 0) AS total_weight
                FROM criteria
                WHERE decision_id = %s
                """,
                (decision_id,)
            )

            result = cursor.fetchone()

            current_total = float(
                result["total_weight"] or 0
            )

            if current_total + weight_value > 100:
                flash(
                    "Total criterion weight cannot exceed 100%.",
                    "error"
                )

                return redirect(
                    url_for(
                        "criteria.manage_criteria",
                        decision_id=decision_id
                    )
                )

            cursor.execute(
                """
                INSERT INTO criteria
                (
                    decision_id,
                    name,
                    description,
                    weight
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    decision_id,
                    name,
                    description or None,
                    weight_value
                )
            )

            connection.commit()

            flash(
                "Criterion added successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "criteria.manage_criteria",
                    decision_id=decision_id
                )
            )

        cursor.execute(
            """
            SELECT
                id,
                name,
                description,
                weight,
                created_at
            FROM criteria
            WHERE decision_id = %s
            ORDER BY id ASC
            """,
            (decision_id,)
        )

        criteria_list = cursor.fetchall()

        total_weight = sum(
            float(item["weight"] or 0)
            for item in criteria_list
        )

        return render_template(
            "criteria.html",
            decision=decision,
            criteria_list=criteria_list,
            total_weight=total_weight
        )

    except Exception as error:

        if connection:
            connection.rollback()

        print(
            "Criteria error:",
            error
        )

        flash(
            "Unable to load criteria.",
            "error"
        )

        return redirect(
            url_for(
                "decisions.decision_detail",
                decision_id=decision_id
            )
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()