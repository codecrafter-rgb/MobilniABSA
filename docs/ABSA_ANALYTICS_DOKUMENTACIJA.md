# ABSA Analytics: IAA i statistika skupa podataka

## 1. Namena

Modul `analytics/absa_analytics.py` služi za dve povezane analize:

1. merenje slaganja anotatora na kalibracionom skupu (Inter-Annotator Agreement, IAA);
2. opisnu statistiku konačnog, konsolidovanog ABSA skupa podataka.

IAA deo podržava proizvoljan broj anotatora. Za pet anotatora automatski formira svih deset jedinstvenih parova:

```text
A1-A2, A1-A3, A1-A4, A1-A5,
A2-A3, A2-A4, A2-A5,
A3-A4, A3-A5,
A4-A5
```

Za svaku metriku se prikazuje rezultat svakog para i aritmetička sredina svih definisanih rezultata. Status šuma se dodatno ocenjuje Fleissovom kapom, koja svih pet anotatora posmatra istovremeno.

Analiza je podeljena na nivoe zato što jedna zbirna mera ne može da pokaže gde nastaje neslaganje. Anotatori mogu, na primer, pronaći isti tekstualni target, a zatim mu dodeliti različitu kategoriju ili sentiment. Odvojene metrike omogućavaju da se tačno utvrdi da li problem nastaje pri filtriranju recenzija, ekstrakciji targeta, izboru kategorije ili proceni sentimenta.

## 2. Instalacija

Modul koristi sledeće biblioteke:

- `numpy` za numeričke matrice;
- `scipy` za Hungarian algoritam;
- `scikit-learn` za nominalnu i komponentnu Cohenovu kapu;
- `statsmodels` za Fleissovu kapu.

Zavisnosti su navedene u `requirements.txt` i instaliraju se komandom:

```bash
python3 -m pip install -r requirements.txt
```

Preporučuje se korišćenje virtuelnog okruženja:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## 3. Ulazni format

### 3.1. Kanonski format

Svaki anotatorski JSON mora da sadrži listu recenzija. Kanonski zapis izgleda ovako:

```json
[
  {
    "review_id": "REV_001",
    "url": "https://mobilnisvet.com/mobilni/yx4/Apple/iPhone-16-8GB-512GB-2x-SIM",
    "text": "Baterija traje dva dana, ali je kamera očajna.",
    "is_noise": false,
    "annotations": [
      {
        "target": "Baterija",
        "start_char": 0,
        "end_char": 8,
        "category": "Baterija",
        "sentiment": "Pozitivan"
      },
      {
        "target": "kamera",
        "start_char": 28,
        "end_char": 34,
        "category": "Kamera",
        "sentiment": "Negativan"
      }
    ]
  }
]
```

Polja imaju sledeće značenje:

| Polje | Značenje |
| :-- | :-- |
| `review_id` | Opcioni lokalni identifikator iz eksporta. Ne koristi se za poravnanje anotatora. |
| `url` | URL izvora. Obavezni deo ključa za poravnanje recenzija. |
| `text` | Originalni tekst recenzije. |
| `is_noise` | `true` ako recenzija nije relevantna za ABSA, inače `false`. |
| `annotations` | Lista aspektnih anotacija. |
| `target` | Eksplicitni tekstualni target ili `"NULL"`/`null` za implicitni aspekt. |
| `start_char` | Početni indeks targeta, uključen u span. |
| `end_char` | Krajnji indeks targeta, nije uključen u span. |
| `category` | Jedna od 11 kategorija taksonomije. |
| `sentiment` | `Pozitivan`, `Negativan`, `Neutralan` ili `Konflikt`. |

Span koristi standardni poluotvoreni interval `[start_char, end_char)`. Na primer, span `(0, 8)` obuhvata karaktere sa indeksima od 0 do 7.

### 3.2. Implicitni aspekti

Implicitni aspekt nema tekstualni span. Podržana su oba zapisa:

```json
{
  "target": "NULL",
  "start_char": null,
  "end_char": null,
  "category": "Performanse",
  "sentiment": "Pozitivan"
}
```

```json
{
  "target": null,
  "start_char": null,
  "end_char": null,
  "category": "Performanse",
  "sentiment": "Pozitivan"
}
```

### 3.3. Format sa paralelnim anotacionim poljima

Modul podržava format u kome su odluka o relevantnosti i aspektne anotacije predstavljene poljima `review_status`, `categories`, `sentiment` i `implicit_aspects`. Za potpun IAA ulaz mora da zadrži sve recenzije i njihove odluke `DA`/`NE`. Eksplicitne anotacije su raspoređene između paralelnih polja:

```json
{
  "url": "https://example.org/izvor-komentara",
  "comment": "Baterija traje dva dana.",
  "id": 17,
  "review_status": "DA",
  "categories": [
    {
      "start": 0,
      "end": 8,
      "text": "Baterija",
      "labels": ["Baterija"]
    }
  ],
  "sentiment": ["Pozitivan"],
  "implicit_aspects": [
    {
      "taxonomy": [["Opšta ocena", "Pozitivan"]]
    }
  ]
}
```

