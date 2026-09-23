(() => {
    const logElement = document.getElementById("live-log");
    const logContainer = document.getElementById("log-container");
    const statusElement = document.getElementById("log-refresh-status");

    if (!logElement) {
        return;
    }

    let previousOutput = logElement.textContent;
    let busy = false;
    let autoScroll = true;
    let firstLoad = true;


    /* ========================================================
       Scrollpositie
       ======================================================== */

    // De <pre class="log"> is zelf de scrollcontainer.
    function isNearBottom() {
        const margin = 80;

        return (
            logElement.scrollTop +
            logElement.clientHeight >=
            logElement.scrollHeight - margin
        );
    }


    // Scroll naar de allerlaatste logregel.
    function scrollToBottom() {
        logElement.scrollTop =
            logElement.scrollHeight - logElement.clientHeight;
    }


    // Alleen automatisch volgen wanneer de gebruiker onderaan stond.
    logElement.addEventListener("scroll", function () {
        autoScroll = isNearBottom();
    });


    /* ========================================================
       Log verversen
       ======================================================== */

    async function refreshLog() {
        if (busy || document.hidden) {
            return;
        }

        busy = true;

        try {
            const response = await fetch(
                logElement.dataset.url,
                {
                    headers: {
                        "Accept": "application/json",
                        "Cache-Control": "no-cache"
                    },
                    cache: "no-store"
                }
            );

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.output !== previousOutput) {
                // Bij de eerste keer altijd naar beneden.
                // Daarna alleen als de gebruiker al onderaan stond.
                const shouldScroll = firstLoad || autoScroll;

                logElement.textContent = data.output;
                previousOutput = data.output;

                if (shouldScroll) {
                    requestAnimationFrame(() => {
                        scrollToBottom();
                    });
                }
            }

            if (statusElement) {
                const updatedAt = String(data.updated_at || "").replace("T", " ");

                statusElement.textContent =
                    `Live bijgewerkt: ${updatedAt}`;
            }

            // Eerste succesvolle refresh is voorbij.
            firstLoad = false;

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
            busy = false;
        }
    }


    /* ========================================================
       Initialisatie
       ======================================================== */

    // Eerst direct naar beneden.
    scrollToBottom();


    // Actuele log ophalen.
    refreshLog();


    // Nadat de volledige pagina geladen is opnieuw naar beneden.
    window.addEventListener("load", function () {
        scrollToBottom();

        requestAnimationFrame(() => {
            scrollToBottom();
        });
    });


    // Extra zekerheid voor mobiele browsers.
    setTimeout(scrollToBottom, 100);
    setTimeout(scrollToBottom, 300);
    setTimeout(scrollToBottom, 500);
    setTimeout(scrollToBottom, 1000);


    /* ========================================================
       Live updates
       ======================================================== */

    window.setInterval(refreshLog, 2000);


    // Bij terugkeren naar het tabblad opnieuw verversen.
    document.addEventListener(
        "visibilitychange",
        refreshLog
    );

})();
