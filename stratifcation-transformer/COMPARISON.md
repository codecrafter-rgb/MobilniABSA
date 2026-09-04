# Poređenje stratifikacije

Obe skripte su proverene nad 17.551 komentarem, sa podelom 80/10/10 i seed-om
42. `DA` komentari stratifikovani su prema 44 kombinacije
`kategorija::sentiment`, dok su `NE` komentari raspoređeni zasebno.

| Rezultat | Ručna implementacija | `iterative-stratification` |
|---|---:|---:|
| Ukupno train/val/test | 14.041 / 1.755 / 1.755 | 14.041 / 1.755 / 1.755 |
| DA train/val/test | 5.163 / 646 / 645 | 5.174 / 640 / 640 |
| NE train/val/test | 8.878 / 1.109 / 1.110 | 8.867 / 1.115 / 1.115 |
| Prosečna apsolutna greška broja oznaka | 0,520 | **0,280** |
| Najveće odstupanje oznake u jednom podskupu | 16,2 | **0,7** |
| Nedostajuće oznake u validaciji/testu | 1 / 4 | 3 / 2 |

Prosečna greška računata je preko 44 oznake i sva tri podskupa. Najveća
razlika je `Opšta ocena::Pozitivan`: ručna verzija daje
1.842/246/214, a bibliotečka 1.842/230/230, naspram idealnih približno
1.842/230/230. Za preostale 43 oznake ukupna greška je jednaka. Ručna verzija
preciznije čuva broj `DA/NE` komentara, dok biblioteka stabilnije čuva
raspodelu ciljnih oznaka.

Za konačne eksperimente preporučena je bibliotečka implementacija, jer je
standardizovana i daje bolju raspodelu oznaka. Obe podele su deterministične,
bez preklapanja i pokrivaju svaki komentar tačno jednom.