Element na indeksu `i` u `categories` dobija sentiment sa indeksa `i` iz liste `sentiment`. Modul proverava da su liste jednake dužine. Svaki taxonomy par iz `implicit_aspects` pretvara se u jednu NULL anotaciju.

U stvarnim eksportima `sentiment` je ponekad string kada postoji tačno jedna eksplicitna kategorija. Modul taj nedvosmislen slučaj normalizuje iz `"Negativan"` u `["Negativan"]`. Kada je `review_status` jednak `NE`, recenzija ostaje u skupu radi noise IAA, a njena prazna lista anotacija se pravilno učitava.

### 3.4. Format sa već formiranom listom aspekata

Modul prihvata i format u kome su anotacije već objedinjene u listi `aspects`:

| Kanonsko polje | Postojeće alternativno polje |
| :-- | :-- |
| `review_id` | `id` |
| `text` | `comment` |
| `annotations` | `aspects` |
| `target` | `text` unutar aspekta |
| `start_char` | `start` |
| `end_char` | `end` |
| `is_noise` | izvodi se iz `review_status` (`NE` znači šum) |

Ovakva šema može da se koristi i za IAA samo ako zadržava sve recenzije, uključujući one sa statusom `NE`. Ako su `NE` zapisi prethodno uklonjeni, format je pogodan za statistiku validnog skupa, ali ne i za noise IAA, jer su različite odluke anotatora o relevantnosti već izgubljene.

Stare oznake sentimenta se normalizuju na kanonske vrednosti:

| Stara oznaka | Kanonska vrednost |
| :--: | :-- |
| `P` | `Pozitivan` |
| `N` | `Negativan` |
| `K` | `Konflikt` |
| `Konfliktan` | `Konflikt` |

Normalizacija sprečava da ista semantička vrednost bude prikazana kao više odvojenih klasa u statistici.

### 3.5. Identifikovanje istog komentara

Lokalno polje `id` nije stabilno između anotatorskih eksportova i zato se ne koristi za poravnanje. Isti komentar može imati jedan ID kod prvog anotatora, a sasvim drugi ID kod drugog.

Sam `url` takođe nije dovoljan kao jedinstveni ključ kada jedna URL stranica sadrži više komentara. Zato se koristi složeni ključ:

```text
(url, text/comment)
```

Modul koristi URL zajedno sa punim tekstom komentara. Time se isti komentar poravnava uprkos različitim lokalnim ID-evima, dok različiti komentari sa iste URL stranice ostaju odvojene jedinice. Svaki ulazni fajl mora imati jedinstvene vrednosti ovog složenog ključa.

Poređenje teksta je tačno, bez približnog uparivanja. Tekst zato ne treba menjati između anotatorskih eksportova. Približno tekstualno uparivanje moglo bi pogrešno spojiti dva slična komentara i nije pogodno kao podrazumevano ponašanje za IAA.

### 3.6. Validacija ulaza

Modul prekida obradu sa jasnom greškom ako:

- JSON na vrhu nije lista;
- recenzija nema validan `url`;
- recenzija nema tekst u polju `text` ili `comment`;
- isti složeni ključ `(url, text/comment)` postoji više puta u jednom fajlu;
- anotacija nema kategoriju ili sentiment;
- kategorija nije jedna od 11 definisanih vrednosti taksonomije;
- sentiment posle normalizacije nije `Pozitivan`, `Negativan`, `Neutralan` ili `Konflikt`;
- broj `categories` elemenata nije jednak broju eksplicitnih `sentiment` vrednosti;
- eksplicitna kategorija u raw eksportu nema tačno jednu vrednost u `labels`;
- `implicit_aspects.taxonomy` nema očekivane parove kategorije i sentimenta;
- eksplicitni span nema celobrojne granice;
- važi `end_char <= start_char`;
- `is_noise` u kanonskom formatu nije logička vrednost;
- anotatorski fajlovi ne sadrže isti skup `(url, text/comment)` ključeva.

Poslednja provera je posebno važna. Pairwise IAA ima smisla samo ako se porede ocene istih jedinica. Tiho poređenje preseka fajlova moglo bi da ukloni upravo recenzije koje nedostaju kod jednog anotatora i veštački poveća slaganje. Svi anotatorski ulazi zato moraju sadržati isti skup `(url, text/comment)` ključeva, iako njihove odluke o statusu i broj aspektnih anotacija mogu biti različiti.

## 4. Tok obrade

Obrada se može predstaviti sledećim tokom:

