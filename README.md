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
  coronatoegangsbewijs (horeca e.d.). Kostenloos. Niet bedoeld voor mensen met
  symptomen. De testen worden afgenomen door commerciële aanbieders.
- Testen bij drukte/Testen bij Klachten, ook bij SON. GGD kan sinds 27
  januari doorverwijzen naar SON (antigeentests). Kostenloos. Uitvoering door
  dezelfde bedrijven maar op andere locaties, maar de financiering werkt
  vermoedelijk anders dan bij Testen voor Toegang.
- Commerciële aanbieders voor negatief-certificaten voor internationale
  reizigers. 

Ik volg sinds zomer 2021 de beschikbaarheid van GGD-testafspraken, zie
[Google sheets](https://docs.google.com/spreadsheets/d/1tUJHU7qbeDf71HaQ3vDfdWGr3q56DXYSfiZ18PuEqZ4/edit?usp=sharing)
en sinds 27 januari ook de beschikbaarheid van Testen bij Klachten via
SON.

Tot 5 februari deed ik dit met de hand; daarna automatisch. Dit
Git-repository is voor de data en code om de data te analyseren. De
code om de data te verzamelen van het online boekingssysteem is niet
openbaar.

Vooralsnog alleen data van SON Testen bij Klachten. Ik ben van plan
meer data bescihkbaar te maken.

Systeemeisen
------------
De code is geschreven voor de Python-omgeving van [Anaconda3
2021.11](https://repo.anaconda.com/archive/) in Linux, in het
bijzonder: Python 3.7 met Pandas. Ik gebruik zelf Spyder
om interactief te werken en te debuggen.

Bestanden
---------
- `data-son/son_scan-yyyy-Www.csv`: CSV-bestanden per kalenderweek; zie
  hieronder.
- `data-son/son_scan-latest.csv`: symbolic link naar meest recente
  son_scan-bestand.
- `son_analyze.py`: simpel script voor analyse van son_scan bestand.

### Kolommen in data-son/son_scan-*.csv

- `scan_time`: Datum/tijd YYYY-mm-dd HH:MM van de scan (tijdzone CET).
- `apt_date`: Datum YYYY-mm-dd van de testafspraak (CET).
- `short_addr`: postcodecijfers en plaats van de testlocatie.
- `num_booked`: aantal boekingen voor deze dag, vanaf scan_time.
- `num_slots`: testcapaciteit voor hetzelfde tijdsinterval. 
- `num_booked_2h`: aantal boekingen tot 2 uur vooruit.
- `num_slots_2h`: aantal slots tot 2 uur vooruit.
- `num_booked_45m`: aantal boekingen tot 45 minuten vooruit.
- `num_slots_45m`: aantal slots tot 45 minuten vooruit.
- `first_tm`: eerst beschikbare afspraaktijd (HH:MM).
- `last_tm`: laatst beschikbare afspraaktijd (HH:MM).
- `company`: naam uitvoerend bedrijf.
- `is_active`: boolean; komt uit de API. Onduidelijk of deze ooit False
  kan zijn.
- `loc_id_hash`: hash van locatie (hexadecimaal). Kan nuttig zijn als
  het werk wordt overgenomen door een ander bedrijf of als er twee
  testlocaties op dezelfde postcodecijfers zitten.

Let op:

- Negeer regels die beginnen met `#`. Die zijn bedoeld om het
  CSV-bestand makkelijker leesbaar te maken voor mensen.
- Volgorde van kolommen kan wijzigen. Gebruik de kolomtitels op de
  eerste regel van elk CSV-bestand.

