# Uputstvo za anotaciju aspekata i sentimenta (ABSA / ATE)

## 1. Cilj anotacije

Cilj ovog projekta je izrada skupa podataka za aspektnu analizu sentimenta (*Aspect-Based Sentiment Analysis* -- ABSA) i ekstrakciju aspektnih izraza (*Aspect Term Extraction* -- ATE) iz korisničkih komentara o mobilnim telefonima na srpskom jeziku.

Za svaki analizirani komentar potrebno je:

1. **Prepoznati i ekstrahovati aspektni izraz (*Aspect Target / Span*)** ako je eksplicitno naveden u tekstu.

2. **Dodeliti odgovarajuću aspektnu kategoriju** iz unapred definisane taksonomije od 11 kategorija.

3. **Odrediti sentiment** (pozitivan, negativan, neutralan ili konfliktan) za svaki prepoznati aspekt zasebno, a ne za komentar u celini.

4. **Filtrirati šum** (ne-evaluativne delove teksta, obične navike korišćenja, pitanja i irelevantna poređenja) u skladu sa protokolom filtriranja.

---

## 2. Osnovni pojmovi

* **Aspektna kategorija:** Određena karakteristika ili osobina mobilnog uređaja definisana taksonomijom od 11 kategorija (npr. *Baterija*, *Kamera*, *Ekran*, *Hardver*...).

* **Aspektni izraz (*Aspect Target / Span*):** Reč ili imenička sintagma u tekstu koja direktno označava predmet vrednovanja.

* *Pravilo granice:* Označava se **isključivo naziv aspekta**, bez reči koje izražavaju sentiment (npr. u *"odlična glavna kamera"*, označava se samo **`glavna kamera`**).

* **Implicitni aspekt (`NULL` Target):** Situacija u kojoj autor iznosi jasan vrednosni stav o nekoj karakteristici uređaja, ali naziv samog aspekta nije eksplicitno pomenut u tekstu.

* *Primer:* *"Radi veoma brzo i ništa ne koči."* $\rightarrow$ Kategorija: **Performanse**, Target: **`NULL`**, Sentiment: **Pozitivan**.

---

## 3. Taksonomija kategorija

### Zbirni pregled taksonomije

| Kategorija | Obuhvata (Primeri pojmova) | Ne obuhvata |
| --- | --- | --- |
| **`Baterija`** | Autonomija, kapacitet (mAh), trajanje, brzo/bežično punjenje, punjač. | Performanse, brzina sistema, procesor. |
| **`Kamera`** | Foto/video kvalitet, zum, noćni/portretni režim, stabilizacija, AI obrada. | Prikaz slike na ekranu. |
| **`Ekran`** | Tip panela (AMOLED/LCD), rezolucija, osvežavanje (Hz), osvetljenje, boje. | Izgled i dimenzije celog uređaja. |
| **`Memorija`** | RAM, interna memorija (GB), podrška za SD karticu. | Optimizacija, bagovi, brzina rada. |
| **`Zvučnici`** | Kvalitet i jačina zvuka, stereo zvučnici, mikrofon, kvalitet poziva, 3.5mm ulaz. | Bluetooth slušalice, bagove pri pozivu/razgovoru koji se ne odnose na kvalitet zvuka. |
| **`Izgled`** | Dizajn, boja, dimenzije, težina, materijali izrade, ergonomija. | Veličina ili kvalitet samog ekrana. |
| **`Hardver`** | Procesor, čipset, komponente, zagrevanje i hlađenje, senzori, otisak prsta, priključci, signal. | OS, aplikacije, bagove (Softver); opštu brzinu bez pomena komponenata (Performanse). |
| **`Softver`** | OS (Android/iOS), korisnički interfejs (UI), ažuriranja, bagovi, optimizacija, aplikacije, igrice. | RAM i internu memoriju. |
| **`Performanse`** | Brzina rada, fluidnost, seckanje, odziv sistema (bez pominjanja procesora/OS-a). | Eksplicitne hardverske čipove ili softverske bagove. |
| **`Cena`** | Cena, odnos cene i kvaliteta (*Value for Money*), isplativost, troškovi servisa. | Akcije prodavnica i dostupnost. |
| **`Opšta ocena`** | Utisak o telefonu u celini, zadovoljstvo kupovinom, preporuka. | Ocene konkretnih pojedinačnih funkcija. |