```text
JSON fajlovi
    |
    v
Učitavanje i normalizacija šeme
    |
    v
Provera `(url, tekst)` ključeva recenzija
    |
    v
Generisanje svih parova anotatora
    |
    +--> nivo 1: status šuma
    +--> nivo 2: eksplicitni spanovi
    +--> nivo 3: kategorije poravnatih targeta
    +--> nivo 4: sentiment usaglašenih aspekata
    +--> nivo 5: kompletne ABSA tuple
    |
    v
Srednja vrednost po metrici + Fleissova kapa
    |
    v
Markdown prikaz + iaa_report.json
```

## 5. Poravnanje anotacija

Pre poređenja kategorije i sentimenta potrebno je utvrditi koje anotacije dva anotatora opisuju isti target.

### 5.1. Character IoU

Za dva eksplicitna spana `A` i `B` računa se character-level Intersection over Union:

```text
IoU(A, B) = dužina(A presek B) / dužina(A unija B)
```

Primer:

```text
A = [0, 8)   dužina 8
B = [0, 7)   dužina 7
presek = 7
unija = 8
IoU = 7 / 8 = 0.875
```

Ako se spanovi ne preklapaju, IoU je 0 i anotacije se ne poravnavaju.

### 5.2. Hungarian algoritam

Za svaku recenziju formira se matrica IoU vrednosti između svih eksplicitnih anotacija anotatora A i svih eksplicitnih anotacija anotatora B. Hungarian algoritam pronalazi jednoznačno uparivanje sa najvećim ukupnim IoU rezultatom.

Jednoznačno znači da jedna anotacija može biti uparena sa najviše jednom anotacijom drugog anotatora. Ovo sprečava da jedan dugačak span bude proglašen poklapanjem sa više kraćih spanova i time neopravdano poveća rezultat.

Prihvataju se samo parovi sa `IoU > 0`. Hungarian algoritam je izabran umesto običnog redoslednog ili lokalno pohlepnog uparivanja zato što daje globalno optimalno poravnanje za celu recenziju.

### 5.3. NULL anotacije

NULL target nema koordinate, pa geometrijsko IoU poravnanje nije moguće. Redosled implicitnih aspekata u JSON listi nema semantičko značenje, jer se svaki implicitni aspekt odnosi na komentar u celosti. Zato se NULL anotacije posmatraju kao neuređeni multiskup.

Za category metrike poravnanje se vrši u tri koraka:

1. uparuje se zajednički multiskup kategorija;
2. preostale različite kategorije uparuju se kao kategorijska neslaganja;
3. ako jedan anotator ima više implicitnih kategorija, svaki višak se uparuje sa posebnom oznakom `MISSING` i ostaje deo koeficijenta.

Kategorija ovde nije pomoćna osobina tekstualnog targeta, već identitet implicitnog aspekta. Zbog toga uparivanje implicitnih anotacija po kategoriji ne uvodi informaciju o redosledu, nego poredi neuređene izbore aspekata. Na primer, liste `[Baterija, Kamera]` i `[Kamera, Baterija]` predstavljaju potpuno isti skup implicitnih kategorija.

Ako se ista implicitna kategorija ponovi više puta, njen broj pojavljivanja ostaje deo multiskupa. Nijedna dodatna ili propuštena kategorija se ne odbacuje.

Sentiment implicitnog aspekta poredi se samo kada oba anotatora imaju tačno jednu anotaciju zajedničke kategorije. Ako je ista implicitna kategorija ponovljena kod nekog anotatora, ne postoji nezavisan identitet kojim bi se sentimenti metodološki neutralno uparili, pa se taj ambigvitet izostavlja iz sentiment kape. Full-tuple F1 ga i dalje ocenjuje kao multiskup kompletnih tupli.

## 6. Nivo 1: status šuma ili relevantnosti

Na ovom nivou svaka recenzija ima jednu binarnu oznaku:

- `is_noise = true`: recenzija se odbacuje;
- `is_noise = false`: recenzija je validna za ABSA anotaciju.

### 6.1. Pairwise Cohenova kapa

Za svaki par anotatora računa se:

```text
kappa = (P_o - P_e) / (1 - P_e)
```

gde je:

- `P_o` stvarno posmatrano slaganje;
- `P_e` očekivano slučajno slaganje dobijeno iz marginalnih raspodela oznaka.

Cohenova kapa je korisnija od običnog procenta slaganja jer koriguje deo slaganja koji bi mogao nastati slučajno. Tipično tumačenje, koje treba koristiti kao smernicu, a ne kao univerzalnu granicu, jeste:

| Kapa | Okvirno tumačenje |
| :--: | :-- |
| `< 0` | slaganje lošije od slučajnog |
| `0.00-0.20` | slabo |
| `0.21-0.40` | zadovoljavajuće/nisko |
| `0.41-0.60` | umereno |
| `0.61-0.80` | značajno |
| `0.81-1.00` | skoro potpuno |

Granice ne treba koristiti bez pregleda broja primera i raspodele klasa. Visoka kapa nad malim uzorkom može biti nestabilna.

