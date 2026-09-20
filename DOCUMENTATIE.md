Pasted text(4).txt
Document

Today 7:28 AM
Pasted text(5).txt
Document

Je krijgt een mail wanneer een automatische inschrijving daadwerkelijk mislukt.

Concreet bijvoorbeeld:

    De ingestelde les is niet beschikbaar op die datum → mail.

    De WOD is vervangen door bijvoorbeeld KerstWOD → mail.

    Het event wordt niet gevonden op de ingestelde tijd → mail.

    SportBit geeft een fout tijdens het inschrijven → mail.

    De inschrijving lijkt gelukt, maar de controle daarna bevestigt geen inschrijving → dat kunnen we ook als fout/notificatie laten behandelen.

Je krijgt geen mail voor normale situaties zoals:

    al ingeschreven;

    al op de wachtlijst;

    inschrijving is nog gesloten.

Belangrijk

De mail wordt verstuurd op het moment dat de automatische inschrijfpoging wordt uitgevoerd en daar iets misgaat. Dus niet vooraf omdat SportBit misschien een feestdagles gaat veranderen.

Als je wilt, kunnen we nog één verbetering toevoegen:
een aparte dagelijkse controle rond 00:01 die controleert of alle verwachte lessen bestaan,
en meteen mailt als bijvoorbeeld de WOD ontbreekt. Dan hoef je niet te wachten tot de daadwerkelijke inschrijfpoging.
Ad

Als je wilt, kunnen we nog één verbetering toevoegen: svgeen aparte dagelijkse controle rond 00:01 die controleert of alle verwachte lessen bestaan, svgen meteen mailt als bijvoorbeeld de WOD ontbreekt. Dan hoef je niet te wachten tot de daadwerkelijke inschrijfpoging.

Dat is mooi.

Ja, mooi — ik heb die verbetering toegevoegd. 👍
Wat er nu gebeurt

Elke dag rond 00:01 controleert de webapp automatisch per ingestelde inschrijving:

    Welke les precies één week later verwacht wordt.

    Of SportBit die les daadwerkelijk heeft gepubliceerd.

    Er wordt exact gekeken naar lesnaam + tijd.

    Ontbreekt de les, bijvoorbeeld:

        WOD → KerstWOD

        les geannuleerd

        gewijzigde les

        les nog niet gepubliceerd

    dan krijg je direct een e-mail.

De bestaande automatische inschrijfpoging blijft daarnaast gewoon bestaan.
Geen dubbele mails

Ik heb er ook een kleine beveiliging in gezet: voor dezelfde inschrijving en dezelfde datum wordt maximaal één ontbrekende-lesmail verstuurd. De registratie daarvan wordt opgeslagen in notify_state.json.

Een technische fout bij SportBit wordt niet zomaar als "les ontbreekt" gemeld; daarvoor blijft de bestaande foutmelding van de daadwerkelijke inschrijfpoging verantwoordelijk.
Aangepaste bestanden

Download sportbit_webapp_aangepast.py

Download notify.py

Ik heb beide bestanden ook met py_compile gecontroleerd; ze zijn syntactisch geldig.

Voorbeeld: als je voor maandag 07:00 WOD hebt ingesteld, dan wordt maandag om ongeveer 00:01 gecontroleerd of er voor de daaropvolgende maandag om 07:00 daadwerkelijk een WOD bestaat. Ontbreekt die, dan krijg je meteen de mail — dus vóórdat je eventueel pas later merkt dat de inschrijving niet gelukt is.
sportbit_webapp_aangepast.pyCode
notify.pyCode

Kun je korte documentatie maken over je werkwijze, wanneer je op welke wijze notificaties stuurt enz. en deze beschikbaar maken middels een "?" knopje op een aparte pagina. Het liefst de tekst ook in een aparte file.

Zeker. Ik heb dit toegevoegd:

    Een ?-knop rechtsboven in de webapp.

    Deze opent een aparte pagina Documentatie.

    De documentatie beschrijft kort:

        hoe de automatische inschrijving werkt;

        de controle rond 00:01;

        wanneer een mail wordt verstuurd;

        wanneer juist geen mail wordt verstuurd;

        hoe dubbele meldingen worden voorkomen;

        de betekenis van de verschillende statussen;

        de rol van notify.py, .env en notify_state.json.

    De tekst staat daarnaast als een apart DOCUMENTATIE.md-bestand, zodat je die ook buiten de webapp kunt bewaren of aanpassen.

Bestanden

Download de aangepaste webapp

Download notify.py

Download DOCUMENTATIE.md

De Python-bestanden zijn opnieuw syntactisch gecontroleerd met py_compile.
sportbit_webapp_aangepast.pyCode
notify.pyCode
DOCUMENTATIE.mdDocument
Ad


Library/
DOCUMENTATIE.md
Go Personal · SportBit webapp — documentatie
1. Automatische inschrijving

Voor iedere inschrijving uit sportbit.conf wordt de eerstvolgende les op de ingestelde weekdag en tijd bepaald. De automatische registratie is gericht op de les precies één week later.

Rond 00:01 op de dag waarop de inschrijving opent wordt SportBit gecontroleerd. De les wordt gezocht op lesnaam + tijd. Het event-ID wordt dus niet vooraf vastgelegd.
2. Dagelijkse controle om 00:01

De webapp heeft een achtergrondcontrole die dagelijks rond 00:01 kijkt voor welke geconfigureerde lessen die dag de boekingsperiode opent.

Als de verwachte les niet bestaat, bijvoorbeeld omdat een WOD is vervangen door een andere les, wordt geen inschrijving uitgevoerd en kan direct een notificatiemail worden verstuurd.

Een technische fout bij het ophalen van SportBit wordt niet automatisch als “les ontbreekt” beschouwd. Zo voorkomen we een verkeerde melding door bijvoorbeeld een tijdelijke netwerk- of SportBit-storing.
3. Wanneer wordt een e-mail gestuurd?

    Les ontbreekt: de dagelijkse controle vindt de verwachte les niet op de doel-datum en het ingestelde tijdstip.

    Inschrijving mislukt: een daadwerkelijke automatische inschrijfpoging levert een fout op of de inschrijving kan niet worden bevestigd.

    Testmail: via Stuur testmail kan handmatig worden gecontroleerd of de SMTP-configuratie werkt.

4. Wanneer wordt géén melding gestuurd?

    Als je al bent ingeschreven.

    Als je al op de wachtlijst staat.

    Als de boekingsperiode nog niet geopend is.

    Als een tijdelijke technische fout niet kan worden vastgesteld als een ontbrekende les.

5. Dubbele meldingen voorkomen

Voor een ontbrekende les wordt per inschrijving en doel-datum maximaal één melding verstuurd. De registratie hiervan staat in notify_state.json. Hierdoor veroorzaakt een herhaalde controle niet steeds opnieuw dezelfde mail.
6. E-mailconfiguratie

De notificaties gebruiken de SMTP-instellingen uit .env. De module notify.py bevat uitsluitend de e-mailafhandeling; de SportBit- en Flask-logica staat in de webapp.
7. Statussen in de webapp

    INGESCHREVEN — SportBit meldt dat de registratie gelukt is.

    WACHTLIJST — je staat op de wachtlijst.

    NIET INGESCHREVEN — de les bestaat en registratie is mogelijk.

    INSCHRIJVING GESLOTEN — de les bestaat, maar het boekingsmoment is nog niet aangebroken.

    GEEN EVENT — de verwachte les is niet gevonden.

    STATUS ONBEKEND — de controle kon niet betrouwbaar worden uitgevoerd.

