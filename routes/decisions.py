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


decisions = Blueprint(
    "decisions",
    __name__,
    url_prefix="/decisions"
)


# ============================================================
# CREATE DECISION
# ============================================================

@decisions.route(
    "/create",
    methods=["GET", "POST"]
)
def create_decision():

    if "user_id" not in session:
        return redirect(
            url_for("auth.login")
        )

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        if not title:

            flash(
                "Decision title is required.",
                "error"
            )

            return redirect(
                url_for(
                    "decisions.create_decision"
                )
            )

        connection = None
        cursor = None

        try:

            connection = get_connection()

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO decisions
                (
                    user_id,
                    title,
                    category,
                    description,
                    status
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    session["user_id"],
                    title,
                    category or None,
                    description or None,
                    "draft"
                )
            )

            connection.commit()

            decision_id = cursor.lastrowid

            return redirect(
                url_for(
                    "decisions.decision_detail",
                    decision_id=decision_id
                )
            )

        except Exception as error:

            if connection:
                connection.rollback()

            print(
                "Create decision error:",
                error
            )

            flash(
                "Unable to create the decision.",
                "error"
            )

            return redirect(
                url_for(
                    "decisions.create_decision"
                )
            )

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template(
        "create_decision.html"
    )


# ============================================================
# DECISION DETAIL
# ============================================================