### 6.2. Fleissova kapa

Fleissova kapa meri slaganje svih anotatora istovremeno. Za svaku recenziju pravi se broj glasova za dve klase, relevantno i šum, a zatim se računa grupno slaganje korigovano za slučajnost.

Za razliku od proseka pairwise Cohenovih kapa, Fleissova kapa nije prosek deset rezultata. Ona predstavlja jednu zajedničku procenu dobijenu direktno iz glasova svih anotatora.

### 6.3. Degenerisan slučaj

Ako svi anotatori svim recenzijama dodele istu jedinu klasu, standardna formula kape ima izraz `0/0`: posmatrano i očekivano slaganje su oba 1. Biblioteke zato često vraćaju `NaN`.

Modul ovaj slučaj prikazuje kao `null` u JSON-u i `N/A` u Markdown izveštaju. Obično observed agreement može biti 100%, ali chance-corrected kappa matematički nije definisana i zato se ne zamenjuje vrednošću `1.0`.

## 7. Nivo 2: ekstrakcija target spanova (ATE)

Na ATE nivou posmatraju se samo eksplicitni targeti i ignorišu se kategorija i sentiment. Analiza se vrši nad recenzijama koje su oba anotatora označila kao validne.

Ovo ograničenje razdvaja dve vrste greške:

- neslaganje o relevantnosti meri nivo 1;
- neslaganje o granicama targeta meri nivo 2.

### 7.1. Strict F1

Strogo poklapanje postoji samo kada su obe granice identične:

```text
(start_A, end_A) == (start_B, end_B)
```

Broj strogo uparenih spanova koristi se kao broj tačno pozitivnih primera. Za dve liste spanova simetrični F1 je:

```text
F1 = 2 * broj_poklapanja / (broj_spanova_A + broj_spanova_B)
```

Ovo je ekvivalentno harmonijskoj sredini preciznosti i odziva, ali ne zahteva da jednog anotatora proglasimo referentnim ili zlatnim standardom.

Primer: A ima 4 spana, B ima 6, a 3 su potpuno ista:

```text
Strict F1 = 2 * 3 / (4 + 6) = 0.60
```

### 7.2. Partial IoU F1

Kod delimičnog poklapanja svaki poravnati par doprinosi svojim IoU rezultatom umesto binarne vrednosti 0 ili 1:

```text
Partial F1 = 2 * suma_IoU_poravnatih_parova
             / (broj_spanova_A + broj_spanova_B)
```

Ova mera nagrađuje delimično saglasne granice. Korisna je kada oba anotatora prepoznaju isti izraz, ali jedan uključuje pridev, predlog ili drugi susedni deo teksta.

Strict i partial F1 treba analizirati zajedno:

- visok partial, a niži strict F1 ukazuje na problem sa pravilima granica targeta;
- oba niska rezultata ukazuju da anotatori često biraju različite targete;
- oba visoka rezultata ukazuju na stabilnu ekstrakciju.

### 7.3. Micro agregacija

Broj spanova i poklapanja prvo se sabira kroz sve zajednički validne recenzije, pa se tek onda računa F1. To je micro F1: recenzije sa više aspekata proporcionalno više utiču na rezultat.

Ako oba anotatora nemaju nijedan eksplicitni target u celom uporedivom skupu, F1 je definisan kao `1.0`, jer ne postoji nijedan lažno dodat ili propušten target.

## 8. Nivo 3: dodela aspektne kategorije (ACSA)

Kategorija se poredi samo na prethodno poravnatim targetima. Uključeni su:

- eksplicitni targeti poravnati sa `IoU > 0`;
- NULL kategorije poravnate kao neuređeni multiskup, uključujući `MISSING` za svaki višak ili manjak.

Na ovom nivou se ne zahteva da sentiment bude jednak. Cilj je da se izoluje slaganje o kategoriji.

### 8.1. Cohenova kapa za kategoriju

Pairwise Cohenova kapa koristi 11 kategorija taksonomije i operativnu oznaku `MISSING` za neuparenu implicitnu kategoriju. Time dodatni ili propušteni NULL aspekt smanjuje agreement umesto da nestane iz računanja. Formula je ista kao kod statusa šuma. Ovde je problem prevalencije izraženiji: neke kategorije, poput opšte ocene, baterije ili kamere, mogu biti mnogo češće od memorije ili performansi.

Zbog toga veoma visoko sirovo slaganje ne mora uvek dati jednako visoku Cohenovu kapu.

### 8.2. Gwetov AC1

Gwetov AC1 se računa kao:

```text
AC1 = (P_o - P_e_gwet) / (1 - P_e_gwet)
```

Za `q` kategorija rating skale i objedinjenu marginalnu verovatnoću `p_k` svake kategorije, očekivano slaganje je:

```text
P_e_gwet = suma[p_k * (1 - p_k)] / (q - 1)
```

