/* =========================================================
   LifeOS Analytics
   Chart.js Visualizations
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const chartFont = {
        family: "Inter, sans-serif"
    };

    const tooltipSettings = {
        backgroundColor: "#171c34",
        titleColor: "#ffffff",
        bodyColor: "#c7ccda",
        padding: 12,
        cornerRadius: 8,
        displayColors: false
    };


    /* =========================================================
       Read Analytics Data
       ========================================================= */

    const analyticsDataElement =
        document.getElementById("analyticsData");

    if (!analyticsDataElement) {
        return;
    }

    let analyticsData;

    try {

        analyticsData = JSON.parse(
            analyticsDataElement.textContent
        );

    } catch (error) {

        console.error(
            "Unable to read analytics data:",
            error
        );

        return;
    }


    const activityLabels =
        Array.isArray(analyticsData.activityLabels)
            ? analyticsData.activityLabels
            : [];

    const activityValues =
        Array.isArray(analyticsData.activityValues)
            ? analyticsData.activityValues
            : [];

    const categoryLabels =
        Array.isArray(analyticsData.categoryLabels)
            ? analyticsData.categoryLabels
            : [];

    const categoryValues =
        Array.isArray(analyticsData.categoryValues)
            ? analyticsData.categoryValues
            : [];


    /* =========================================================
       Decision Activity Chart
       ========================================================= */

    const activityCanvas =
        document.getElementById("activityChart");

    if (
        activityCanvas &&
        typeof Chart !== "undefined"
    ) {

        const hasActivityData =
            activityLabels.length > 0;

        if (hasActivityData) {

            new Chart(
                activityCanvas,
                {
                    type: "line",

                    data: {
                        labels: activityLabels,

                        datasets: [
                            {
                                label: "Decisions",
                                data: activityValues,

                                borderWidth: 3,
                                tension: 0.4,

                                pointRadius: 4,
                                pointHoverRadius: 6,

                                fill: true,

                                backgroundColor:
                                    "rgba(111, 78, 239, 0.10)",

                                borderColor:
                                    "#6f4eef",

                                pointBackgroundColor:
                                    "#6f4eef",

                                pointBorderColor:
                                    "#ffffff",

                                pointBorderWidth: 2
                            }
                        ]
                    },

                    options: {
                        responsive: true,
                        maintainAspectRatio: false,

                        interaction: {
                            intersect: false,
                            mode: "index"
                        },

                        plugins: {

                            legend: {
                                display: false
                            },

                            tooltip: tooltipSettings
                        },

                        scales: {

                            x: {

                                grid: {
                                    display: false
                                },

                                border: {
                                    display: false
                                },

                                ticks: {

                                    color: "#8b94aa",

                                    font: {
                                        ...chartFont,
                                        size: 10
                                    },

                                    maxRotation: 0
                                }
                            },

                            y: {

                                beginAtZero: true,

                                ticks: {

                                    precision: 0,

                                    color: "#8b94aa",

                                    font: {
                                        ...chartFont,
                                        size: 10
                                    }
                                },

                                grid: {
                                    color: "#edf0f5"
                                },

                                border: {
                                    display: false
                                }
                            }
                        }
                    }
                }
            );

        } else {

            showChartEmptyState(
                activityCanvas,
                "No decision activity available yet."
            );
        }
    }


    /* =========================================================
       Category Distribution Chart
       ========================================================= */

    const categoryCanvas =
        document.getElementById("categoryChart");

    if (
        categoryCanvas &&
        typeof Chart !== "undefined"
    ) {

        const hasCategoryData =
            categoryLabels.length > 0;

        if (hasCategoryData) {

            new Chart(
                categoryCanvas,
                {
                    type: "doughnut",

                    data: {
                        labels: categoryLabels,

                        datasets: [
                            {
                                data: categoryValues,

                                borderWidth: 3,

                                borderColor:
                                    "#ffffff",

                                backgroundColor: [
                                    "#6f4eef",
                                    "#14b88a",
                                    "#f1a900",
                                    "#4f6ee8",
                                    "#ef5366",
                                    "#8b5cf6",
                                    "#14b8a6",
                                    "#64748b"
                                ],

                                hoverOffset: 7
                            }
                        ]
                    },

                    options: {
                        responsive: true,
                        maintainAspectRatio: false,

                        cutout: "68%",

                        plugins: {

                            legend: {
                                position: "bottom",

                                labels: {

                                    color: "#66718b",

                                    padding: 16,

                                    usePointStyle: true,

                                    pointStyle: "circle",

                                    font: {
                                        ...chartFont,
                                        size: 10
                                    }
                                }
                            },

                            tooltip: {

                                ...tooltipSettings,

                                callbacks: {

                                    label: function (context) {

                                        const label =
                                            context.label || "";

                                        const value =
                                            context.parsed || 0;

                                        return (
                                            label +
                                            ": " +
                                            value
                                        );
                                    }
                                }
                            }
                        }
                    }
                }
            );

        } else {

            showChartEmptyState(
                categoryCanvas,
                "No category data available yet."
            );
        }
    }


    /* =========================================================
       Health Progress Bars
       ========================================================= */

    setProgressWidth(
        ".completion-progress",
        "data-value"
    );

    setProgressWidth(
        ".confidence-progress",
        "data-value"
    );

    setProgressWidth(
        ".score-progress",
        "data-value"
    );

    setProgressWidth(
        ".risk-progress-fill",
        "data-value"
    );


    /* =========================================================
       Empty Chart State
       ========================================================= */

    function showChartEmptyState(
        canvas,
        message
    ) {

        const container =
            canvas.closest(".chart-container");

        if (!container) {
            return;
        }

        canvas.style.display = "none";

        const emptyMessage =
            document.createElement("div");

        emptyMessage.className =
            "chart-empty";

        emptyMessage.textContent =
            message;

        container.appendChild(
            emptyMessage
        );
    }


    /* =========================================================
       Progress Bar Helper
       ========================================================= */

    function setProgressWidth(
        selector,
        attributeName
    ) {

        const progressBars =
            document.querySelectorAll(selector);

        progressBars.forEach(function (bar) {

            const value =
                Number(
                    bar.getAttribute(attributeName)
                );

            if (Number.isNaN(value)) {
                return;
            }

            const safeValue =
                Math.min(
                    Math.max(value, 0),
                    100
                );

            bar.style.width =
                `${safeValue}%`;
        });
    }

});