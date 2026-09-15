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


scoring = Blueprint(
    "scoring",
    __name__,
    url_prefix="/decisions"
)


# ============================================================
# SCORING
# ============================================================

@scoring.route(
    "/<int:decision_id>/scoring",
    methods=["GET", "POST"]
)
def manage_scoring(decision_id):

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

        # ====================================================
        # VERIFY DECISION OWNERSHIP
        # ====================================================

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

        # ====================================================
        # LOAD OPTIONS
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                option_name,
                description
            FROM decision_options
            WHERE decision_id = %s
            ORDER BY id ASC
            """,
            (decision_id,)
        )

        options = cursor.fetchall()

        # ====================================================
        # LOAD CRITERIA
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                name,
                description,
                weight
            FROM criteria
            WHERE decision_id = %s
            ORDER BY id ASC
            """,
            (decision_id,)
        )

        criteria_list = cursor.fetchall()

        # ====================================================
        # CHECK MINIMUM OPTIONS
        # ====================================================

        if len(options) < 2:

            flash(
                "Please add at least two options before scoring.",
                "error"
            )

            return redirect(
                url_for(
                    "decisions.add_options",
                    decision_id=decision_id
                )
            )

        # ====================================================
        # CHECK CRITERIA
        # ====================================================

        if not criteria_list:

            flash(
                "Please add criteria before scoring.",
                "error"
            )

            return redirect(
                url_for(
                    "criteria.manage_criteria",
                    decision_id=decision_id
                )
            )

        # ====================================================
        # CALCULATE TOTAL CRITERIA WEIGHT
        # ====================================================

        total_weight = sum(
            float(
                criterion["weight"] or 0
            )
            for criterion in criteria_list
        )

        # ====================================================
        # WEIGHTS MUST TOTAL 100%
        # ====================================================

        if abs(total_weight - 100) > 0.01:

            flash(
                "Criterion importance must total 100% before scoring.",
                "error"
            )

            return redirect(
                url_for(
                    "criteria.manage_criteria",
                    decision_id=decision_id
                )
            )

        # ====================================================
        # SAVE SCORES
        # ====================================================

        if request.method == "POST":

            for option in options:

                for criterion in criteria_list:

                    field_name = (
                        f"score_"
                        f"{option['id']}_"
                        f"{criterion['id']}"
                    )

                    score_value = request.form.get(
                        field_name,
                        ""
                    ).strip()

                    # Every score is required.
                    if score_value == "":

                        flash(
                            "Please enter a score for every option and criterion.",
                            "error"
                        )

                        return redirect(
                            url_for(
                                "scoring.manage_scoring",
                                decision_id=decision_id
                            )
                        )

                    # Convert score to float.
                    try:

                        score = float(
                            score_value
                        )

                    except (
                        ValueError,
                        TypeError
                    ):

                        flash(
                            "Every score must be a number between 0 and 10.",
                            "error"
                        )

                        return redirect(
                            url_for(
                                "scoring.manage_scoring",
                                decision_id=decision_id
                            )
                        )

                    # Score must be between 0 and 10.
                    if score < 0 or score > 10:

                        flash(
                            "Scores must be between 0 and 10.",
                            "error"
                        )

                        return redirect(
                            url_for(
                                "scoring.manage_scoring",
                                decision_id=decision_id
                            )
                        )

                    # Insert a new score or update
                    # an existing score.
                    cursor.execute(
                        """
                        INSERT INTO scores
                        (
                            decision_id,
                            option_id,
                            criterion_id,
                            score
                        )
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            score = VALUES(score)
                        """,
                        (
                            decision_id,
                            option["id"],
                            criterion["id"],
                            score
                        )
                    )

            # Save all scores permanently.
            connection.commit()

            flash(
                "Scores saved successfully.",
                "success"
            )

            # Continue to analysis.
            return redirect(
                url_for(
                    "analysis.decision_analysis",
                    decision_id=decision_id
                )
            )

        # ====================================================
        # LOAD PREVIOUSLY SAVED SCORES
        # ====================================================

        cursor.execute(
            """
            SELECT
                option_id,
                criterion_id,
                score
            FROM scores
            WHERE decision_id = %s
            """,
            (decision_id,)
        )

        saved_scores = cursor.fetchall()

        # Create a lookup map:
        # (option_id, criterion_id) -> score
        score_map = {}

        for item in saved_scores:

            key = (
                item["option_id"],
                item["criterion_id"]
            )

            score_map[key] = float(
                item["score"] or 0
            )

        # ====================================================
        # RENDER SCORING PAGE
        # ====================================================

        return render_template(
            "scoring.html",
            decision=decision,
            options=options,
            criteria_list=criteria_list,
            score_map=score_map,
            total_weight=total_weight
        )

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as error:

        if connection:
            connection.rollback()

        print(
            "Scoring error:",
            error
        )

        flash(
            "Unable to load scoring.",
            "error"
        )

        return redirect(
            url_for(
                "decisions.decision_detail",
                decision_id=decision_id
            )
        )

    # ========================================================
    # CLOSE DATABASE RESOURCES
    # ========================================================

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()