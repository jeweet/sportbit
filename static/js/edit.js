(() => {
    const dagElement = document.getElementById("dag");
    const tijdElement = document.getElementById("tijd");
    const lesElement = document.getElementById("les");
    const statusElement = document.getElementById("lessen-status");

    if (!dagElement || !tijdElement || !lesElement) {
        return;
    }

    /*
     * Cache per dag.
     *
     * Bijvoorbeeld:
     * {
     *     maandag: {
     *         "07:00": ["WOD"],
     *         "18:00": ["WOD", "Olympic Weightlifting"]
     *     }
     * }
     */
    const dagCache = new Map();

    let requestId = 0;

    const huidigeTijd =
        tijdElement.dataset.currentTijd || "";

    const huidigeLes =
        lesElement.dataset.currentLes || "";

    function toonStatus(tekst) {
        if (statusElement) {
            statusElement.textContent = tekst;
        }
    }

    function laadTijden(data, geselecteerdeTijd = "") {
        tijdElement.innerHTML = "";

        const tijden = Object.keys(data);

        if (!tijden.length) {
            const option = document.createElement("option");
            option.value = "";
            option.textContent =
                "Geen tijden beschikbaar";

            tijdElement.appendChild(option);
            tijdElement.disabled = true;

            return;
        }

        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent =
            "Selecteer een tijd...";

        tijdElement.appendChild(placeholder);

        tijden.forEach((tijd) => {
            const option = document.createElement("option");

            option.value = tijd;
            option.textContent = tijd;

            if (tijd === geselecteerdeTijd) {
                option.selected = true;
            }

            tijdElement.appendChild(option);
        });

        tijdElement.disabled = false;
    }

    function laadLessen(data, tijd, geselecteerdeLes = "") {
        lesElement.innerHTML = "";

        const lessen = data[tijd] || [];

        if (!tijd) {
            const option = document.createElement("option");
            option.value = "";
            option.textContent =
                "Kies eerst een tijd...";

            lesElement.appendChild(option);
            lesElement.disabled = true;

            return;
        }

        if (!lessen.length) {
            const option = document.createElement("option");
            option.value = "";
            option.textContent =
                "Geen lessen beschikbaar";

            lesElement.appendChild(option);
            lesElement.disabled = true;

            return;
        }

        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent =
            "Selecteer een les...";

        lesElement.appendChild(placeholder);

        lessen.forEach((les) => {
            const option = document.createElement("option");

            option.value = les;
            option.textContent = les;

            if (les === geselecteerdeLes) {
                option.selected = true;
            }

            lesElement.appendChild(option);
        });

        lesElement.disabled = false;
    }

    function toonDagData(dag, geselecteerdeTijd = "", geselecteerdeLes = "") {
        const data = dagCache.get(dag);

        if (!data) {
            return;
        }

        laadTijden(
            data,
            geselecteerdeTijd
        );

        const tijd =
            geselecteerdeTijd && data[geselecteerdeTijd]
                ? geselecteerdeTijd
                : "";

        laadLessen(
            data,
            tijd,
            geselecteerdeLes
        );

        if (Object.keys(data).length) {
            const aantalTijden =
                Object.keys(data).length;

            toonStatus(
                `${aantalTijden} tijdstip${
                    aantalTijden === 1 ? "" : "pen"
                } beschikbaar.`
            );
        }
    }

    async function laadDag(dag, geselecteerdeTijd = "", geselecteerdeLes = "") {
        if (!dag) {
            tijdElement.innerHTML = "";
            lesElement.innerHTML = "";

            tijdElement.disabled = true;
            lesElement.disabled = true;

            toonStatus("");

            return;
        }

        /*
         * Dag al geladen?
         * Dan absoluut geen nieuwe API-call.
         */
        if (dagCache.has(dag)) {
            toonDagData(
                dag,
                geselecteerdeTijd,
                geselecteerdeLes
            );

            return;
        }

        const currentRequest = ++requestId;

        tijdElement.disabled = true;
        lesElement.disabled = true;

        tijdElement.innerHTML = "";
        lesElement.innerHTML = "";

        const loadingTime = document.createElement("option");
        loadingTime.value = "";
        loadingTime.textContent =
            "Tijden laden...";

        tijdElement.appendChild(loadingTime);

        const loadingLes = document.createElement("option");
        loadingLes.value = "";
        loadingLes.textContent =
            "Lessen laden...";

        lesElement.appendChild(loadingLes);

        toonStatus("SportBit wordt gecontroleerd...");

        try {
            const response = await fetch(
                `/api/lessen?dag=${encodeURIComponent(dag)}`,
                {
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );

            const data = await response.json();

            if (currentRequest !== requestId) {
                return;
            }

            if (!response.ok) {
                throw new Error(
                    data.error || `HTTP ${response.status}`
                );
            }

            const lessen = data.lessen || {};

            dagCache.set(
                dag,
                lessen
            );

            toonDagData(
                dag,
                geselecteerdeTijd,
                geselecteerdeLes
            );

        } catch (error) {
            if (currentRequest !== requestId) {
                return;
            }

            tijdElement.innerHTML = "";
            lesElement.innerHTML = "";

            const timeOption = document.createElement("option");
            timeOption.value = "";
            timeOption.textContent =
                "Tijden konden niet worden geladen";

            tijdElement.appendChild(timeOption);

            const lesOption = document.createElement("option");
            lesOption.value = "";
            lesOption.textContent =
                "Lessen konden niet worden geladen";

            lesElement.appendChild(lesOption);

            tijdElement.disabled = true;
            lesElement.disabled = true;

            toonStatus(
                "De lessen konden niet worden opgehaald."
            );

            console.error(
                "SportBit-dagdata ophalen mislukt:",
                error
            );
        }
    }

    dagElement.addEventListener(
        "change",
        () => {
            laadDag(
                dagElement.value
            );
        }
    );

    tijdElement.addEventListener(
        "change",
        () => {
            const dag = dagElement.value;
            const tijd = tijdElement.value;
            const data = dagCache.get(dag);

            if (!data) {
                return;
            }

            /*
             * Belangrijk:
             * hier wordt géén API-call gedaan.
             */
            laadLessen(
                data,
                tijd
            );

            const lessen =
                data[tijd] || [];

            toonStatus(
                `${lessen.length} les${
                    lessen.length === 1 ? "" : "sen"
                } beschikbaar.`
            );
        }
    );

    /*
     * Bij openen:
     * bestaande dag/tijd/les herstellen.
     */
    laadDag(
        dagElement.value,
        huidigeTijd,
        huidigeLes
    );

})();
