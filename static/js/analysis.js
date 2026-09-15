/* =========================================================
   LifeOS Decision Analysis
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const scoreBars =
        document.querySelectorAll(".score-fill");

    scoreBars.forEach(function (bar) {

        const percentage =
            Number(bar.dataset.percentage);

        if (Number.isNaN(percentage)) {
            return;
        }

        const safePercentage =
            Math.min(
                Math.max(percentage, 0),
                100
            );

        bar.style.width =
            `${safePercentage}%`;

    });

});