---

### Detaljne definicije kategorija

#### 1. Baterija

Obuhvata trajanje baterije, autonomiju, kapacitet (npr. 5000 mAh), brzinu i tehnologije punjenja (brzo, bežično, obrnuto punjenje), punjač u pakovanju i potrošnju energije.

* *Primer:* *"Baterija traje dva dana."* $\rightarrow$ **Pozitivan**

* *Primer:* *"Punjač ne stiže u kutiji."* $\rightarrow$ **Negativan**

#### 2. Kamera

Obuhvata glavnu, prednju, ultraširoku i telefoto kameru, kvalitet fotografija i videa, noćni i portretni režim, fokus, optički/digitalni zum, HDR i AI obradu slika.

* *Primer:* *"Noćne fotografije su mutne."* $\rightarrow$ **Negativan**

* *Primer:* *"Zum me je oduševio."* $\rightarrow$ **Pozitivan**

#### 3. Ekran

Obuhvata tip panela (AMOLED, OLED, LCD), rezoluciju, osvežavanje (60Hz, 120Hz), osvetljenost, prikaz boja, kontrast, osetljivost na dodir (touch) i zaštitno staklo.

* *Primer:* *"Boje su izuzetno žive i tačne."* $\rightarrow$ **Pozitivan**

* *Primer:* *"Slabo se vidi na direktnom suncu."* $\rightarrow$ **Negativan**

#### 4. Memorija

Obuhvata kapacitet RAM memorije, internu memoriju za skladištenje i proširivost putem SD kartice.

* *Primer:* *"128 GB je premalo za današnje potrebe."* $\rightarrow$ **Negativan**

#### 5. Zvučnici

Obuhvata kvalitet i jačinu reprodukcije zvuka sa zvučnika, stereo balans, mikrofon, kvalitet zvuka tokom telefonskih poziva i prisustvo 3.5mm priključka za slušalice.

* *Primer:* *"Zvuk tokom poziva je čist, a zvučnici glasni."* $\rightarrow$ **Pozitivan**

#### 6. Izgled

Obuhvata vizuelni dizajn, boju, dimenzije, masu (težinu), debljinu, primenjene materijale (staklo, aluminijum, plastika) i subjektivni osjećaj u ruci (ergonomiju).

* *Primer:* *"Telefon prelepo izgleda ali je malo težak."* $\rightarrow$ **Konflikt**

#### 7. Hardver

Obuhvata fizičke elektronske komponente: procesor (čipset/GPU), senzore (čitač otiska, Face ID), mrežne modeme (signal, Wi-Fi, Bluetooth, GPS), fizičke priključke, vibracioni motor, kao i zagrevanje uređaja i sistem hlađenja.

* *Primer:* *"Čitač otiska prsta često ne prepoznaje prst."* $\rightarrow$ **Negativan**

* *Primer:* *"Telefon se jako zagreva tokom igranja."* $\rightarrow$ **Negativan**

#### 8. Softver

Obuhvata operativni sistem (Android, iOS, MIUI, MagicOS...), korisnički interfejs (UI), sistemska ažuriranja, optimizaciju, sistemske aplikacije, AI alate za obradu i ponašanje aplikacija, kao i aplikacije treće strane i igrice.

* *Primer:* *"Interfejs je pregledan i redovno stižu ažuriranja."* $\rightarrow$ **Pozitivan**

* *Primer:* *"Aplikacija baguje i ruši se."* $\rightarrow$ **Negativan**

#### 9. Performanse

Obuhvata opštu brzinu rada uređaja, fluidnost u radu, odziv sistema i prisustvo seckanja/kočenja kada u tekstu **nije eksplicitno pomenut procesor ili softverski bag**.

