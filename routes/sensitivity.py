from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    flash
)

from database.connection import get_connection


sensitivity = Blueprint(
    "sensitivity",
    __name__,
    url_prefix="/decisions"
)


# ============================================================
# CALCULATE DECISION SCORES
# ============================================================

def calculate_decision_scores(
    options,
    criteria_list,
    score_map,
    risk_map
):
    """
    Calculate weighted and risk-adjusted scores
    for all decision options.
    """

    results = []

    for option in options:

        weighted_score = 0.0

        for criterion in criteria_list:

            key = (
                option["id"],
                criterion["id"]
            )

            score = float(
                score_map.get(
                    key,
                    0
                )
            )

            weight = float(
                criterion["weight"] or 0
            )

            weighted_score += (
                score *
                weight /
                100
            )

        risk_score = float(
            risk_map.get(
                option["id"],
                0
            )
        )

        # Apply risk adjustment.
        risk_adjusted_score = (
            weighted_score *
            (
                1 -
                risk_score /
                100
            )
        )

        # Keep scores within the valid 0-10 range.
        weighted_score = max(
            0.0,
            min(
                weighted_score,
                10.0
            )
        )

        risk_adjusted_score = max(
            0.0,
            min(
                risk_adjusted_score,
                10.0
            )
        )

        results.append(
            {
                "id": option["id"],
                "name": option["name"],
                "weighted_score": round(
                    weighted_score,
                    2
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

    # Rank from highest to lowest
    # risk-adjusted score.
    results.sort(
        key=lambda item: item[
            "risk_adjusted_score"
        ],
        reverse=True
    )

    for index, result in enumerate(
        results,
        start=1
    ):

        result["rank"] = index

    return results


# ============================================================
# DECISION SENSITIVITY ANALYSIS
# ============================================================

@sensitivity.route(
    "/<int:decision_id>/sensitivity"
)
def decision_sensitivity(decision_id):

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
                user_id
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
        # CHECK OPTIONS
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
                "Please add criteria before sensitivity analysis.",
                "error"
            )

            return redirect(
                url_for(
                    "criteria.manage_criteria",
                    decision_id=decision_id
                )
            )

        # ====================================================
        # VALIDATE TOTAL CRITERIA WEIGHT
        # ====================================================

        total_weight = sum(
            float(
                criterion["weight"] or 0
            )
            for criterion in criteria_list
        )

        if abs(total_weight - 100) > 0.01:

            flash(
                "Criterion weights must total 100%.",
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

        saved_scores = cursor.fetchall()

        # Create score lookup.
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

        if len(score_map) < expected_scores:

            flash(
                "Please complete all option scores before sensitivity analysis.",
                "error"
            )

            return redirect(
                url_for(
                    "scoring.manage_scoring",
                    decision_id=decision_id
                )
            )

        # ====================================================
        # VERIFY EVERY SCORE EXISTS
        # ====================================================

        for option in options:

            for criterion in criteria_list:

                key = (
                    option["id"],
                    criterion["id"]
                )

                if key not in score_map:

                    flash(
                        "Please complete all option scores before sensitivity analysis.",
                        "error"
                    )

                    return redirect(
                        url_for(
                            "scoring.manage_scoring",
                            decision_id=decision_id
                        )
                    )

        # ====================================================
        # LOAD RISK ASSESSMENTS
        # ====================================================

        cursor.execute(
            """
            SELECT
                option_id,
                probability,
                impact
            FROM risk_assessments
            WHERE decision_id = %s
            """,
            (decision_id,)
        )

        risk_rows = cursor.fetchall()

        risk_map = {}

        for item in risk_rows:

            option_id = item["option_id"]

            probability = float(
                item["probability"] or 0
            )

            impact = float(
                item["impact"] or 0
            )

            # Recalculate risk score using
            # the LifeOS risk formula.
            risk_score = (
                probability *
                impact /
                10
            )

            risk_score = max(
                0.0,
                min(
                    risk_score,
                    100.0
                )
            )

            risk_map[option_id] = round(
                risk_score,
                2
            )

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
        # CALCULATE BASELINE
        # ====================================================

        baseline = calculate_decision_scores(
            options,
            criteria_list,
            score_map,
            risk_map
        )

        if not baseline:

            flash(
                "Unable to calculate decision baseline.",
                "error"
            )

            return redirect(
                url_for(
                    "decisions.decision_detail",
                    decision_id=decision_id
                )
            )

        baseline_winner = baseline[0]

        current_recommendation = (
            baseline_winner
        )

        # ====================================================
        # SENSITIVITY TEST VALUES
        # ====================================================

        # Each option is tested independently.
        # Database values are never modified.
        change_values = [
            -2.0,
            -1.5,
            -1.0,
            -0.5,
            0.0,
            0.5,
            1.0,
            1.5,
            2.0
        ]

        sensitivity_results = []

        # ====================================================
        # TEST EVERY OPTION
        # ====================================================

        for option in baseline:

            option_tests = []

            original_weighted_score = float(
                option["weighted_score"]
            )

            risk_score = float(
                option["risk_score"]
            )

            for change in change_values:

                # Apply hypothetical change only
                # to the selected option.
                simulated_weighted_score = (
                    original_weighted_score +
                    change
                )

                # Keep score inside 0-10.
                simulated_weighted_score = max(
                    0.0,
                    min(
                        10.0,
                        simulated_weighted_score
                    )
                )

                # Recalculate risk-adjusted score.
                simulated_risk_adjusted = (
                    simulated_weighted_score *
                    (
                        1 -
                        risk_score /
                        100
                    )
                )

                simulated_risk_adjusted = max(
                    0.0,
                    min(
                        10.0,
                        simulated_risk_adjusted
                    )
                )

                simulated_results = []

                for other_option in baseline:

                    if (
                        other_option["id"]
                        == option["id"]
                    ):

                        simulated_score = (
                            simulated_risk_adjusted
                        )

                    else:

                        simulated_score = float(
                            other_option[
                                "risk_adjusted_score"
                            ]
                        )

                    simulated_results.append(
                        {
                            "id":
                                other_option["id"],

                            "name":
                                other_option["name"],

                            "risk_adjusted_score":
                                simulated_score
                        }
                    )

                # Rank simulated results.
                simulated_results.sort(
                    key=lambda item:
                    item[
                        "risk_adjusted_score"
                    ],
                    reverse=True
                )

                simulated_winner = (
                    simulated_results[0]
                )

                recommendation_changed = (
                    simulated_winner["id"]
                    != current_recommendation["id"]
                )

                option_tests.append(
                    {
                        "change": change,

                        "weighted_score":
                            round(
                                simulated_weighted_score,
                                2
                            ),

                        "risk_adjusted_score":
                            round(
                                simulated_risk_adjusted,
                                2
                            ),

                        "recommendation":
                            simulated_winner["name"],

                        "changed":
                            recommendation_changed
                    }
                )

            # ====================================================
            # FIND CLOSEST RECOMMENDATION SWITCH
            # ====================================================

            option_switches = [
                test
                for test in option_tests
                if test["changed"]
            ]

            option_switches.sort(
                key=lambda test:
                abs(
                    test["change"]
                )
            )

            if option_switches:

                option_closest_switch = abs(
                    option_switches[0]["change"]
                )

            else:

                option_closest_switch = None

            # ====================================================
            # DETERMINE OPTION STABILITY
            # ====================================================

            if option_closest_switch is None:

                option_stability = "Stable"

            elif option_closest_switch <= 0.5:

                option_stability = "Fragile"

            elif option_closest_switch <= 1.0:

                option_stability = "Moderate"

            else:

                option_stability = "Stable"

            sensitivity_results.append(
                {
                    "id":
                        option["id"],

                    "name":
                        option["name"],

                    "baseline_weighted":
                        option["weighted_score"],

                    "baseline_risk":
                        option["risk_score"],

                    "baseline_risk_adjusted":
                        option[
                            "risk_adjusted_score"
                        ],

                    "tests":
                        option_tests,

                    "stability":
                        option_stability,

                    "closest_switch":
                        option_closest_switch
                }
            )

        # ====================================================
        # FIND CLOSEST SWITCH ACROSS ENTIRE DECISION
        # ====================================================

        switch_points = []

        for option_result in sensitivity_results:

            for test in option_result["tests"]:

                if test["changed"]:

                    switch_points.append(
                        {
                            "option":
                                option_result["name"],

                            "change":
                                test["change"],

                            "absolute_change":
                                abs(
                                    test["change"]
                                ),

                            "recommendation":
                                test["recommendation"]
                        }
                    )

        switch_points.sort(
            key=lambda item:
            item["absolute_change"]
        )

        closest_switch = (
            switch_points[0]
            if switch_points
            else None
        )

        if closest_switch:

            overall_switch = float(
                closest_switch[
                    "absolute_change"
                ]
            )

        else:

            overall_switch = None

        # ====================================================
        # DETERMINE OVERALL STABILITY
        # ====================================================

        if overall_switch is None:

            stability = "Stable"

        elif overall_switch <= 0.5:

            stability = "Fragile"

        elif overall_switch <= 1.0:

            stability = "Moderate"

        else:

            stability = "Stable"

        # ====================================================
        # RENDER SENSITIVITY PAGE
        # ====================================================

        return render_template(
            "sensitivity.html",

            decision=decision,

            baseline=baseline,

            baseline_winner=baseline_winner,

            current_recommendation=
                current_recommendation,

            sensitivity_results=
                sensitivity_results,

            stability=stability,

            overall_stability=stability,

            closest_switch=
                closest_switch,

            overall_switch=
                overall_switch,

            change_values=
                change_values
        )

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as error:

        if connection:
            connection.rollback()

        print(
            "Sensitivity analysis error:",
            error
        )

        flash(
            "Unable to calculate decision stability.",
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