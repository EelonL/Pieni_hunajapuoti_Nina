# Hunajapuoti-demo

Pieni Pythonilla tehty Streamlit-verkkokauppademo hunajapuodille.

## Ominaisuudet
- tuotelista
- ostoskori
- asiakastietojen syöttö
- tilauksen tallennus CSV-tiedostoon
- yksinkertainen tilausnäkymä ylläpitoa varten

## Käynnistys

1. Luo virtuaaliympäristö (valinnainen)
2. Asenna riippuvuudet:

```bash
pip install -r requirements.txt
```

3. Käynnistä sovellus:

```bash
streamlit run app.py
```

## Tiedostot
- `app.py` – pääsovellus
- `products.csv` – tuotteet
- `orders.csv` – tallennetut tilaukset

## Ideoita seuraavaan versioon
- tuotekuvat
- varastosaldojen automaattinen päivitys tilauksen jälkeen
- sähköposti-ilmoitus uudesta tilauksesta
- admin-kirjautuminen
- maksutavan lisääminen
