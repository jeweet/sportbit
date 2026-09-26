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
     * Alleen de leskeuze initialiseren wanneer
     * deze elementen op de huidige pagina bestaan.
     */

    if (
        dagSelect &&
        lessonOptions &&
        tijdInput &&
        lesInput
    ) {


        /* =====================================================
           STATUS
           ===================================================== */

        function setStatus(message) {

            if (lessenStatus) {
                lessenStatus.textContent = message;
            }

        }


        /* =====================================================
           LES SELECTEREN
           ===================================================== */

        function selectLesson(button) {

            lessonOptions
                .querySelectorAll(".lesson-option")
                .forEach((option) => {

                    option.classList.remove(
                        "selected"
                    );

                    option.setAttribute(
                        "aria-checked",
                        "false"
                    );

                });


            button.classList.add(
                "selected"
            );

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


        /* =====================================================
           LESBLOK MAKEN
           ===================================================== */

        function createLessonButton(
            tijd,
            lesNaam
        ) {

            const button =
                document.createElement(
                    "button"
                );


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
                document.createElement(
                    "span"
                );

            time.className =
                "lesson-option-time";

            time.textContent =
                tijd;


            /* Naam */

            const name =
                document.createElement(
                    "span"
                );

            name.className =
                "lesson-option-name";

            name.textContent =
                lesNaam;


            /* Vinkje */

            const check =
                document.createElement(
                    "span"
                );

            check.className =
                "lesson-option-check";

            check.textContent =
                "✓";


            button.appendChild(
                time
            );

            button.appendChild(
                name
            );

            button.appendChild(
                check
            );


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


        /* =====================================================
           LESSEN LADEN
           ===================================================== */

        async function laadLessen(dag) {

            if (!dag) {

                lessonOptions.innerHTML =
                    "";

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
                                "Accept":
                                    "application/json"
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
                            a
                                .split(":")
                                .map(Number);

                        const [bh, bm] =
                            b
                                .split(":")
                                .map(Number);

                        return (
                            ah * 60 +
                            am -
                            (
                                bh * 60 +
                                bm
                            )
                        );

                    });


                /*
                 * Alle lessen toevoegen.
                 *
                 * Corporate,
                 * Prakticon en
                 * Personal Training
                 * worden bewust overgeslagen.
                 */

                tijden.forEach((tijd) => {

                    const lessen =
                        lessenPerTijd[tijd];


                    if (!Array.isArray(lessen)) {
                        return;
                    }


                    lessen.forEach(
                        (lesNaam) => {

                            if (
                                lesNaam === "Corporate" ||
                                lesNaam === "Prakticon" ||
                                lesNaam === "Personal Training"
                            ) {
                                return;
                            }


                            const button =
                                createLessonButton(
                                    tijd,
                                    lesNaam
                                );


                            lessonOptions.appendChild(
                                button
                            );

                        }
                    );

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


        /* =====================================================
           DAG VERANDERD
           ===================================================== */

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


        /* =====================================================
           FORMULIER
           ===================================================== */

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


        /* =====================================================
           INITIEEL LADEN
           ===================================================== */

        if (dagSelect.value) {

            laadLessen(
                dagSelect.value
            );

        } else {

            lessonOptions.innerHTML =
                "";

        }

    }



/* =========================================================
   SCHEDULER TIJD
   ========================================================= */

const schedulerTime =
    document.getElementById("SPORTBIT_SCHEDULER_TIME");

const schedulerHours =
    document.getElementById("SPORTBIT_SCHEDULER_TIME_HH");

const schedulerMinutes =
    document.getElementById("SPORTBIT_SCHEDULER_TIME_MM");


if (
    schedulerTime &&
    schedulerHours &&
    schedulerMinutes
) {

    /* Bestaande tijd opsplitsen */

    const current = schedulerTime.value || "";

    if (/^\d{2}:\d{2}$/.test(current)) {

        schedulerHours.value =
            current.slice(0, 2);

        schedulerMinutes.value =
            current.slice(3, 5);

    }


    /* Tijd samenvoegen */

    function updateSchedulerTime() {

        schedulerTime.value =
            `${schedulerHours.value}:${schedulerMinutes.value}`;

    }


    /* =====================================================
       UREN
       ===================================================== */

    schedulerHours.addEventListener(
        "input",
        () => {

            schedulerHours.value =
                schedulerHours.value
                    .replace(/\D/g, "")
                    .slice(0, 2);

            updateSchedulerTime();

        }
    );


    /* =====================================================
       MINUTEN
       ===================================================== */

    schedulerMinutes.addEventListener(
        "input",
        () => {

            schedulerMinutes.value =
                schedulerMinutes.value
                    .replace(/\D/g, "")
                    .slice(0, 2);

            updateSchedulerTime();

        }
    );


    /* =====================================================
       PIJLTJES
       ===================================================== */

    schedulerHours.addEventListener(
        "keydown",
        (event) => {

            /*
             * Alleen naar minuten wanneer
             * de cursor daadwerkelijk aan
             * het einde van het urenveld staat.
             */

            if (
                event.key === "ArrowRight" &&
                schedulerHours.selectionStart ===
                    schedulerHours.value.length
            ) {

                event.preventDefault();

                schedulerMinutes.focus();

                schedulerMinutes.setSelectionRange(
                    0,
                    0
                );

            }

        }
    );


    schedulerMinutes.addEventListener(
        "keydown",
        (event) => {

            /*
             * Pijl links:
             * alleen naar uren wanneer
             * de cursor helemaal links staat.
             */

            if (
                event.key === "ArrowLeft" &&
                schedulerMinutes.selectionStart === 0
            ) {

                event.preventDefault();

                schedulerHours.focus();

                schedulerHours.setSelectionRange(
                    schedulerHours.value.length,
                    schedulerHours.value.length
                );

            }


            /*
             * Backspace wanneer de cursor
             * helemaal links staat.
             */

            if (
                event.key === "Backspace" &&
                schedulerMinutes.selectionStart === 0 &&
                schedulerMinutes.selectionEnd === 0
            ) {

                event.preventDefault();

                schedulerHours.focus();

                schedulerHours.setSelectionRange(
                    schedulerHours.value.length,
                    schedulerHours.value.length
                );

            }

        }
    );

}




    /* ========================================================
       LIVE LOG
       ======================================================== */

    const logElement =
        document.getElementById("live-log");

    const logContainer =
        document.getElementById("log-container");

    const statusElement =
        document.getElementById(
            "log-refresh-status"
        );


    /*
     * Op pagina's zonder live-log hoeft
     * de rest van dit logblok niet uitgevoerd te worden.
     */

    if (!logElement) {
        return;
    }


    let previousOutput =
        logElement.textContent;

    let busy =
        false;

    let autoScroll =
        true;

    let firstLoad =
        true;





    function kleurLogregels() {
        const log = document.getElementById("live-log");

        if (!log) {
            return;
        }

        const regels = log.textContent.split("\n");

        log.innerHTML = regels
            .map(regel => {
                const veilig = regel
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;");

                if (regel.includes(" ERROR ")) {
                    return `<span class="log-error">${veilig}</span>`;
                }

                return veilig;
            })
            .join("\n");
    }

    kleurLogregels();

    /* ========================================================
       Scrollpositie
       ======================================================== */

    // De <pre class="log"> is zelf de scrollcontainer.

    function isNearBottom() {

        const margin =
            80;

        return (
            logElement.scrollTop +
            logElement.clientHeight >=
            logElement.scrollHeight -
            margin
        );

    }


    // Scroll naar de allerlaatste logregel.

    function scrollToBottom() {

        logElement.scrollTop =
            logElement.scrollHeight -
            logElement.clientHeight;

    }


    // Alleen automatisch volgen wanneer
    // de gebruiker onderaan stond.

    logElement.addEventListener(
        "scroll",
        function () {

            autoScroll =
                isNearBottom();

        }
    );


    /* ========================================================
       Log verversen
       ======================================================== */

    async function refreshLog() {

        if (
            busy ||
            document.hidden
        ) {
            return;
        }


        busy = true;


        try {

            const response =
                await fetch(
                    logElement.dataset.url,
                    {
                        headers: {
                            "Accept":
                                "application/json",

                            "Cache-Control":
                                "no-cache"
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


            if (
                data.output !==
                previousOutput
            ) {

                /*
                 * Bij de eerste keer altijd naar beneden.
                 * Daarna alleen als de gebruiker al onderaan stond.
                 */

                const shouldScroll =
                    firstLoad ||
                    autoScroll;


                logElement.textContent =
                    data.output;

                previousOutput =
                    data.output;


                if (shouldScroll) {

                    requestAnimationFrame(
                        () => {
                            scrollToBottom();
                        }
                    );

                }

            }


            if (statusElement) {

                const updatedAt =
                    String(
                        data.updated_at || ""
                    ).replace(
                        "T",
                        " "
                    );


                statusElement.textContent =
                    `Live bijgewerkt: ${updatedAt}`;

            }


            // Eerste succesvolle refresh is voorbij.

            firstLoad =
                false;


        } catch (error) {

            if (statusElement) {

                statusElement.textContent =
                    "Live bijwerken tijdelijk niet beschikbaar";

            }


            console.error(
                "Log verversen mislukt",
                error
            );


        } finally {

            busy =
                false;

        }

    }


    /* ========================================================
       Initialisatie
       ======================================================== */

    // Eerst direct naar beneden.

    scrollToBottom();


    // Actuele log ophalen.

    refreshLog();


    // Nadat de volledige pagina geladen is
    // opnieuw naar beneden.

    window.addEventListener(
        "load",
        function () {

            scrollToBottom();


            requestAnimationFrame(
                () => {
                    scrollToBottom();
                }
            );

        }
    );


    // Extra zekerheid voor mobiele browsers.

    setTimeout(
        scrollToBottom,
        100
    );

    setTimeout(
        scrollToBottom,
        300
    );

    setTimeout(
        scrollToBottom,
        500
    );

    setTimeout(
        scrollToBottom,
        1000
    );


    /* ========================================================
       Live updates
       ======================================================== */

    window.setInterval(
        refreshLog,
        2000
    );


    // Bij terugkeren naar het tabblad
    // opnieuw verversen.

    document.addEventListener(
        "visibilitychange",
        refreshLog
    );

});