@decisions.route(
    "/<int:decision_id>"
)
def decision_detail(decision_id):

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

        # ----------------------------------------------------
        # Verify decision ownership
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Load options
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                option_name,
                description,
                created_at
            FROM decision_options
            WHERE decision_id = %s
            ORDER BY id ASC
            """,
            (decision_id,)
        )

        options = cursor.fetchall()

        # ----------------------------------------------------
        # Load criteria
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Load scores
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                option_id,
                criterion_id,
                score
            FROM scores
            WHERE decision_id = %s
            ORDER BY id ASC
            """,
            (decision_id,)
        )

        scores = cursor.fetchall()

        # ----------------------------------------------------
        # Load risk assessments
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                option_id,
                probability,
                impact,
                risk_score
            FROM risk_assessments
            WHERE decision_id = %s
            ORDER BY id ASC
            """,
            (decision_id,)
        )

        risk_assessments = cursor.fetchall()

        # ----------------------------------------------------
        # Basic counts
        # ----------------------------------------------------

        option_count = len(options)

        criteria_count = len(
            criteria_list
        )

        score_count = len(scores)

        risk_count = len(
            risk_assessments
        )

        # ----------------------------------------------------
        # Validate options
        # ----------------------------------------------------

        options_complete = (
            option_count >= 2
        )

        # ----------------------------------------------------
        # Validate criteria
        # ----------------------------------------------------

        total_weight = sum(
            float(
                criterion["weight"] or 0
            )
            for criterion in criteria_list
        )

        criteria_complete = (
            criteria_count > 0
            and abs(total_weight - 100) <= 0.01
        )

        # ----------------------------------------------------
        # Validate scores
        # ----------------------------------------------------

        expected_scores = (
            option_count *
            criteria_count
        )

        scoring_complete = (
            criteria_complete
            and expected_scores > 0
            and score_count >= expected_scores
        )

        # ----------------------------------------------------
        # Validate risks
        # ----------------------------------------------------

        risk_complete = (
            scoring_complete
            and risk_count >= option_count
        )

        # ----------------------------------------------------
        # Determine current workflow stage
        # ----------------------------------------------------

        if not options_complete:

            current_step = "options"

        elif not criteria_complete:

            current_step = "criteria"

        elif not scoring_complete:

            current_step = "scoring"

        elif not risk_complete:

            current_step = "risk"

        else:

            current_step = "risk_adjusted"

        # ----------------------------------------------------
        # Calculate workflow progress
        #
        # Core data pipeline:
        #
        # 20% Decision
        # 40% Options
        # 60% Criteria
        # 70% Scoring
        # 80% Risk
        # Advanced analysis starts after 80%
        # ----------------------------------------------------

        if not options_complete:

            progress = 20

        elif not criteria_complete:

            progress = 40

        elif not scoring_complete:

            progress = 60

        elif not risk_complete:

            progress = 80

        else:

            progress = 80

        # ----------------------------------------------------
        # Advanced workflow availability
        # ----------------------------------------------------

        risk_adjusted_available = (
            risk_complete
        )

        what_if_available = (
            risk_complete
        )

        summary_available = (
            risk_complete
        )

        stability_available = (
            risk_complete
        )

        # ----------------------------------------------------
        # Render page
        # ----------------------------------------------------

        return render_template(
            "decision_detail.html",

            decision=decision,

            options=options,

            criteria_list=criteria_list,

            scores=scores,

            risk_assessments=risk_assessments,

            option_count=option_count,

            criteria_count=criteria_count,

            score_count=score_count,

            risk_count=risk_count,

            current_step=current_step,

            progress=progress,

            options_complete=options_complete,

            criteria_complete=criteria_complete,

            scoring_complete=scoring_complete,

            risk_complete=risk_complete,

            total_weight=total_weight,

            expected_scores=expected_scores,

            risk_adjusted_available=risk_adjusted_available,

            what_if_available=what_if_available,

            summary_available=summary_available,

            stability_available=stability_available
        )

    except Exception as error:

        if connection:
            connection.rollback()

        print(
            "Decision detail error:",
            error
        )

        flash(
            "Unable to load the decision.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# ADD OPTIONS
# ============================================================

@decisions.route(
    "/<int:decision_id>/options",
    methods=["GET", "POST"]
)
def add_options(decision_id):

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

        # ----------------------------------------------------
        # Verify decision ownership
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Add option
        # ----------------------------------------------------

        if request.method == "POST":

            option_name = request.form.get(
                "option_name",
                ""
            ).strip()

            option_description = request.form.get(
                "option_description",
                ""
            ).strip()

            if not option_name:

                flash(
                    "Option name is required.",
                    "error"
                )

                return redirect(
                    url_for(
                        "decisions.add_options",
                        decision_id=decision_id
                    )
                )

            cursor.execute(
                """
                INSERT INTO decision_options
                (
                    decision_id,
                    option_name,
                    description
                )
                VALUES (%s, %s, %s)
                """,
                (
                    decision_id,
                    option_name,
                    option_description or None
                )
            )

            connection.commit()

            flash(
                "Option added successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "decisions.add_options",
                    decision_id=decision_id
                )
            )

        # ----------------------------------------------------
        # Load options
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                option_name,
                description,
                created_at
            FROM decision_options
            WHERE decision_id = %s
            ORDER BY id ASC
            """,
            (decision_id,)
        )

        options = cursor.fetchall()

        return render_template(
            "add_options.html",
            decision=decision,
            options=options
        )

    except Exception as error:

        if connection:
            connection.rollback()

        print(
            "Add options error:",
            error
        )

        flash(
            "Unable to process the option.",
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


# ============================================================
# FINAL DECISION SUMMARY
# ============================================================

@decisions.route(
    "/<int:decision_id>/summary"
)
def decision_summary(decision_id):

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

        # ----------------------------------------------------
        # Verify decision ownership
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Load options
        # ----------------------------------------------------

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

        if len(options) < 2:

            flash(
                "At least two options are required.",
                "error"
            )

            return redirect(
                url_for(
                    "decisions.decision_detail",
                    decision_id=decision_id
                )
            )

        # ----------------------------------------------------
        # Load criteria
        # ----------------------------------------------------

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

        if not criteria_list:

            flash(
                "Criteria are required before generating the summary.",
                "error"
            )

            return redirect(
                url_for(
                    "criteria.manage_criteria",
                    decision_id=decision_id
                )
            )

        # ----------------------------------------------------
        # Validate weights
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Load scores
        # ----------------------------------------------------

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

        expected_scores = (
            len(options) *
            len(criteria_list)
        )

        if len(score_rows) < expected_scores:

            flash(
                "Please complete all scores before viewing the final summary.",
                "error"
            )

            return redirect(
                url_for(
                    "scoring.manage_scoring",
                    decision_id=decision_id
                )
            )

        # ----------------------------------------------------
        # Create score map
        # ----------------------------------------------------

        score_map = {}

        for row in score_rows:

            key = (
                row["option_id"],
                row["criterion_id"]
            )

            score_map[key] = float(
                row["score"] or 0
            )

        # ----------------------------------------------------
        # Calculate weighted scores
        # ----------------------------------------------------

        weighted_results = []

        for option in options:

            weighted_score = 0.0

            for criterion in criteria_list:

                score = score_map.get(
                    (
                        option["id"],
                        criterion["id"]
                    ),
                    0
                )

                weight = float(
                    criterion["weight"] or 0
                )

                weighted_score += (
                    score *
                    weight /
                    100
                )

            weighted_results.append(
                {
                    "id": option["id"],
                    "option_name": option["option_name"],
                    "description": option["description"],
                    "weighted_score": round(
                        weighted_score,
                        2
                    )
                }
            )

        # ----------------------------------------------------
        # Load risk assessments
        # ----------------------------------------------------

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

        risk_map = {}

        for row in risk_rows:

            risk_map[
                row["option_id"]
            ] = {
                "probability": float(
                    row["probability"] or 0
                ),
                "impact": float(
                    row["impact"] or 0
                ),
                "risk_score": float(
                    row["risk_score"] or 0
                )
            }

        # ----------------------------------------------------
        # Calculate final risk-adjusted scores
        # ----------------------------------------------------

        final_results = []

        for result in weighted_results:

            risk = risk_map.get(
                result["id"]
            )

            if not risk:

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

            weighted_score = result[
                "weighted_score"
            ]

            risk_score = risk[
                "risk_score"
            ]

            risk_adjusted_score = (
                weighted_score *
                (
                    1 -
                    (
                        risk_score /
                        100
                    )
                )
            )

            final_results.append(
                {
                    "id": result["id"],
                    "option_name": result["option_name"],
                    "description": result["description"],
                    "weighted_score": round(
                        weighted_score,
                        2
                    ),
                    "probability": risk[
                        "probability"
                    ],
                    "impact": risk[
                        "impact"
                    ],
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

        # ----------------------------------------------------
        # Sort by risk-adjusted score
        # ----------------------------------------------------

        final_results.sort(
            key=lambda item:
                item["risk_adjusted_score"],
            reverse=True
        )

        # ----------------------------------------------------
        # Add ranking
        # ----------------------------------------------------

        for index, result in enumerate(
            final_results,
            start=1
        ):

            result["rank"] = index

        # ----------------------------------------------------
        # Recommended option
        # ----------------------------------------------------

        recommended_option = (
            final_results[0]
        )

        # ----------------------------------------------------
        # Calculate confidence
        # ----------------------------------------------------

        if len(final_results) >= 2:

            top_score = final_results[0][
                "risk_adjusted_score"
            ]

            second_score = final_results[1][
                "risk_adjusted_score"
            ]

            if top_score > 0:

                confidence = (
                    (
                        top_score -
                        second_score
                    )
                    /
                    top_score
                ) * 100

            else:

                confidence = 0

        else:

            confidence = 100

        confidence = max(
            0,
            min(
                100,
                confidence
            )
        )

        # ----------------------------------------------------
        # Decision strength
        # ----------------------------------------------------

        if confidence >= 40:

            decision_strength = "Strong"

        elif confidence >= 20:

            decision_strength = "Moderate"

        else:

            decision_strength = "Close"

        # ----------------------------------------------------
        # Runner-up
        # ----------------------------------------------------

        if len(final_results) >= 2:

            runner_up = final_results[1]

            score_difference = (
                recommended_option[
                    "risk_adjusted_score"
                ]
                -
                runner_up[
                    "risk_adjusted_score"
                ]
            )

        else:

            runner_up = None

            score_difference = 0

        # ----------------------------------------------------
        # Summary metrics
        # ----------------------------------------------------

        option_count = len(
            options
        )

        criteria_count = len(
            criteria_list
        )

        score_count = len(
            score_rows
        )

        risk_count = len(
            risk_rows
        )

        # ----------------------------------------------------
        # Save final result
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE decisions
            SET
                final_score = %s,
                confidence_score = %s,
                status = %s
            WHERE id = %s
            AND user_id = %s
            """,
            (
                recommended_option[
                    "risk_adjusted_score"
                ],
                confidence,
                "completed",
                decision_id,
                session["user_id"]
            )
        )

        connection.commit()

        # ----------------------------------------------------
        # Render final summary
        # ----------------------------------------------------

        return render_template(
            "decision_summary.html",

            decision=decision,

            results=final_results,

            recommended_option=
                recommended_option,

            runner_up=runner_up,

            confidence=round(
                confidence,
                1
            ),

            decision_strength=
                decision_strength,

            score_difference=round(
                score_difference,
                2
            ),

            total_weight=
                total_weight,

            option_count=
                option_count,

            criteria_count=
                criteria_count,

            score_count=
                score_count,

            risk_count=
                risk_count
        )

    except Exception as error:

        if connection:
            connection.rollback()

        print(
            "Decision summary error:",
            error
        )

        flash(
            "Unable to generate the final decision summary.",
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