AC1 je dodat zato što je manje osetljiv na poznati paradoks prevalencije: anotatori mogu imati veoma visok procenat slaganja, ali nisku Cohenovu kapu kada jedna klasa izrazito dominira.

Vrednost `q` se dobija iz cele unapred definisane rating skale, a ne samo iz klasa koje su se pojavile kod konkretnog para. Za category računanje skala ima 12 operativnih vrednosti: 11 kategorija i `MISSING`. Kategorije sa nulom pojavljivanja ostaju deo skale sa marginalnom verovatnoćom nula.

Cohenovu kapu i AC1 treba prikazivati zajedno. Velika razlika između njih je signal da treba pregledati raspodelu kategorija, a ne automatski izabrati povoljniji rezultat.

## 9. Nivo 4: sentiment aspekta

Sentiment se poredi samo kada važe oba uslova:

1. targeti su poravnati;
2. anotatori su dodelili istu aspektnu kategoriju.

Ovo ograničenje odgovara pojmu „međusobno usaglašena aspektna jedinica“. Ako je jedan anotator označio target kao `Hardver`, a drugi kao `Softver`, njihovi sentimenti ne treba da budu korišćeni za procenu čiste sentiment saglasnosti. Kategorijsko neslaganje je već zabeleženo na nivou 3.

### 9.1. Glavne sentiment metrike

Četiri sentimenta se u glavnim metrikama tretiraju kao nominalne klase. Ne nameće se linearni redosled, jer `Konflikt` nije prirodna ordinalna tačka između negativnog, neutralnog i pozitivnog sentimenta.

Prikazuju se:

- nominalna Cohenova kapa, koja koriguje exact slaganje za očekivano slučajno slaganje;
- nominalni Gwet AC1 sa celom četvoroklasnom rating skalom;
- exact agreement, odnosno prost procenat identičnih sentiment oznaka.

Exact agreement je interpretabilan, ali ne koriguje slučajno slaganje. Zato se prikazuje uz Cohen i AC1, a ne umesto njih.

### 9.2. Bipolarne komponente

Za dopunsku analizu svaki sentiment se predstavlja prisustvom pozitivne i negativne komponente:

| Sentiment | Pozitivna komponenta | Negativna komponenta |
| :-- | :--: | :--: |
| `Pozitivan` | 1 | 0 |
| `Negativan` | 0 | 1 |
| `Neutralan` | 0 | 0 |
| `Konflikt` | 1 | 1 |

Posebno se računaju Cohenove kape za pozitivnu i negativnu komponentu. One pokazuju da li neslaganje pretežno nastaje pri prepoznavanju pozitivnog ili negativnog stava.

### 9.3. Bipolarna ponderisana kapa

Jedinstvena dopunska mera koristi Hamming udaljenost između dve bipolarne reprezentacije:

```text
w(a, b) = 1 - HammingDistance(bits(a), bits(b)) / 2
```

Matrica težina slaganja je:

|  | Pozitivan | Negativan | Neutralan | Konflikt |
| :-- | :--: | :--: | :--: | :--: |
| Pozitivan | 1.0 | 0.0 | 0.5 | 0.5 |
| Negativan | 0.0 | 1.0 | 0.5 | 0.5 |
| Neutralan | 0.5 | 0.5 | 1.0 | 0.0 |
| Konflikt | 0.5 | 0.5 | 0.0 | 1.0 |

Posmatrano ponderisano slaganje je prosek težina anotiranih parova. Očekivano ponderisano slaganje dobija se iz marginalnih sentiment raspodela oba anotatora i iste matrice težina. Konačna kapa je:

```text
kappa_bipolar = (P_observed_weighted - P_expected_weighted)
                 / (1 - P_expected_weighted)
```

Ova mera je sekundarna. Glavni sentiment zaključak treba zasnivati na nominalnom Cohenu, AC1 i exact agreementu.

## 10. ACSA tuple Micro F1

ACSA anotacija se predstavlja parom:

```text
(kategorija, sentiment)
```

Target se na ovom nivou zanemaruje. Eksplicitna i implicitna anotacija sa istom
kategorijom i sentimentom zato predstavljaju isti ACSA izlaz. Unutar jednog
komentara identični parovi se konsoliduju u skup, jer njihovo ponavljanje ne
predstavlja novu ACSA odluku.

Za svaki par anotatora prvo se kroz sve komentare saberu broj jedinstvenih ACSA
parova svakog anotatora i veličine njihovih preseka. Zatim se računa simetrični
micro F1:

```text
ACSA Micro F1 = 2 * broj_zajednickih_parova
                / (broj_parova_A + broj_parova_B)
```

Mera zahteva istovremeno slaganje kategorije i sentimenta, ali ne zahteva
slaganje target spana. Time dopunjava odvojene kategorijske i sentiment metrike
i odgovara standardnoj evaluaciji ACSA zadatka.

