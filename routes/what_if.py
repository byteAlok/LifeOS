from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    flash
)

from database.connection import get_connection


what_if = Blueprint(
    "what_if",
    __name__,
    url_prefix="/decisions"
)


# ============================================================
# WHAT-IF ANALYSIS
# ============================================================

@what_if.route(
    "/<int:decision_id>/what-if",
    methods=["GET"]
)
def what_if_analysis(decision_id):

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
                "At least two options are required before What-If Analysis.",
                "error"
            )

            return redirect(
                url_for(
                    "decisions.add_options",
                    decision_id=decision_id
                )
            )

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
        # CHECK CRITERIA
        # ====================================================

        if not criteria_list:

            flash(
                "Please add criteria before using What-If Analysis.",
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
                "Criterion importance must total 100% before What-If Analysis.",
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

        scores = cursor.fetchall()

        # ====================================================
        # CHECK SCORE COMPLETENESS
        # ====================================================

        expected_scores = (
            len(options) *
            len(criteria_list)
        )

        if len(scores) < expected_scores:

            flash(
                "Please complete all option scores before using What-If Analysis.",
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

        for item in scores:

            key = (
                item["option_id"],
                item["criterion_id"]
            )

            score_map[key] = float(
                item["score"] or 0
            )

        # ====================================================
        # CALCULATE WEIGHTED SCORE
        # ====================================================

        for option in options:

            weighted_score = 0.0

            for criterion in criteria_list:

                key = (
                    option["id"],
                    criterion["id"]
                )

                score = score_map.get(
                    key
                )

                # Every score must exist.
                if score is None:

                    flash(
                        "Please complete all option scores before using What-If Analysis.",
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

            option["weighted_score"] = round(
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

        risks = cursor.fetchall()

        # ====================================================
        # CREATE RISK LOOKUP
        # ====================================================

        risk_map = {}

        for risk in risks:

            option_id = risk["option_id"]

            probability = float(
                risk["probability"] or 0
            )

            impact = float(
                risk["impact"] or 0
            )

            # Recalculate risk score from
            # probability and impact.
            calculated_risk_score = (
                probability *
                impact /
                10
            )

            # Keep risk score between 0 and 100.
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
        # CHECK RISK COMPLETENESS
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
        # ADD RISK INFORMATION TO OPTIONS
        # ====================================================

        for option in options:

            risk = risk_map[
                option["id"]
            ]

            option["probability"] = (
                risk["probability"]
            )

            option["impact"] = (
                risk["impact"]
            )

            option["risk_score"] = (
                risk["risk_score"]
            )

        # ====================================================
        # CALCULATE RISK-ADJUSTED SCORE
        # ====================================================

        for option in options:

            weighted_score = float(
                option["weighted_score"]
            )

            risk_score = float(
                option["risk_score"]
            )

            risk_adjusted_score = (
                weighted_score *
                (
                    1 -
                    risk_score /
                    100
                )
            )

            # Keep final score between 0 and 10.
            risk_adjusted_score = max(
                0,
                min(
                    risk_adjusted_score,
                    10
                )
            )

            option["risk_adjusted_score"] = round(
                risk_adjusted_score,
                2
            )

        # ====================================================
        # RANK OPTIONS
        # ====================================================

        ranked_options = sorted(
            options,
            key=lambda item: item[
                "risk_adjusted_score"
            ],
            reverse=True
        )

        # ====================================================
        # ASSIGN RANK
        # ====================================================

        for index, option in enumerate(
            ranked_options,
            start=1
        ):

            option["rank"] = index

        # ====================================================
        # RENDER WHAT-IF PAGE
        # ====================================================

        return render_template(
            "what_if.html",
            decision=decision,
            options=options,
            criteria_list=criteria_list,
            ranked_options=ranked_options
        )

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as error:

        if connection:
            connection.rollback()

        print(
            "\n========================================"
        )

        print(
            "WHAT-IF ANALYSIS ERROR:"
        )

        print(
            repr(error)
        )

        print(
            "========================================\n"
        )

        flash(
            "Unable to calculate What-If Analysis.",
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