Coronatest-scandata -- monitoring COVID-19 test capacity in the Netherlands
===========================================================================

Author: Han-Kwang Nienhuys (@hk_nien on Twitter).

Copyright:

* Code: open source according to the MIT license; see LICENSE file.
* Data: public domain. Credits would be appreciated, though.

Since this data is mostly of interest to people in the Netherlands,
the rest of the documentation will be in Dutch.

Achtergrond
-----------
Testen voor COVID-19 wordt momenteel (februari 2022) door een aantal partijen
gedaan:

- GGD: voor mensen met symptomen en mensen die in contact zijn geweest met
  een besmette persoon. GGD gebruikt hoofdzakelijk PCR-testen; incidenteel ook
  antigeentesten. Testen is gratis, maar gedurende drukke perioden schiet de
  capaciteit tekort; o.a. in november 2021 en januari 2022.
- Testen voor Toegang bij Stichting Open Nederland (SON): antigeentesten, voor
  coronatoegangsbewijs (horeca e.d.). Kosteloos. Niet bedoeld voor mensen met
  symptomen. De testen worden afgenomen door commerciële aanbieders.
- Testen bij drukte/Testen bij Klachten, ook bij SON. GGD kan sinds 27
  januari doorverwijzen naar SON (antigeentests). Kosteloos. Uitvoering door
  dezelfde bedrijven als Testen voor Toegang, maar op andere locaties en met
  vermoedelijk andere financieringsconstructie.
- Commerciële aanbieders voor negatief-certificaten voor internationale
  reizigers (PCR en antigeen). Meest dezelfde aanbieders, maar de reiziger
  betaalt.

