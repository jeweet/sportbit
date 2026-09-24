document.addEventListener("DOMContentLoaded", () => {

    /* =========================================================
       SCROLLPOSITIE BEWAREN BIJ UITSCHRIJVEN / VERWIJDEREN
       ========================================================= */

    document
        .querySelectorAll(".scroll-preserve")
        .forEach((form) => {

            form.addEventListener("submit", () => {

                sessionStorage.setItem(
                    "sportbit-scroll-position",
                    window.scrollY.toString()
                );

            });

        });


    /* Scrollpositie herstellen na pagina-reload */

    const savedScrollPosition =
        sessionStorage.getItem(
            "sportbit-scroll-position"
        );

    if (savedScrollPosition !== null) {

        sessionStorage.removeItem(
            "sportbit-scroll-position"
        );

        const restoreScroll = () => {
            window.scrollTo(
                0,
                Number(savedScrollPosition)
            );
        };

        requestAnimationFrame(() => {
            requestAnimationFrame(restoreScroll);
        });

    }


    /* ========================================================
       HAMBURGER MENU
       ======================================================== */

    const menuToggle =
        document.getElementById("menuToggle");

    const mobileMenu =
        document.getElementById("mobileMenu");

    if (menuToggle && mobileMenu) {

        function openMenu() {
            menuToggle.classList.add("is-open");

            mobileMenu.classList.add("is-open");

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
            menuToggle.classList.remove("is-open");

            mobileMenu.classList.remove("is-open");

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
                menuToggle.classList.contains("is-open");

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


        /* Menu sluiten wanneer buiten het menu wordt geklikt */

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

    }


    /* =========================================================
       MOBIELE KAARTEN IN-/UITKLAPPEN
       ========================================================= */

    document
        .querySelectorAll(".mobile-collapse-toggle")
        .forEach((header) => {

            function toggleCard() {

                const card =
                    header.closest(".card");

                if (!card) {
                    return;
                }

                const collapsed =
                    card.classList.toggle(
                        "mobile-collapsed"
                    );

                header.setAttribute(
                    "aria-expanded",
                    collapsed ? "false" : "true"
                );
            }


            header.addEventListener(
                "click",
                toggleCard
            );


            header.addEventListener(
                "keydown",
                (event) => {

                    if (
                        event.key === "Enter" ||
                        event.key === " "
                    ) {
                        event.preventDefault();
                        toggleCard();
                    }

                }
            );

        });


    /* =========================================================
       LESKEUZE
       ========================================================= */

    const dagSelect =
        document.getElementById("dag");

    const lessonOptions =
        document.getElementById("lesson-options");

    const tijdInput =
        document.getElementById("tijd");

    const lesInput =
        document.getElementById("les");

    const lessonForm =
        document.getElementById("lesson-form");

    const lessenStatus =
        document.getElementById("lessen-status");


    /*
     * Op pagina's zonder leskeuze hoeft
     * de rest van dit script niet uitgevoerd te worden.
     */

    if (
        !dagSelect ||
        !lessonOptions ||
        !tijdInput ||
        !lesInput
    ) {
        return;
    }


    /* =========================================================
       STATUS
       ========================================================= */

    function setStatus(message) {

        if (lessenStatus) {
            lessenStatus.textContent = message;
        }

    }


    /* =========================================================
       LES SELECTEREN
       ========================================================= */

    function selectLesson(button) {

        lessonOptions
            .querySelectorAll(".lesson-option")
            .forEach((option) => {

                option.classList.remove("selected");

                option.setAttribute(
                    "aria-checked",
                    "false"
                );

            });


        button.classList.add("selected");

        button.setAttribute(
            "aria-checked",
            "true"
        );


        /*
         * Dit zijn de waarden die Flask
         * bij submit ontvangt.
         */

        tijdInput.value =
            button.dataset.tijd || "";

        lesInput.value =
            button.dataset.les || "";

    }


    /* =========================================================
       LESBLOK MAKEN
       ========================================================= */

    function createLessonButton(tijd, lesNaam) {

        const button =
            document.createElement("button");


        button.type =
            "button";

        button.className =
            "lesson-option";

        button.dataset.tijd =
            tijd;

        button.dataset.les =
            lesNaam;


        button.setAttribute(
            "role",
            "radio"
        );

        button.setAttribute(
            "aria-checked",
            "false"
        );


        /* Tijd */

        const time =
            document.createElement("span");

        time.className =
            "lesson-option-time";

        time.textContent =
            tijd;


        /* Naam */

        const name =
            document.createElement("span");

        name.className =
            "lesson-option-name";

        name.textContent =
            lesNaam;


        /* Vinkje */

        const check =
            document.createElement("span");

        check.className =
            "lesson-option-check";

        check.textContent =
            "✓";


        button.appendChild(time);

        button.appendChild(name);

        button.appendChild(check);


        /*
         * Bestaande waarde herstellen
         * bij het bewerken van een les.
         */

        if (
            tijdInput.value === tijd &&
            lesInput.value === lesNaam
        ) {

            button.classList.add(
                "selected"
            );

            button.setAttribute(
                "aria-checked",
                "true"
            );

        }


        /* Klik op volledige tegel */

        button.addEventListener(
            "click",
            () => {
                selectLesson(button);
            }
        );


        return button;
    }


    /* =========================================================
       LESSEN LADEN
       ========================================================= */

    async function laadLessen(dag) {

        if (!dag) {
            lessonOptions.innerHTML = "";
            return;
        }


        /*
         * Alleen deze laadstatus tonen.
         */

        lessonOptions.innerHTML = `
            <p class="lesson-choice-message">
                Lessen laden...
            </p>
        `;


        try {

            const response =
                await fetch(
                    `/api/lessen?dag=${encodeURIComponent(dag)}`,
                    {
                        method: "GET",

                        headers: {
                            "Accept": "application/json"
                        },

                        cache: "no-store"
                    }
                );


            if (!response.ok) {

                throw new Error(
                    `HTTP ${response.status}`
                );

            }


            const data =
                await response.json();


            lessonOptions.innerHTML =
                "";


            const lessenPerTijd =
                data.lessen || {};


            /*
             * Tijden chronologisch sorteren.
             */

            const tijden =
                Object.keys(
                    lessenPerTijd
                ).sort((a, b) => {

                    const [ah, am] =
                        a.split(":").map(Number);

                    const [bh, bm] =
                        b.split(":").map(Number);

                    return (
                        ah * 60 +
                        am -
                        (bh * 60 + bm)
                    );

                });


            /*
             * Alle lessen toevoegen.
             */

            tijden.forEach((tijd) => {

                const lessen =
                    lessenPerTijd[tijd];


                if (!Array.isArray(lessen)) {
                    return;
                }


                lessen.forEach((lesNaam) => {

                    const button =
                        createLessonButton(
                            tijd,
                            lesNaam
                        );


                    lessonOptions.appendChild(
                        button
                    );

                });

            });


        } catch (error) {

            console.error(
                "Lessen laden mislukt:",
                error
            );


            /*
             * Alleen deze foutmelding tonen.
             */

            lessonOptions.innerHTML = `
                <p class="lesson-choice-message">
                    Er ging iets mis
                </p>
            `;

        }

    }


    /* =========================================================
       DAG VERANDERD
       ========================================================= */

    dagSelect.addEventListener(
        "change",
        () => {

            /*
             * Oude selectie wissen.
             */

            tijdInput.value =
                "";

            lesInput.value =
                "";


            laadLessen(
                dagSelect.value
            );

        }
    );


    /* =========================================================
       FORMULIER
       ========================================================= */

    if (lessonForm) {

        lessonForm.addEventListener(
            "submit",
            (event) => {

                /*
                 * Zonder geselecteerde les mag
                 * het formulier niet verzonden worden.
                 */

                if (
                    !tijdInput.value ||
                    !lesInput.value
                ) {

                    event.preventDefault();

                    return;
                }

            }
        );

    }


    /* =========================================================
       INITIEEL LADEN
       ========================================================= */

    if (dagSelect.value) {

        laadLessen(
            dagSelect.value
        );

    } else {

        lessonOptions.innerHTML =
            "";

    }



});
