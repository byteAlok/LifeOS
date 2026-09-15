/* =========================================================
   LifeOS Risk-Adjusted Analysis
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const scoreBars =
        document.querySelectorAll(".score-fill");

    scoreBars.forEach(function (bar) {

        const score =
            Number(bar.dataset.score);

        if (Number.isNaN(score)) {
            return;
        }

        const percentage =
            score * 10;

        const safePercentage =
            Math.min(
                Math.max(percentage, 0),
                100
            );

        bar.style.width =
            `${safePercentage}%`;

    });

});