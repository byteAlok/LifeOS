document.addEventListener("DOMContentLoaded", function () {

    const alerts = document.querySelectorAll(".alert");

    alerts.forEach(function (alert) {

        setTimeout(function () {

            alert.classList.add("alert-hide");

            setTimeout(function () {
                alert.remove();
            }, 400);

        }, 2000);

    });

});