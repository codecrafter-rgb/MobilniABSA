# Cilj anotacije

Cilj ovog projekta je izrada skupa podataka za aspektnu analizu sentimenta (Aspect-Based Sentiment Analysis -- ABSA) koji se sastoji od komentara korisnika o mobilnim telefonima.

Za svaki komentar potrebno je:

1.  prepoznati koji aspekti telefona se pominju,

2.  odrediti sentiment prema svakom od tih aspekata.

Sentiment se određuje posebno za svaki aspekt, a ne za komentar u celini.

# Osnovni pojmovi

**Aspekt** predstavlja određenu karakteristiku ili osobinu mobilnog uređaja o kojoj korisnik iznosi mišljenje, zapažanje ili opis. U okviru ovog projekta aspekti odgovaraju unapred definisanim kategorijama, kao što su baterija, kamera, ekran, softver i druge.

Jedan komentar može sadržati:

- nijedan aspekt,

- jedan aspekt,

- više različitih aspekata.

Primer: *Kamera je odlična, ali baterija traje kratko.*

U ovom primeru prepoznaju se dva aspekta:

- Kamera -- pozitivan sentiment,

- Baterija -- negativan sentiment.

Sentiment se određuje zasebno za svaki aspekt, a ne za komentar u celini.

**Aspektni izraz** predstavlja reč ili grupu reči u komentaru koja direktno označava aspekt o kojem autor govori. To može biti jedna reč ili sintagma.

Primeri aspektnih izraza: kamera, prednja kamera, trajanje baterije, brzo punjenje. Kod anotacije se označava **samo aspektni izraz**, bez reči koje izražavaju sentiment.

Primer: *Odlična kamera pravi veoma kvalitetne fotografije.*

Aspektni izraz je kamera, dok pridev odlična predstavlja pokazatelj sentimenta i ne smatra se delom aspektnog izraza.

**Sentiment** predstavlja stav ili mišljenje autora komentara prema određenom aspektu uređaja. Sentiment se određuje **posebno za svaki aspekt** koji se pojavljuje u komentaru.

U ovom projektu koriste se sledeće oznake sentimenta:

- **Pozitivan** -- autor izražava zadovoljstvo aspektom.

- **Negativan** -- autor izražava nezadovoljstvo aspektom.

- **Neutralan** -- aspekt se pominje, ali bez izraženog pozitivnog ili negativnog stava.

- **Konfliktan** -- za isti aspekt istovremeno postoje pozitivne i negativne ocene, pri čemu nije moguće odrediti dominantan sentiment prema pravilima anotacije.

**Aspektna kategorija** predstavlja unapred definisanu grupu kojoj pripada aspektni izraz. Više različitih aspektnih izraza može pripadati istoj kategoriji.

Primer:

- trajanje baterije,

- kapacitet baterije,

- brzo punjenje,

pripadaju kategoriji baterija.

**Implicitni aspekt.** Aspekt ne mora uvek biti eksplicitno pomenut u tekstu. U pojedinim komentarima korisnik izražava stav o određenoj karakteristici uređaja, iako naziv aspekta nije direktno naveden.

Primer: *Radi veoma brzo i ništa ne koči.*

Naziv aspekta nije eksplicitno navede, ali se komentar odnosi na kategoriju softver.

U ovakvim slučajevima anotira se odgovarajuća aspektna kategorija i sentiment, dok se aspektni izraz označava kao **implicitan** (NULL), u skladu sa mogućnostima alata za anotaciju.

# Kategorije aspekata

### Baterija

Kategorija baterija obuhvata sve komentare koji se odnose na potrošnju energije, punjenje i tehnologije povezane sa baterijom.

Obuhvata:

- trajanje baterije

- autonomiju baterije

- kapacitet baterije (npr. 5000 mAh)

- brzo punjenje

- bežično punjenje

- obrnuto punjenje

- punjač

- brzinu punjenja

- potrošnju energije

Ne obuhvata:

- performanse uređaja

- brzinu rada sistema

- procesor

Primeri:

- Baterija traje dva dana.

- Brzo se puni.

- Troši bateriju previše.

- Ima bateriju od 5000 mAh. (neutralan)

- Punjač nije uključen u pakovanje.

### Kamera

Kategorija kamera obuhvata sve komentare koji se odnose na fotografisanje, snimanje videa i funkcionalnosti kamera.

Obuhvata:

- glavnu kameru

- prednju kameru

- ultraširoku kameru

- telefoto kameru

- kvalitet fotografija

- kvalitet videa

- noćni režim

- portretni režim

- fokus

- autofokus

- stabilizaciju

- optički ili digitalni zum

- HDR

- obradu fotografija

Ne obuhvata:

- ekran (ako se govori o prikazu slike na ekranu)