* *Primer:* *"Skrolovanje je glatko i sve radi brzo."* $\rightarrow$ **Pozitivan**

* *Primer:* *"Telefon povremeno secka pri prelasku iz aplikacije u aplikaciju."* $\rightarrow$ **Negativan**

#### 10. Cena

Obuhvata cenu uređaja (cena, pare, novac), ocenu isplativosti (*Value for Money*), troškove zvaničnih popravki i servisa.

* *Primer:* *"Odličan telefon za ove pare."* $\rightarrow$ **Target: pare** $\rightarrow$ **Pozitivan**

#### 11. Opšta ocena uređaja

Korisnički utisak o telefonu u celini, celokupno zadovoljstvo kupovinom i opšta preporuka bez izdvajanja konkretnog aspekta.

* *Primer:* *"Najbolji telefon koji sam imao, sve preporuke."* $\rightarrow$ **Pozitivan**

---

## 4. Sentiment

Sentiment predstavlja vrednosni stav autora prema specificiranom aspektu:

* **Pozitivan:** Autor izražava zadovoljstvo, pohvalu ili potvrđuje kvalitet aspekta.

* **Negativan:** Autor izražava nezadovoljstvo, kritiku, razočaranje ili ukazuje na manu.

* **Neutralan:** Autor navodi umerenu ocenu bez izražene emocije (npr. *"ekran je prosek"*) ILI vrši **normalizaciju očekivanog ponašanja** (npr. *"greje se pri brzom punjenju, ali to je normalno i očekivano"*).

* **Konfliktan:** Unutar iste rečenice/misli za *isti aspekt* istovremeno postoje i izrazito pozitivne i izrazito negativne ocene (npr. *"kamera pravi odlične slike po danu, ali je noću očajna"*).

---

## 5. Specijalna metodološka pravila

### Pravilo 1: Eksplecitnost i nepretpostavljanje

Anotira se **samo ono što je napisano**. Ne pretpostavlja se implicitno nezadovoljstvo ako autor daje samo suvu činjenicu bez vrednosnog prideva (npr. *"Baterija je kapaciteta 5000 mAh"* ili *"Stiglo je novo ažuriranje"* se **NE anotiraju**).

### Pravilo 2: Pravilo opovrgavanja glasina (*Debunking Rule*)

Kada autor u tekstu izričito **demantuje ili opovrgne poznatu manu, kritiku ili glasinu sa foruma** u vezi sa telefonom (npr. pritužbe na grejanje ili curenje zvuka), tom aspektu se dodeljuje **Pozitivan** sentiment pod odgovarajućom kategorijom.

* *Primer:* *"Stvarno nisam primetila da se telefon greje, to su izmišljotine."* $\rightarrow$ Target: **`NULL`** (Hardver), Sentiment: **Pozitivan**.
* *Primer:* *"Priče da svi čuju sagovornika se rešavaju smanjivanjem zvuka slušalice."* $\rightarrow$ Target: **`zvuka slušalice`** (Zvučnici), Sentiment: **Pozitivan**.

### Pravilo 3: Single-Entity pravilo (Poređenje sa drugim uređajima)

Anotiraju se **isključivo stavovi koji se odnose na telefon koji je predmet recenzije**.

* **Anotira se:** Ako poređenje sadrži direktnu evaluaciju ciljanog telefona (npr. *"Kamera na ovom telefonu je bolja nego na iPhone 15"* $\rightarrow$ Target: **`Kamera`**, Sentiment: **Pozitivan**).

* **Filtrira se (Šum):** Svako pominjanje eksternog telefona ili OS-a koje ne daje direktnu ocenu našeg telefona (npr. *"Video je bolji na ajfonu"* ili *"Korisnik sam iOS-a već 5 godina"*) se **potpuno filtrira kao šum**.

### Pravilo 4: Višestruki targeti pod jednim pridevom

Kada autor nabroji više aspekata povezanih jednim vrednosnim pridavom, svaki eksplicitni target dobija sopstveni ulaz u tabeli.

