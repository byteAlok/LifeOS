/* =========================================================
   LIFEOS DASHBOARD JAVASCRIPT
   ========================================================= */


/* =========================================================
   NUMBER COUNTERS
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    const counters = document.querySelectorAll(
        ".counter"
    );


    counters.forEach((counter) => {

        const target = Number(
            counter.dataset.value || 0
        );

        let current = 0;

        const duration = 700;

        const startTime = performance.now();


        function animateCounter(currentTime) {

            const elapsed =
                currentTime - startTime;

            const progress =
                Math.min(elapsed / duration, 1);

            const eased =
                1 - Math.pow(1 - progress, 3);

            current =
                Math.floor(target * eased);

            counter.textContent = current;


            if (progress < 1) {

                requestAnimationFrame(
                    animateCounter
                );

            } else {

                counter.textContent = target;

            }

        }


        requestAnimationFrame(
            animateCounter
        );

    });

});


/* =========================================================
   PROGRESS BARS
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    const progressBars =
        document.querySelectorAll(
            ".progress-fill"
        );


    progressBars.forEach((bar) => {

        let progress =
            Number(
                bar.dataset.progress || 0
            );


        progress =
            Math.max(
                0,
                Math.min(progress, 100)
            );


        setTimeout(() => {

            bar.style.width =
                `${progress}%`;

        }, 150);

    });

});