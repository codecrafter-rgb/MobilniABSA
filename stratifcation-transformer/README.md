# Fiksna stratifikovana podela

Folder sadrži dve implementacije podele anotiranih komentara na 80% trening,
10% validaciju i 10% test. Obe koriste `aspect_categories`, ne grupišu
duplikate i zasebno raspoređuju `DA` i `NE` komentare.

## Ručna implementacija

`create_stratified_split.py` koristi ručno implementiran rare-label-first
algoritam. Ne zahteva biblioteku `iterative-stratification`.

```bash
python3 stratifcation-transformer/create_stratified_split.py
```

Rezultat se podrazumevano čuva u
`stratifcation-transformer/output-manual/`.

## Bibliotečka implementacija

`create_stratified_split_iterstrat.py` koristi
`MultilabelStratifiedShuffleSplit` iz biblioteke
`iterative-stratification==0.1.9`.

```bash
python3 -m pip install -r requirements.txt
python3 stratifcation-transformer/create_stratified_split_iterstrat.py
```

Rezultat se podrazumevano čuva u
`stratifcation-transformer/output-iterstrat/`.

## Rezultati

Obe skripte generišu:

- `train.json`
- `validation.json`
- `test.json`
- `split_manifest.json`

Manifest sadrži izvorne indekse, SHA-256 ulaznog fajla i broj svake oznake po
podskupu. Podela mora nastati pre pravljenja ACSA parova `(komentar,
kategorija)` i treba da bude ista za RoBERTa i BERTić modele.

Kratko poređenje rezultata nalazi se u [`COMPARISON.md`](COMPARISON.md).

Skripte ne prepisuju postojeće rezultate bez opcije `--overwrite`.