## 11. Nivo 5: potpuna ABSA tuple

Potpuna anotacija se predstavlja kao:

```text
(span ili NULL, kategorija, sentiment)
```

Za eksplicitni target identitet čine koordinate `(start_char, end_char)`, a za implicitni target vrednost `NULL`. Tekst targeta se ne koristi kao poseban ključ jer su koordinate stabilniji identifikator dela originalnog teksta.

Dve tuple se poklapaju samo ako su sva tri elementa identična. Koristi se multiskup (`Counter`), tako da se ispravno obrađuju i eventualne ponovljene identične tuple.

Simetrični micro F1 je:

```text
Micro F1 = 2 * broj_identicnih_tupli
           / (broj_tupli_A + broj_tupli_B)
```

Ovo je najstroža krajnja mera. Nizak full-tuple F1 ne objašnjava uzrok sam po sebi, pa ga uvek treba tumačiti uz rezultate prethodna četiri nivoa.

## 12. Grupne srednje vrednosti

Za svaku pairwise metriku računa se aritmetička sredina:

```text
group_mean = suma(definisanih_pairwise_rezultata)
             / broj_definisanih_pairwise_rezultata
```

Ako pojedinačna kapa nije matematički definisana zato što nema nijednog uporedivog para oznaka, u JSON izveštaju se zapisuje `null`, a u Markdown tabeli `N/A`. Takva vrednost se ne uključuje u grupni prosek.

Broj isključenih parova treba proveriti pre interpretacije proseka. Prosek zasnovan na malom podskupu parova ne predstavlja nužno celu grupu.

## 13. Statistika konačnog skupa

Funkcija:

```python
generate_dataset_statistics(final_data_json)
```

učitava konsolidovani JSON i vraća Python rečnik pogodan za JSON serijalizaciju.

Anotacije noise recenzija se ne uključuju u distribucije i gustinu. Ovo sprečava da slučajno zaostale anotacije unutar odbačene recenzije utiču na statistiku validnog skupa.

### 13.1. Distribucija kategorija

Za svaku od 11 kategorija prikazuje se:

- apsolutni broj anotacija;
- procenat svih anotacija validnih recenzija.

Kategorije bez primera ostaju u rezultatu sa brojem i procentom 0. To obezbeđuje stabilnu šemu izveštaja i olakšava poređenje različitih verzija skupa.

### 13.2. Distribucija sentimenta

Za četiri sentimenta se prikazuju broj i procenat. Procenat se računa u odnosu na ukupan broj anotacija validnih recenzija.

### 13.3. Category x Sentiment matrica

Matrica prikazuje broj anotacija za svaku kombinaciju kategorije i sentimenta. Redovi su kategorije, a kolone četiri sentimenta.

Ona omogućava da se uoče obrasci koji nisu vidljivi iz marginalnih raspodela, na primer da li je `Cena` pretežno negativna ili da li se `Konflikt` sentiment uglavnom javlja kod kamere i softvera.

### 13.4. Eksplicitni i implicitni aspekti

Eksplicitna anotacija ima validan target span. Implicitna anotacija ima `target = "NULL"`, `target = null` ili legacy koordinate `-1`.

Izveštaj sadrži broj i procenat obe grupe. Procenti se računaju u odnosu na ukupan broj anotacija, pa njihov zbir iznosi 100% kada skup sadrži anotacije.

### 13.5. Udeo šuma

Udeo šuma je:

```text
noise_percentage = 100 * broj_noise_recenzija / ukupan_broj_recenzija
```

Prikazuju se i apsolutni brojevi ukupnih, validnih i noise recenzija.

### 13.6. Gustina anotacija

Prosečna gustina predstavlja broj ABSA tupli po validnoj recenziji:

```text
annotation_density = ukupan_broj_anotacija_validnih_recenzija
                     / broj_validnih_recenzija
```

Noise recenzije nisu u imeniocu. Ako nema validnih recenzija, gustina je `0.0` umesto greške deljenja nulom.

## 14. Pokretanje iz komandne linije

### 14.1. Eksplicitna lista fajlova

```bash
python3 analytics/absa_analytics.py \
  <anotatorski-fajl-1.json> \
  <anotatorski-fajl-2.json> \
  <anotatorski-fajl-3.json> \
  <anotatorski-fajl-4.json> \
  <anotatorski-fajl-5.json> \
  --final <finalni-skup.json> \
  --output <izvestaj.json>
```

Redosled argumenata određuje oznake `A1`, `A2`, ..., `A5` u izveštaju.

Nazivi fajlova nisu značajni. Svaki fajl se učitava prema svojoj unutrašnjoj JSON strukturi, a redosled argumenata određuje oznake anotatora u izveštaju.

### 14.2. Direktorijum anotatora

Ako jedan pozicioni argument pokazuje na direktorijum, učitavaju se svi `.json` fajlovi direktno u tom direktorijumu, sortirani po nazivu:

