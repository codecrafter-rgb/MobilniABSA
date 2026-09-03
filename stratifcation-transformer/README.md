# Fiksna stratifikovana podela

Skripta `create_stratified_split.py` pravi jednu determinističku podelu
anotiranih komentara na 80% trening, 10% validaciju i 10% test.

Za stratifikaciju koristi 44 binarne kombinacije `kategorija::sentiment` iz
polja `aspect_categories` i dodatnu oznaku `STATUS::NE`. Duplikati se ne
grupišu.

Pokretanje iz korena projekta:

```bash
python3 stratifcation-transformer/create_stratified_split.py
```

Podrazumevani ulaz je `annotation/annotations.json`, a rezultat se čuva u
`stratifcation-transformer/output/`:

- `train.json`
- `validation.json`
- `test.json`
- `split_manifest.json`

Manifest sadrži originalne indekse komentara, SHA-256 ulaznog fajla i broj
svake oznake po podskupu. Ista tri izlazna fajla treba koristiti za RoBERTa i
BERTić, kao i za two-stage i multi-head pristup.

Drugi ulazni ili izlazni put mogu se zadati eksplicitno:

```bash
python3 stratifcation-transformer/create_stratified_split.py \
  --input annotation/annotations.json \
  --output-dir stratifcation-transformer/output \
  --seed 42
```

Skripta ne prepisuje postojeće rezultate bez opcije `--overwrite`.