Primeri:

- Slike su odlične.

- Prednja kamera je loša.

- Noćne fotografije su mutne.

- Ima tri kamere. (neutralan)

- Zum je odličan.

### Ekran

Kategorija ekran obuhvata sve što se odnosi na prikaz slike i fizičke karakteristike ekrana.

Obuhvata:

- AMOLED

- OLED

- LCD

- IPS

- rezoluciju

- veličinu ekrana

- osvetljenje

- boje

- kontrast

- osvežavanje (60 Hz, 90 Hz, 120 Hz...)

- odziv ekrana

- touch (osetljivost na dodir)

- Gorilla Glass ili drugu zaštitu

- čitljivost na suncu

Ne obuhvata:

- izgled telefona u celini

- dimenzije uređaja (osim kada se eksplicitno govori o veličini ekrana)

Primeri:

- Ekran je fenomenalan.

- Boje su odlične.

- Slabo se vidi na suncu.

- Ima ekran od 6.7 inča. (neutralan)

- 120 Hz pravi veliku razliku.

### Memorija

Kategorija memorija obuhvata sve što se odnosi na skladištenje podataka i radnu memoriju uređaja.

Obuhvata:

- RAM memoriju

- internu memoriju

- prostor za skladištenje

- proširenje memorije SD karticom

- dostupni slobodni prostor

Ne obuhvata:

- brzinu rada sistema

- optimizaciju

- bagove

Primeri:

- 128 GB je sasvim dovoljno.

- Premalo memorije.

- Ima 12 GB RAM-a. (neutralan)

- Nema podršku za SD karticu.

### Zvučnici

Kategorija zvučnici obuhvata sve što se odnosi na reprodukciju i snimanje zvuka.

Obuhvata:

- kvalitet zvuka

- jačinu zvuka

- stereo zvučnike

- balans zvuka

- mikrofon

- kvalitet razgovora

- zvuk tokom poziva

- priključak za slušalice (3.5 mm)

Ne obuhvata:

- Bluetooth slušalice

- kvalitet muzike koji zavisi od aplikacije

Primeri:

- Stereo zvučnici su odlični.

- Mikrofon je loš.

- Zvuk je previše tih.

- Ima stereo zvučnike. (neutralan)

### Izgled

Kategorija izgled obuhvata fizičke karakteristike uređaja i subjektivni utisak o njegovom dizajnu.

Obuhvata:

- dizajn

- izgled uređaja

- boju

- dimenzije

- težinu

- debljinu

- kvalitet izrade

- materijale (plastika, aluminijum, staklo)

- ergonomiju

Ne obuhvata:

- veličinu ekrana

- kvalitet ekrana

Primeri:

- Telefon izgleda prelepo.

- Pretežak je.

- Ne sviđa mi se plastika.

- *Telefon je tanak.* (u zavisnosti od konteksta može biti pozitivan ili neutralan)

### Hardver

Kategorija hardver obuhvata fizičke elektronske komponente uređaja, njihove performanse i funkcije koje ne pripadaju nekoj preciznijoj kategoriji.

Obuhvata:

- procesor i čipset

- grafički procesor (GPU)

- performanse uređaja kada su jasno povezane sa hardverskim komponentama

- zagrevanje i sistem hlađenja

- modem, antene i kvalitet prijema signala

- Wi-Fi, Bluetooth, NFC i GPS

- senzore, čitač otiska prsta i prepoznavanje lica

- USB i druge priključke, osim priključka za slušalice

- fizičke tastere i vibracioni motor

Ne obuhvata:

- operativni sistem, aplikacije, bagove i optimizaciju (Softver)

- brzinu rada kada iz komentara nije jasno da je uzrok hardverska komponenta (Softver)

- RAM i internu memoriju (Memorija)

- bateriju, ekran, kameru i zvučnike, jer za njih postoje posebne kategorije

- dizajn, materijale i kvalitet izrade kućišta (Izgled)

Primeri:

- Procesor je veoma brz. (pozitivan)

- Telefon se previše zagreva tokom igranja. (negativan)

- Signal je odličan i u zatvorenom prostoru. (pozitivan)

- Čitač otiska prsta često ne prepoznaje prst. (negativan)

- Telefon podržava NFC. (neutralan)

- Ima Snapdragon 8 Gen 3 procesor. (neutralan)

Ako komentar samo navodi da telefon radi brzo, sporo ili secka, bez pominjanja procesora ili druge hardverske komponente, bira se kategorija **Softver**. Kategorija **Hardver** bira se kada je hardverska komponenta eksplicitno navedena ili kada se komentar nedvosmisleno odnosi na fizičku komponentu, kao što su signal, senzor, priključak ili zagrevanje.

