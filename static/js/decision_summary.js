document.addEventListener("DOMContentLoaded", function () {

    // Set confidence progress bar width.
    const confidenceBar = document.querySelector(
        ".progress-fill"
    );

    if (confidenceBar) {

        const confidence = Number(
            confidenceBar.dataset.confidence
        );

        const safeConfidence = Math.min(
            Math.max(confidence, 0),
            100
        );

        confidenceBar.style.width =
            `${safeConfidence}%`;
    }


    // Set risk bar widths.
    const riskBars = document.querySelectorAll(
        ".risk-fill"
    );

    riskBars.forEach(function (riskBar) {

        const risk = Number(
            riskBar.dataset.risk
        );

        const safeRisk = Math.min(
            Math.max(risk, 0),
            100
        );

        riskBar.style.width =
            `${safeRisk}%`;
    });

});