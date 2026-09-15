from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    flash
)

from database.connection import get_connection


risk_adjusted = Blueprint(
    "risk_adjusted",
    __name__,
    url_prefix="/decisions"
)


# ============================================================
# RISK-ADJUSTED ANALYSIS
# ============================================================

@risk_adjusted.route(
    "/<int:decision_id>/risk-adjusted"
)
def manage_risk_adjusted(decision_id):

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
        # CHECK MINIMUM OPTIONS
        # ====================================================

        if len(options) < 2:

            flash(
                "At least two options are required.",
                "error"
            )

            return redirect(
                url_for(
                    "decisions.add_options",
                    decision_id=decision_id
                )
            )

        # ====================================================
        # LOAD CRITERIA
        # ====================================================

        cursor.execute(
            """
            SELECT
                id,
                name,
                weight
            FROM criteria
            WHERE decision_id = %s
            ORDER BY id ASC
            """,
            (decision_id,)
        )

        criteria_list = cursor.fetchall()

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
        # VALIDATE CRITERIA WEIGHTS
        # ====================================================

        total_weight = sum(
            float(
                criterion["weight"] or 0
            )
            for criterion in criteria_list
        )

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
        # LOAD SCORES
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

        score_rows = cursor.fetchall()

        # ====================================================
        # CHECK SCORE COMPLETENESS
        # ====================================================

        expected_scores = (
            len(options) *
            len(criteria_list)
        )

        if len(score_rows) < expected_scores:

            flash(
                "Please complete all option scores before risk-adjusted analysis.",
                "error"
            )

            return redirect(
                url_for(
                    "scoring.manage_scoring",
                    decision_id=decision_id
                )
            )

        # ====================================================
        # CREATE SCORE LOOKUP
        # ====================================================

        score_map = {}

        for row in score_rows:

            key = (
                row["option_id"],
                row["criterion_id"]
            )

            score_map[key] = float(
                row["score"] or 0
            )

        # ====================================================
        # CALCULATE WEIGHTED SCORES
        # ====================================================

        weighted_scores = {}

        for option in options:

            option_id = option["id"]

            weighted_score = 0.0

            for criterion in criteria_list:

                criterion_id = criterion["id"]

                key = (
                    option_id,
                    criterion_id
                )

                score = score_map.get(
                    key
                )

                # A score must exist for
                # every option and criterion.
                if score is None:

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

                weight = float(
                    criterion["weight"] or 0
                )

                contribution = (
                    score *
                    weight /
                    100
                )

                weighted_score += contribution

            weighted_scores[option_id] = round(
                weighted_score,
                2
            )

        # ====================================================
        # LOAD RISK ASSESSMENTS
        # ====================================================

        cursor.execute(
            """
            SELECT
                option_id,
                probability,
                impact,
                risk_score
            FROM risk_assessments
            WHERE decision_id = %s
            """,
            (decision_id,)
        )

        risk_rows = cursor.fetchall()

        # ====================================================
        # CREATE RISK LOOKUP
        # ====================================================

        risk_map = {}

        for row in risk_rows:

            option_id = row["option_id"]

            probability = float(
                row["probability"] or 0
            )

            impact = float(
                row["impact"] or 0
            )

            # Recalculate risk score from
            # probability and impact.
            calculated_risk_score = (
                probability *
                impact /
                10
            )

            # Keep risk score within 0-100.
            calculated_risk_score = max(
                0,
                min(
                    calculated_risk_score,
                    100
                )
            )

            risk_map[option_id] = {
                "probability": probability,
                "impact": impact,
                "risk_score": calculated_risk_score
            }

        # ====================================================
        # VALIDATE RISK DATA
        # ====================================================

        for option in options:

            if option["id"] not in risk_map:

                flash(
                    "Risk assessment is missing for one or more options.",
                    "error"
                )

                return redirect(
                    url_for(
                        "risk_analysis.manage_risk_analysis",
                        decision_id=decision_id
                    )
                )

        # ====================================================
        # CALCULATE RISK-ADJUSTED SCORES
        # ====================================================

        results = []

        for option in options:

            option_id = option["id"]

            weighted_score = weighted_scores.get(
                option_id,
                0.0
            )

            risk = risk_map[option_id]

            probability = risk["probability"]

            impact = risk["impact"]

            risk_score = risk["risk_score"]

            # Convert risk score into
            # a remaining score factor.
            risk_factor = (
                1 -
                (
                    risk_score /
                    100
                )
            )

            # Apply risk adjustment.
            risk_adjusted_score = (
                weighted_score *
                risk_factor
            )

            # Keep final score between 0 and 10.
            risk_adjusted_score = max(
                0,
                min(
                    risk_adjusted_score,
                    10
                )
            )

            results.append(
                {
                    "id": option_id,
                    "option_name": option["option_name"],
                    "description": option["description"],
                    "weighted_score": round(
                        weighted_score,
                        2
                    ),
                    "probability": round(
                        probability,
                        1
                    ),
                    "impact": round(
                        impact,
                        1
                    ),
                    "risk_score": round(
                        risk_score,
                        2
                    ),
                    "risk_adjusted_score": round(
                        risk_adjusted_score,
                        2
                    )
                }
            )

        # ====================================================
        # SORT BY RISK-ADJUSTED SCORE
        # ====================================================

        results.sort(
            key=lambda item: item[
                "risk_adjusted_score"
            ],
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
        # IDENTIFY RECOMMENDED OPTION
        # ====================================================

        recommended_option = results[0]

        # ====================================================
        # RENDER RISK-ADJUSTED PAGE
        # ====================================================

        return render_template(
            "risk_adjusted.html",
            decision=decision,
            results=results,
            recommended_option=recommended_option
        )

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as error:

        if connection:
            connection.rollback()

        print(
            "Risk-adjusted analysis error:",
            error
        )

        flash(
            "Unable to calculate risk-adjusted analysis.",
            "error"
        )

        return redirect(
            url_for(
                "risk_analysis.manage_risk_analysis",
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