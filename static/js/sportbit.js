"use strict";


/* ============================================================
   PWA
   ============================================================ */

if ("serviceWorker" in navigator) {

    window.addEventListener("load", function () {

        navigator.serviceWorker
            .register("/static/sw.js")

            .then(function (registration) {

                console.log(
                    "SportBit PWA actief:",
                    registration.scope
                );

            })

            .catch(function (error) {

                console.error(
                    "PWA service worker fout:",
                    error
                );

            });

    });

}


/* ============================================================
   BEVESTIGINGEN
   ============================================================ */

document.addEventListener("DOMContentLoaded", function () {

    const forms =
        document.querySelectorAll(
            "form[data-confirm]"
        );


    forms.forEach(function (form) {

        form.addEventListener(
            "submit",
            function (event) {

                const message =
                    form.dataset.confirm;

                if (
                    message &&
                    !window.confirm(message)
                ) {
                    event.preventDefault();
                }

            }
        );

    });


    /* ========================================================
       HAMBURGER MENU
       ======================================================== */

    const menuToggle =
        document.getElementById(
            "menuToggle"
        );

    const mobileMenu =
        document.getElementById(
            "mobileMenu"
        );


    if (!menuToggle || !mobileMenu) {
        return;
    }


    function openMenu() {

        menuToggle.classList.add(
            "is-open"
        );

        mobileMenu.classList.add(
            "is-open"
        );

        menuToggle.setAttribute(
            "aria-expanded",
            "true"
        );

        menuToggle.setAttribute(
            "aria-label",
            "Menu sluiten"
        );

        mobileMenu.setAttribute(
            "aria-hidden",
            "false"
        );

    }


    function closeMenu() {

        menuToggle.classList.remove(
            "is-open"
        );

        mobileMenu.classList.remove(
            "is-open"
        );

        menuToggle.setAttribute(
            "aria-expanded",
            "false"
        );

        menuToggle.setAttribute(
            "aria-label",
            "Menu openen"
        );

        mobileMenu.setAttribute(
            "aria-hidden",
            "true"
        );

    }


    function toggleMenu() {

        const isOpen =
            menuToggle.classList.contains(
                "is-open"
            );

        if (isOpen) {
            closeMenu();
        } else {
            openMenu();
        }

    }


    menuToggle.addEventListener(
        "click",
        toggleMenu
    );


    /* Menu sluiten na klikken op een link */

    mobileMenu
        .querySelectorAll("a")
        .forEach(function (link) {

            link.addEventListener(
                "click",
                closeMenu
            );

        });


    /* Menu sluiten wanneer buiten het menu
       wordt geklikt */

    document.addEventListener(
        "click",
        function (event) {

            if (
                !mobileMenu.contains(event.target) &&
                !menuToggle.contains(event.target)
            ) {
                closeMenu();
            }

        }
    );


    /* Escape sluit het menu */

    document.addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Escape") {
                closeMenu();
            }

        }
    );


    /* Bij teruggaan naar desktop altijd sluiten */

    window.addEventListener(
        "resize",
        function () {

            if (window.innerWidth > 700) {
                closeMenu();
            }

        }
    );

});