```bash
python3 analytics/absa_analytics.py <direktorijum-sa-anotacijama>/ \
  --final <finalni-skup.json> \
  --output <izvestaj.json>
```

Iz direktorijumskog skeniranja automatski se izuzimaju izlazni izveštaj i fajl prosleđen kroz `--final`, ako se nalaze u istom direktorijumu.

Preporučuje se da direktorijum sadrži samo anotatorske JSON fajlove. U suprotnom je sigurnije navesti eksplicitnu listu.

### 14.3. Samo IAA, bez finalne statistike

Argument `--final` nije obavezan:

```bash
python3 analytics/absa_analytics.py <anotatorski-fajlovi> --output <izvestaj.json>
```

U tom slučaju Markdown izlaz sadrži samo IAA tabelu, a `dataset_statistics` u JSON izveštaju ima vrednost `null`.

## 15. Programski API

Modul se može koristiti i iz drugog Python koda:

```python
from analytics.absa_analytics import (
    calculate_iaa,
    generate_dataset_statistics,
    render_markdown,
)

annotator_files = [
    "annotator_1.json",
    "annotator_2.json",
    "annotator_3.json",
    "annotator_4.json",
    "annotator_5.json",
]

iaa = calculate_iaa(annotator_files)
statistics = generate_dataset_statistics("final_dataset.json")
markdown = render_markdown(iaa, statistics)

print(markdown)
```

Glavne javne funkcije su:

| Funkcija | Rezultat |
| :-- | :-- |
| `load_annotations(path)` | Učitane recenzije indeksirane složenim ključem `(url, tekst)`. |
| `align_annotations(a, b)` | Poravnati parovi anotacija i njihov IoU. |
| `calculate_iaa(paths)` | Svi pairwise rezultati, grupne sredine i Fleissova kapa. |
| `generate_dataset_statistics(path)` | Opisna statistika finalnog skupa. |
| `render_markdown(iaa, statistics)` | Formatiran Markdown izveštaj. |

## 16. Struktura `iaa_report.json`

Izlaz ima dva glavna dela:

```json
{
  "iaa": {
    "annotators": [],
    "review_count": 0,
    "pair_count": 0,
    "pairs": {},
    "group_means": {},
    "noise_fleiss_kappa": null,
    "methodology": {}
  },
  "dataset_statistics": {}
}
```

Za svaki par se čuvaju sledeći ključevi:

```json
{
  "noise_cohen_kappa": 0.0,
  "span_strict_f1": 0.0,
  "span_partial_f1": 0.0,
  "category_cohen_kappa": 0.0,
  "category_gwet_ac1": 0.0,
  "acsa_tuple_micro_f1": 0.0,
  "sentiment_cohen_kappa": 0.0,
  "sentiment_gwet_ac1": 0.0,
  "sentiment_exact_agreement": 0.0,
  "sentiment_positive_component_kappa": 0.0,
  "sentiment_negative_component_kappa": 0.0,
  "sentiment_bipolar_weighted_kappa": 0.0,
  "full_tuple_micro_f1": 0.0
}
```

Polje `methodology` beleži najvažnije odluke o obuhvatu i poravnanju. Time izveštaj ostaje samodokumentujući i rezultat se kasnije može pravilno interpretirati bez oslanjanja samo na izvorni kod.

JSON se zapisuje sa `allow_nan=False`. Nedostupni rezultati su zato standardni JSON `null`, a ne nestandardne vrednosti `NaN` ili `Infinity` koje mnogi alati ne mogu ispravno da obrade.

## 17. Tumačenje rezultata

Preporučeni redosled analize je:

1. proveriti raspodelu validnih i noise recenzija;
2. pregledati Fleissovu i pairwise Cohenovu kapu za noise status;
3. uporediti strict i partial span F1;
4. uporediti Cohenovu kapu kategorija sa Gwetovim AC1;
5. proveriti ACSA tuple Micro F1 kao zajedničku meru kategorije i sentimenta bez targeta;
6. zajedno pregledati nominalnu sentiment kapu, AC1 i exact agreement;
7. komponentne i bipolarnu kapu koristiti za dijagnostiku vrste sentiment neslaganja;
8. full-tuple F1 koristiti kao zbirnu krajnju proveru;
9. pronaći parove anotatora koji odstupaju od grupnog proseka;
10. ručno pregledati recenzije iz problematičnog nivoa.

Primer dijagnostike:

