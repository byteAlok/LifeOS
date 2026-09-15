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


risk_analysis = Blueprint(
    "risk_analysis",
    __name__,
    url_prefix="/decisions"
)


# ============================================================
# RISK ANALYSIS
# ============================================================

@risk_analysis.route(
    "/<int:decision_id>/risk-analysis",
    methods=["GET", "POST"]
)
def manage_risk_analysis(decision_id):

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
                "At least two options are required before risk analysis.",
                "error"
            )

            return redirect(
                url_for(
                    "decisions.add_options",
                    decision_id=decision_id
                )
            )

        # ====================================================
        # LOAD SAVED RISK ASSESSMENTS
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

        saved_risks = cursor.fetchall()

        # Create a lookup map for saved risks.
        risk_map = {}

        for item in saved_risks:

            risk_map[item["option_id"]] = {
                "probability": float(
                    item["probability"] or 0
                ),
                "impact": float(
                    item["impact"] or 0
                ),
                "risk_score": float(
                    item["risk_score"] or 0
                )
            }

        # ====================================================
        # SAVE RISK ASSESSMENTS
        # ====================================================

        if request.method == "POST":

            for option in options:

                probability_field = (
                    f"probability_{option['id']}"
                )

                impact_field = (
                    f"impact_{option['id']}"
                )

                probability_value = request.form.get(
                    probability_field,
                    ""
                ).strip()

                impact_value = request.form.get(
                    impact_field,
                    ""
                ).strip()

                # Every option must have
                # probability and impact.
                if (
                    probability_value == ""
                    or impact_value == ""
                ):

                    flash(
                        "Please complete probability and impact for every option.",
                        "error"
                    )

                    return redirect(
                        url_for(
                            "risk_analysis.manage_risk_analysis",
                            decision_id=decision_id
                        )
                    )

                # Convert values to numbers.
                try:

                    probability = float(
                        probability_value
                    )

                    impact = float(
                        impact_value
                    )

                except (
                    ValueError,
                    TypeError
                ):

                    flash(
                        "Probability and impact must be valid numbers.",
                        "error"
                    )

                    return redirect(
                        url_for(
                            "risk_analysis.manage_risk_analysis",
                            decision_id=decision_id
                        )
                    )

                # ====================================================
                # VALIDATE PROBABILITY AND IMPACT
                # ====================================================

                if (
                    probability < 0
                    or probability > 100
                    or impact < 0
                    or impact > 10
                ):

                    flash(
                        "Probability must be 0-100 and impact must be 0-10.",
                        "error"
                    )

                    return redirect(
                        url_for(
                            "risk_analysis.manage_risk_analysis",
                            decision_id=decision_id
                        )
                    )

                # ====================================================
                # CALCULATE NORMALIZED RISK SCORE
                # ====================================================

                risk_score = (
                    probability *
                    impact
                ) / 10

                # Keep the value within 0-100.
                risk_score = max(
                    0,
                    min(
                        risk_score,
                        100
                    )
                )

                # ====================================================
                # INSERT OR UPDATE RISK ASSESSMENT
                # ====================================================

                cursor.execute(
                    """
                    INSERT INTO risk_assessments
                    (
                        decision_id,
                        option_id,
                        probability,
                        impact,
                        risk_score
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        probability = VALUES(probability),
                        impact = VALUES(impact),
                        risk_score = VALUES(risk_score)
                    """,
                    (
                        decision_id,
                        option["id"],
                        probability,
                        impact,
                        risk_score
                    )
                )

            # Commit all risk assessments together.
            connection.commit()

            flash(
                "Risk assessments saved successfully.",
                "success"
            )

            # Move to risk-adjusted analysis.
            return redirect(
                url_for(
                    "risk_adjusted.manage_risk_adjusted",
                    decision_id=decision_id
                )
            )

        # ====================================================
        # ADD SAVED RISK DATA TO OPTIONS
        # ====================================================

        for option in options:

            risk = risk_map.get(
                option["id"]
            )

            if risk:

                option["probability"] = (
                    risk["probability"]
                )

                option["impact"] = (
                    risk["impact"]
                )

                option["risk_score"] = (
                    risk["risk_score"]
                )

            else:

                option["probability"] = None
                option["impact"] = None
                option["risk_score"] = None

        # ====================================================
        # RENDER RISK ANALYSIS PAGE
        # ====================================================

        return render_template(
            "risk_analysis.html",
            decision=decision,
            options=options
        )

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as error:

        if connection:
            connection.rollback()

        print(
            "Risk analysis error:",
            error
        )

        flash(
            "Unable to load risk analysis.",
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