* *Primer:* *"Ekran, brzina i zvučnici su vrhunski."*
1. Target: **`Ekran`** (Ekran) $\rightarrow$ **Pozitivan**
2. Target: **`brzina`** (Performanse) $\rightarrow$ **Pozitivan**
3. Target: **`zvučnici`** (Zvučnici) $\rightarrow$ **Pozitivan**

---

## 6. Protokol za filtriranje šuma (Šta se NE anotira)

Sledeće kategorije teksta moraju se **strikno ignorisati i potisnuti iz ABSA ekstrakcije**:

1. **Polemike i komentari forumaša (*Meta & Forum Dispute Noise*):**
* *"100 ljudi, 100 ćudi"*, *"Neki traže dlaku u jajetu"*, *"Uzela sam telefon u A1 pre neki dan"*.


2. **Dnevnici potrošnje i navike (*Usage Journal & Context Noise*):**
* *"Od 07h do 13h potrošilo se 30% baterije uz slušanje muzike..."*, *"Ne igram igrice pa ne znam..."*.
*(Služi samo kao opis uslova testiranja, anotira se samo zaključak o trajanju baterije).*

3. **Pitanja i traženje tehničke podrške (*Support & Troubleshooting Noise*):**
* *"Da li još nekome potamni ekran u YouTube-u kada skroluje?"*, *"Zna li neko kako se ovo rešava?"*.
*(Deskriptivna pitanja bez iznošenja evaluativnog sentimenta o samom telefonu).*

4. **Lične navike i profil upotrebe (*User Habit Noise*):**
* *"Olovku ne koristim jer nemam naviku"*.

---

## 7. Pravila za označavanje aspektnog izraza (*Span*)

1. Označava se **samo imenička sintagma** (npr. `kamera`, `prednja kamera`, `trajanje baterije`).

2. U span se **NE uključuju** pridevi sentimenta (npr. u *"odličan ekran"*, označava se samo **`ekran`**).

3. Implicitni aspekt nema span (target se označava kao **`NULL`**).

4. Zamenice koje se odnose na telefon ne označavaju se kao span, već se anotira implicitni aspekt.

5. Redosled ekstrakcije: Aspekte obavezno ekstrahovati i navesti u JSON izlazu u striktno hronološkom redosledu kako se pojavljuju u tekstu od početka do kraja.

---

## 8. Primer kompletne anotacije teksta

**Tekst:**

> *"Telefon je super. Ekran i zvučnici su vrhunski. Baterija izdrži dan i po što je odlično. Priče da se previše greje nisu tačne, nisam primetila taj problem. Video snimak je bolji na ajfonu, ali meni to nije bitno. Sve u svemu, odličan kupovina."*

### Ekstrahovana ABSA Tabela:

| Aspect Target (*Span*) | Kategorija | Sentiment | Obrazloženje / Opis u tekstu |
| --- | --- | --- | --- |
| **`Telefon`** | **`Opšta ocena`** | **`Pozitivan`** | Izraz *"Telefon je super"*. |
| **`Ekran`** | **`Ekran`** | **`Pozitivan`** | Izraz *"vrhunski"*. |
| **`zvučnici`** | **`Zvučnici`** | **`Pozitivan`** | Izraz *"vrhunski"*. |
| **`Baterija`** | **`Baterija`** | **`Pozitivan`** | Izraz *"izdrži dan i po što je odlično"*. |
| **`NULL`** *(Implicit)* | **`Hardver`** | **`Pozitivan`** | **Debunking Rule:** Autor demantuje glasine o pregrevanju (*"priče nisu tačne, nisam primetila"*). |
| **`kupovina`** | **`Cena`** | **`Pozitivan`** | Izraz *"odlična kupovina"* (odnos uloženo/dobijeno). |

### Filtrirani šum:

* *"Video snimak je bolji na ajfonu, ali meni to nije bitno."* $\rightarrow$ **Single-Entity Noise:** Direktno poređenje sa eksternim modelom bez ocene našeg telefona.