Ik volg sinds zomer 2021 de beschikbaarheid van GGD-testafspraken, zie
[Google sheets](https://docs.google.com/spreadsheets/d/1tUJHU7qbeDf71HaQ3vDfdWGr3q56DXYSfiZ18PuEqZ4/edit?usp=sharing)
en sinds 27 januari ook de beschikbaarheid van Testen bij Klachten via
SON.

Tot 5 februari deed ik dit met de hand; daarna automatisch. Dit
Git-repository is voor de data en code om de data te analyseren. De
code om de data te verzamelen van het online boekingssysteem is niet
openbaar.

Bij het afsprakensysteem van SON was er data beschikbaar over de exacte
capaciteit van de testlocaties, d.w.z. hoeveel testafspraken er precies gemaakt
werden en beschikbaar waren in elk slot van 15 minuten. Deze informatie zag je
niet in de web-interface, maar werd wel door je browser opgehaald. Helaas,
enkele dagen nadat ik hierover twitterde hebben (op 10 februari) werd die
informatie weggehaald.


Systeemeisen
------------
De code is geschreven voor de Python-omgeving van [Anaconda3
2021.11](https://repo.anaconda.com/archive/) in Linux, in het
bijzonder: Python 3.8 met Pandas. Ik gebruik zelf Spyder
om interactief te werken en te debuggen.

Bestanden
---------
- `data-son/son_scan-yyyy-Www.csv`: CSV-bestanden per kalenderweek; zie
  hieronder.
- `data-son/son_scan-latest.csv`: symbolic link naar meest recente
  son_scan-bestand.
- `data-son/loc-*.json`: informatie over de locaties in JSON-formaat.
  Bestandsnaam `loc-{postcode}-{hash}.json`. Een aantal velden zijn
  vervangen door `'####'` omdat die mogelijk niet-relevante wijzingen
  ondergaan.
- `data-son/summary-*.txt`: samenvatting van elke scan (gegenereerd door
  `son_analyze.py`), gebundeld per week. De opmaak van dit bestand kan
  met terugwerkende kracht wijzigen.
- `data-ggd/ggd_scan-{YYYY}-W{ww}.csv`: GGD scan data, per week.
- `data-ggd/ggd_locations.csv`: GGD locatiebeschrijving (volledig adres
  etc.).
- `son_analyze.py`: simpel script voor analyse van son_scan bestand.
- `coronatest_analyze_csv.py`: script om ggd_scan-*.csv te converteren
  naar scores (1-7).

### Kolommen in data-son/son_scan-*.csv

- `scan_time`: Datum/tijd YYYY-mm-dd HH:MM van de scan (tijdzone CET).
- `apt_date`: Datum YYYY-mm-dd van de testafspraak (CET).
- `short_addr`: postcodecijfers en plaats van de testlocatie.
- `num_booked`: aantal boekingen voor deze dag, vanaf scan_time.
- `num_slots`: testcapaciteit voor hetzelfde tijdsinterval.
   Tot 10 februari waren `num_booked` en `num_slots` het werkelijke
   aantal boekingen; daarna alleen het aantal beschikbare tijdslots.
- `num_booked_2h`, `num_slots_2h`: aantal boekingen/slots tot 2 uur vooruit.
- `num_booked_45m`, `num_slots_45m`: aantal boekingen/slots tot 45 minuten vooruit.
- `num_booked_15m`, `num_slots_15m`: aantal boekingen/capaciteit tot
  15 minuten vooruit. Dit is het eerstvolgende slot van 15 minuten;
  representatief voor de werkelijk gebruikte capaciteit.
- `first_tm`: eerst beschikbare afspraaktijd (HH:MM) of '-----' indien
   er geen slots waren.
- `last_tm`: laatst beschikbare afspraaktijd (HH:MM) of '-----'.
- `company`: naam uitvoerend bedrijf.
- `all_slots`: complete agenda vanaf first_tm; bijv. '-X---' voor vijf
  slots waarvan de tweede ('X') niet beschikbaar is.
- `is_active`: boolean; komt uit de API. Onduidelijk of deze ooit False
  kan zijn.
- `loc_id_hash`: hash van locatie (hexadecimaal). Kan nuttig zijn als
  het werk wordt overgenomen door een ander bedrijf of als er twee
  testlocaties op dezelfde postcodecijfers zitten.
- `api_version`: 1 voor volledige boekingsinformatie; 2 voor alleen het
  aantal tijdslots (vanaf 10 februari). Kolom ontbreekt in oudere data.
- `xfields`: verdwenen of nieuwe velden (als SON de API wijzigt).
  Ontbreekt in oudere data.

### Kolommen in data-ggd/ggd_scan-*.csv

- `scan_time`: Datum/tijd 'YYYY-mm-dd HH:MM' van de scan (tijdzone CET).
- `req_date`: Datum (YYYY-mm-dd) van de gewenste afspraakdatum.
- `req_pc4`: Gevraagde postcode (fietsafstand).
- `opt0_short_addr`: optie 0, verkort adres (postcodecijfers + woonplaats)
- `opt0_time`: optie 0, afspraaktijd (YYYY-mm-dd HH:MM)
- `opt0_loc_id`: optie 0, locatie-ID (postcode+hash); verwijst naar
   ggd_locations.csv.
- `opt1_short_addr`, `opt1_time`, `opt1_loc_id`: zelfde voor optie 1.
- `opt2_short_addr`, `opt2_time`, `opt2_loc_id`: zelfde voor optie 2.

### Kolommen in data-ggd/ggd_locations.csv

- `loc_id`: locatie ID (postcodecijfers+hash). Als er iets aan de locatie verandert
  (adres, bereikbaarheid), dan verandert deze ID ook.
- `first_seen`: eerste  afspraakdatum (YYYY-mm-dd).
- Overige kolommen spreken voor zich.

### Kolommen in data-ggd/ggd_locations-last_seen.csv

- `last_seen`: laatste afspraakdatum. (Apart bestand i.v.m. frequente updates.)

### Let op:

- Negeer regels die beginnen met `#`. Die zijn bedoeld om het
  CSV-bestand makkelijker leesbaar te maken voor mensen.
- Volgorde van kolommen kan wijzigen. Gebruik de kolomtitels op de
  eerste regel van elk CSV-bestand.
