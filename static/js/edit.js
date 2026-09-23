(() => {
    const dagElement = document.getElementById("dag");
    const tijdElement = document.getElementById("tijd");
    const lesElement = document.getElementById("les");
    const statusElement = document.getElementById("lessen-status");

    if (!dagElement || !tijdElement || !lesElement) {
        return;
    }

    let timer = null;
    let requestId = 0;

    async function laadLessen() {
        const dag = dagElement.value;
        const tijd = tijdElement.value;

        lesElement.innerHTML = "";

        if (!dag || !tijd) {
            lesElement.disabled = true;

            const option = document.createElement("option");
            option.value = "";
            option.textContent = "Voer dag en tijd in...";
            lesElement.appendChild(option);

            if (statusElement) {
                statusElement.textContent = "";
            }

            return;
        }

        lesElement.disabled = true;

        const loadingOption = document.createElement("option");
        loadingOption.value = "";
        loadingOption.textContent = "Lessen laden...";
        lesElement.appendChild(loadingOption);

        if (statusElement) {
            statusElement.textContent = "";
        }

        const currentRequest = ++requestId;

        try {
            const response = await fetch(
                `/api/lessen?dag=${encodeURIComponent(dag)}&tijd=${encodeURIComponent(tijd)}`,
                {
                    headers: {
                        "Accept": "application/json"
                    },
                    cache: "no-store"
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

            const lessen = data.lessen || [];
            const huidigeLes =
                lesElement.dataset.currentLes || "";

            lesElement.innerHTML = "";

            if (!lessen.length) {
                const option = document.createElement("option");
                option.value = "";
                option.textContent =
                    "Geen lessen beschikbaar op dit tijdstip";
                lesElement.appendChild(option);

                if (statusElement) {
                    statusElement.textContent =
                        "Geen lessen gevonden voor deze dag en tijd.";
                }

                return;
            }

            const placeholder = document.createElement("option");
            placeholder.value = "";
            placeholder.textContent = "Selecteer een les...";
            lesElement.appendChild(placeholder);

            lessen.forEach((les) => {
                const option = document.createElement("option");

                option.value = les;
                option.textContent = les;

                if (les === huidigeLes) {
                    option.selected = true;
                }

                lesElement.appendChild(option);
            });

            lesElement.disabled = false;

            if (statusElement) {
                statusElement.textContent =
                    `${lessen.length} les${lessen.length === 1 ? "" : "sen"} beschikbaar.`;
            }

        } catch (error) {
            if (currentRequest !== requestId) {
                return;
            }

            lesElement.innerHTML = "";

            const option = document.createElement("option");
            option.value = "";
            option.textContent =
                "Lessen konden niet worden geladen";
            lesElement.appendChild(option);

            if (statusElement) {
                statusElement.textContent =
                    "Lessen konden niet worden opgehaald.";
            }

            console.error(
                "Lessen ophalen mislukt:",
                error
            );
        }
    }

    function wijziging() {
        clearTimeout(timer);

        timer = setTimeout(
            laadLessen,
            250
        );
    }

    dagElement.addEventListener(
        "change",
        wijziging
    );

    tijdElement.addEventListener(
        "change",
        wijziging
    );

    tijdElement.addEventListener(
        "input",
        wijziging
    );

    // Bij bewerken meteen de bestaande
    // combinatie controleren.
    laadLessen();

})();
