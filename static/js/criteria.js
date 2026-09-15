/* =========================================================
   LifeOS Criteria Page
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const progressBar =
        document.querySelector(".progress-fill");

    if (!progressBar) {
        return;
    }

    const totalWeight =
        Number(progressBar.dataset.weight);

    if (Number.isNaN(totalWeight)) {
        return;
    }

    const safeWeight =
        Math.min(
            Math.max(totalWeight, 0),
            100
        );

    progressBar.style.width =
        `${safeWeight}%`;

});