document.addEventListener("DOMContentLoaded", function () {

    // Get all scenario option cards.
    const scenarioOptions =
        document.querySelectorAll(".scenario-option");

    // Get action buttons.
    const runButton =
        document.getElementById("runSimulationBtn");

    const resetButton =
        document.getElementById("resetScenarioBtn");

    // Get simulation result elements.
    const resultBox =
        document.getElementById("simulationResult");

    const resultTitle =
        document.getElementById("resultTitle");

    const resultMessage =
        document.getElementById("resultMessage");


    // Set the baseline score bar widths.
    const scoreFills =
        document.querySelectorAll(".score-fill");

    scoreFills.forEach(function (fill) {

        const score =
            parseFloat(fill.dataset.score) || 0;

        const safeScore =
            Math.max(
                0,
                Math.min(100, score)
            );

        fill.style.width =
            `${safeScore}%`;

    });


    // Keep a number inside the allowed range.
    function clamp(value, min, max) {

        return Math.max(
            min,
            Math.min(max, value)
        );

    }


    // Calculate risk using the LifeOS risk formula.
    function calculateRisk(
        probability,
        impact
    ) {

        return (
            probability * impact
        ) / 10;

    }


    // Safely convert an input value to a number.
    function getNumber(input) {

        const value =
            parseFloat(input.value);

        if (Number.isNaN(value)) {

            return 0;

        }

        return value;

    }


    // Run the What-If simulation.
    function runSimulation() {

        let bestOption = null;

        let bestScore = -Infinity;


        scenarioOptions.forEach(function (card) {

            const optionName =
                card.dataset.optionName;


            const scoreInput =
                card.querySelector(
                    ".scenario-score"
                );


            const probabilityInput =
                card.querySelector(
                    ".scenario-probability"
                );


            const impactInput =
                card.querySelector(
                    ".scenario-impact"
                );


            const riskResult =
                card.querySelector(
                    ".risk-result"
                );


            let score =
                getNumber(scoreInput);


            let probability =
                getNumber(probabilityInput);


            let impact =
                getNumber(impactInput);


            // Keep scenario values within valid ranges.
            score =
                clamp(
                    score,
                    0,
                    10
                );


            probability =
                clamp(
                    probability,
                    0,
                    100
                );


            impact =
                clamp(
                    impact,
                    0,
                    10
                );


            // Update inputs with safe values.
            scoreInput.value =
                score;


            probabilityInput.value =
                probability;


            impactInput.value =
                impact;


            // Calculate simulated risk.
            const riskScore =
                calculateRisk(
                    probability,
                    impact
                );


            // Display simulated risk.
            riskResult.textContent =
                riskScore.toFixed(2);


            // Calculate the risk-adjusted score.
            const riskFactor =
                1 -
                (
                    riskScore / 100
                );


            const adjustedScore =
                score *
                riskFactor;


            // Identify the best simulated option.
            if (
                adjustedScore > bestScore
            ) {

                bestScore =
                    adjustedScore;

                bestOption =
                    optionName;

            }

        });


        if (!bestOption) {

            return;

        }


        // Display the simulated recommendation.
        resultTitle.textContent =
            bestOption +
            " performs best in this scenario.";


        resultMessage.textContent =
            "The simulated recommendation is calculated from your changed score, probability, and impact values. Your saved decision remains unchanged.";


        // Show the simulation result.
        resultBox.classList.add(
            "visible"
        );

    }


    // Reset all scenario values to their baseline.
    function resetScenario() {

        scenarioOptions.forEach(function (card) {

            const scoreInput =
                card.querySelector(
                    ".scenario-score"
                );


            const probabilityInput =
                card.querySelector(
                    ".scenario-probability"
                );


            const impactInput =
                card.querySelector(
                    ".scenario-impact"
                );


            const riskResult =
                card.querySelector(
                    ".risk-result"
                );


            scoreInput.value =
                card.dataset.baselineScore;


            probabilityInput.value =
                card.dataset.baselineProbability;


            impactInput.value =
                card.dataset.baselineImpact;


            riskResult.textContent =
                Number(
                    card.dataset.baselineRisk
                ).toFixed(2);

        });


        // Reset result message.
        resultTitle.textContent =
            "Change the assumptions to explore a scenario";


        resultMessage.textContent =
            "LifeOS will compare the simulated values against your current baseline.";


        // Hide the simulation result.
        resultBox.classList.remove(
            "visible"
        );

    }


    // Attach simulation event.
    if (runButton) {

        runButton.addEventListener(
            "click",
            runSimulation
        );

    }


    // Attach reset event.
    if (resetButton) {

        resetButton.addEventListener(
            "click",
            resetScenario
        );

    }

});