### Softver

Kategorija softver obuhvata operativni sistem, korisnički interfejs i ponašanje sistema tokom korišćenja.

Obuhvata:

- Operativni sistem telefona (Android, iOS, MIUI, EMUI itd)

- ažuriranja

- bagove

- optimizaciju

- brzinu rada sistema

- korisnički interfejs

- preinstalirane aplikacije

Ne obuhvata:

- RAM

- internu memoriju

Primeri:

- Telefon baguje.

- Sve radi veoma brzo.

- Dobija redovna ažuriranja.

- Interfejs je pregledan.

- Previše nepotrebnih aplikacija.

### Cena

Kategorija cena obuhvata finansijski aspekt uređaja.

Obuhvata:

- cenu uređaja

- odnos cene i kvaliteta

- isplativost kupovine

- vrednost za novac

- troškove popravke

Ne obuhvata:

- dostupnost uređaja

- akcije prodavnica

Primeri:

- Preskup je.

- Odličan telefon za ove pare.

- Ne vredi.

- Popravka je preskupa.

### Opšta ocena uređaja

Kategorija Opšta ocena uređaja koristi se kada korisnik iznosi utisak o telefonu kao celini, bez izdvajanja konkretnog aspekta.

Obuhvata:

- ukupan utisak

- zadovoljstvo uređajem

- preporuku za kupovinu

- ocenu uređaja u celini

- dugotrajnost uređaja, ukoliko nije vezana za određeni aspekt

Ne obuhvata:

- komentare koji se jasno odnose na neku drugu kategoriju

Primeri:

- Odličan telefon.

- Ne preporučujem ovaj uređaj.

- Najbolji telefon koji sam imao.

- Veoma sam zadovoljan kupovinom.

- Telefon je prosečan. (neutralan)

# Oznake sentimenta

Za svaki aspekt bira se jedna od četiri vrednosti.

## Pozitivan

Autor jasno izražava zadovoljstvo aspektom.

Primeri:

- *Kamera pravi odlične slike.*

- *Ekran je fantastičan.*

## Negativan

Autor jasno izražava nezadovoljstvo.

Primeri:

- *Kamera je katastrofa.*

- *Baterija se isprazni za nekoliko sati.*

## Neutralan

Autor govori o aspektu bez jasne pozitivne ili negativne ocene.

Primeri:

- *Telefon ima bateriju od 5000 mAh.*

- *Ima tri kamere.*

- *Ekran je AMOLED.*

Napomena: Neutralan sentiment označava informaciju, a ne mešovit sentiment.

## Konflikt

Autor govori o aspektu navodeći i pozitivne i negativne ocene u podjednakoj meri.

Primer:

- *Kamera je odlična po danu, ali noću veoma loša.*

# Pravila anotacije

1.  Anotira se samo ono što je napisano. Nikad ne treba pretpostavljati mišljenje autora.

> Primer: *Baterija traje jedan dan.*
>
> Primer ilustruje neutralan sentiment, nikako ne pretpostavljati da korisniku smeta što baterija traje jedan dan.

2.  Jedan komentar može imati više aspekata.

Primer: *Kamera je odlična, baterija loša.*

Sentiment kamere je pozitivan, baterije negativan.

3.  Jedan aspekt dobija samo jednu oznaku sentimenta.

> Ako postoje i pozitivni i negativni delovi za isti aspekt, bira se dominantni sentiment. Ukoliko nije moguće odrediti dominantan aspekt, bira se konflikt.
>
> Primer: *Kamera je odlična po danu, ali noću veoma loša.*
>
> Kamera → Konflikt (zbog jednakog broja pozitivnih i negativnih)

4.  U slučaju ironije koja je očigledna, sentiment je negativan.

5.  Obratiti pažnju na negacije (*Nije loša kamera* = pozitivan sentiment).

6.  Aspekt ne treba označavati ako se pominje samo usput (*Kupio sam telefon zbog kamere*).

7.  Obratiti pažnju na oređenja (Kamera je gora nego na ajfonu = negativan sentiment).

8.  Ukoliko autor opisuje karakteristiku uređaja na način koji predstavlja vrednosni sud (npr. *ekran je mali*, *telefon je težak*, *predebeo je*), anotira se odgovarajući sentiment.

# Pravila za označavanje aspektnog izraza

1.  Označava se samo imenica ili imenička sintagma (kamera, prednja kamera).

2.  Kod izraza od nekoliko reči označiti celu sintagmu (trajanje baterije, kvalitet zvuka).

3.  Implicitni aspekt se označava kao NULL - *Jedva preživi dan.*

4.  Ako se upotrebljavaju zamenice a jasno je na šta se odnosi sud, aspekt se označava kao NULL.

# Primeri