| Obrazac | Verovatno objašnjenje |
| :-- | :-- |
| Noise kapa je niska | Pravila relevantnosti nisu dovoljno precizna ili se različito primenjuju. |
| Partial F1 je visok, strict F1 niži | Anotatori nalaze iste targete, ali ne koriste ista pravila za granice. |
| Span F1 je visok, category kappa niska | Taksonomske granice između kategorija nisu dovoljno jasne. |
| Cohenova kapa je mnogo niža od AC1 | Raspodelom dominira mali broj kategorija; proveriti prevalenciju. |
| Category agreement je visok, sentiment kappa niska | Potrebno je precizirati pravila za neutralan i konfliktan sentiment. |
| Svi parcijalni nivoi su visoki, full tuple je primetno niži | Manja neslaganja sa više nivoa se kumuliraju u strogoj tuple metrici. |

Grupni prosek ne treba da sakrije problem jednog para. Ako devet parova ima rezultat oko 0.90, a jedan 0.45, srednja vrednost može i dalje izgledati prihvatljivo. Pairwise kolone zato ostaju centralni deo izveštaja.

## 18. Metodološka ograničenja

### 18.1. Poravnanje nepreklapajućih targeta

Eksplicitni targeti sa IoU 0 ne mogu biti poravnati, čak i ako pripadaju istoj kategoriji i opisuju isti širi koncept. Ovo je namerno: ATE meri označeni tekst, ne samo semantiku kategorije.

### 18.2. Višestruki NULL aspekti iste kategorije

Redosled NULL aspekata ne utiče na rezultat. Ako se ista implicitna kategorija u jednom komentaru pojavi više puta sa različitim sentimentima, anotacije se porede kao multiskup. To je dosledno trenutnom formatu, ali takve primere ipak treba ručno pregledati: ponavljanje iste implicitne kategorije može predstavljati legitimne odvojene stavove, konflikt koji treba spojiti u jednu anotaciju ili slučajan duplikat.

### 18.3. Bipolarna interpretacija sentimenta

Bipolarna mapa je eksplicitna domenska pretpostavka: `Neutralan` se tumači kao odsustvo obe polarne komponente, a `Konflikt` kao prisustvo obe. Bipolarnu ponderisanu kapu zato treba prikazati kao dopunsku, ne kao zamenu za nominalne koeficijente. Ako se definicija klase `Konflikt` u anotacionim smernicama promeni, mora se ponovo razmotriti i matrica težina.

### 18.4. Kapa i retke klase

Sve chance-corrected metrike zavise od prevalencije. Rezultat uvek treba prikazati zajedno sa brojem primera, matricom raspodele i, kada je moguće, intervalom pouzdanosti dobijenim dodatnom bootstrap analizom.

### 18.5. IAA nije kvalitet prema zlatnom standardu

Visoko slaganje znači da anotatori dosledno primenjuju ista pravila. Ne dokazuje samo po sebi da su anotacije lingvistički ili domenski tačne. Za to je potreban adjudication proces, pregled smernica i provera konačnog konsenzusnog skupa.

## 19. Testiranje

Testovi se pokreću komandom:

```bash
python3 -m unittest -v tests/test_absa_analytics.py
```

Test suite proverava:

- maksimalno IoU poravnanje Hungarian algoritmom;
- redosledno nezavisno poravnanje NULL anotacija po kategoriji;
- ponašanje F1 i AC1 u praznim ili jedno-klasnim slučajevima;
- referentni Cohen kappa primer sa unapred poznatim rezultatom;
- AC1 računanje sa celom unapred definisanom rating skalom;
- kažnjavanje dodatnih ili propuštenih implicitnih kategorija;
- dinamičko formiranje 10 parova za pet anotatora;
- savršeno slaganje i JSON serijalizaciju bez `NaN` vrednosti;
- statistiku finalnog skupa;
- normalizaciju legacy sentiment oznaka;
- direktno učitavanje raw `categories`, `sentiment` i `implicit_aspects` polja;
- zadržavanje `NE` recenzija za noise IAA;
- scalar sentiment kod jednog eksplicitnog aspekta;
- odbijanje raw zapisa sa neuparenim kategorijama i sentimentima;
- odbijanje nepoznatih kategorija i sentimenta;
- poravnanje istog komentara uprkos različitim lokalnim ID-evima;
- razdvajanje različitih komentara koji dele isti URL;
- odbijanje fajlova sa različitim skupovima `(url, tekst)` ključeva.

## 20. Preporučeni proces rada

Praktičan kalibracioni ciklus može da izgleda ovako:

1. svih pet anotatora nezavisno anotira isti kalibracioni skup;
2. pokreće se `analytics/absa_analytics.py` nad pet eksportovanih fajlova;
3. pregledaju se najniže metrike i problematični parovi;
4. ručno se analiziraju konkretna neslaganja;
5. smernice se dopunjuju primerima i jasnijim pravilima;
6. radi se novi krug nezavisne kalibracije;
7. tek nakon stabilnog slaganja prelazi se na punu anotaciju;
8. konsolidovani skup se analizira preko `--final` statistike.

Na ovaj način metrike nisu samo završni broj za izveštaj, već alat za otkrivanje nejasnih pravila i sistematsko poboljšanje kvaliteta skupa podataka.
