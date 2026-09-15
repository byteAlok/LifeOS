from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    flash
)

from database.connection import get_connection


analysis = Blueprint(
    "analysis",
    __name__,
    url_prefix="/decisions"
)


# ============================================================
# DECISION ANALYSIS
# ============================================================

@analysis.route(
    "/<int:decision_id>/analysis"
)
def decision_analysis(decision_id):

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
        # LOAD DECISION OPTIONS
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                option_name AS name,
                description
            FROM decision_options
            WHERE decision_id = %s
            ORDER BY id ASC
            """,
            (decision_id,)
        )

        options = cursor.fetchall()

        # ====================================================
        # LOAD DECISION CRITERIA
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
                "At least two options are required for analysis.",
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
                "Please add criteria before analysis.",
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
                "Criterion importance must total 100% before analysis.",
                "error"
            )

            return redirect(
                url_for(
                    "criteria.manage_criteria",
                    decision_id=decision_id
                )
            )

        # ====================================================
        # LOAD SAVED SCORES
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

        # Create score lookup map.
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
        # CHECK SCORE COMPLETENESS
        # ====================================================

        expected_scores = (
            len(options) *
            len(criteria_list)
        )

        if len(saved_scores) < expected_scores:

            flash(
                "Please complete all option scores before analysis.",
                "error"
            )

            return redirect(
                url_for(
                    "scoring.manage_scoring",
                    decision_id=decision_id
                )
            )

        # ====================================================
        # CALCULATE WEIGHTED SCORES
        # ====================================================

        results = []

        for option in options:

            weighted_score = 0.0

            criterion_results = []

            for criterion in criteria_list:

                key = (
                    option["id"],
                    criterion["id"]
                )

                score = score_map.get(
                    key,
                    0.0
                )

                weight = float(
                    criterion["weight"] or 0
                )

                contribution = (
                    score *
                    weight /
                    100
                )

                weighted_score += contribution

                criterion_results.append(
                    {
                        "name": criterion["name"],
                        "weight": weight,
                        "score": score,
                        "contribution": round(
                            contribution,
                            2
                        )
                    }
                )

            results.append(
                {
                    "id": option["id"],
                    "name": option["name"],
                    "description": option["description"],
                    "weighted_score": round(
                        weighted_score,
                        2
                    ),
                    "percentage": round(
                        weighted_score * 10,
                        1
                    ),
                    "criteria": criterion_results
                }
            )

        # ====================================================
        # RANK OPTIONS
        # ====================================================

        results.sort(
            key=lambda item: item["weighted_score"],
            reverse=True
        )

        # ====================================================
        # ASSIGN RANKING
        # ====================================================

        for index, result in enumerate(
            results,
            start=1
        ):

            result["rank"] = index

        # ====================================================
        # IDENTIFY WINNER
        # ====================================================

        winner = results[0]

        # ====================================================
        # CALCULATE DIFFERENCE FROM WINNER
        # ====================================================

        for result in results:

            result["difference"] = round(
                winner["weighted_score"] -
                result["weighted_score"],
                2
            )

        # ====================================================
        # RENDER ANALYSIS PAGE
        # ====================================================

        return render_template(
            "analysis.html",
            decision=decision,
            results=results,
            winner=winner,
            total_weight=total_weight
        )

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as error:

        if connection:
            connection.rollback()

        print(
            "Analysis error:",
            error
        )

        flash(
            "Unable to calculate decision analysis.",
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