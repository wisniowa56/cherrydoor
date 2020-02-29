[![Build status](https://github.com/oplik0/cherrydoor/workflows/python/badge.svg)](https://github.com/oplik0/cherrydoor/actions?query=workflow%3Atest)
[![Maintainability](https://api.codeclimate.com/v1/badges/7b05467561774c611f8c/maintainability)](https://codeclimate.com/github/oplik0/cherrydoor/maintainability)
[![HitCount](http://hits.dwyl.io/oplik0/cherrydoor.svg)](http://hits.dwyl.io/oplik0/cherrydoor)

<h1 align="center">cherrydoor</h1>
<p align="center">
  <img src="static/images/logo/logo.svg">
</p>
Prosta webaplikacja do zarządzania i przeglądania statystyk wykorzystania zamka RFID korzystająca z Flaska i MongoDB.

## Obecny stan (v0.1)

- Podstawa backendu działa
- Działa REST API
- Działa websocket
- Jest działające logowanie
- Działa większość frontendu - brakuje zarządzania administratorami i ustawień przerw

## Instalacja i uruchamianie:

1. Sklonuj projekt `git clone https://github.com/oplik0/cherrydoor cherrydoor` i przejdź do powstałego folderu `cd cherrydoor`
2. Uruchom skrypt instalacyjny: `bash install.sh`
3. Jeśli nie jesteś pewien, czy korzystasz z najnowszej wersji aplikacji, wpisz `y` przy pytaniu o aktualizację
4. Wpisz `y` by skonfigurować MongoDB, kolejne `y` by stworzyć pierwszego administratora. Wpisz jego nazwę i hasło.
5. (opcjonalne, ale zalecane) Zmień klucz w [`config.json`](config.json) na losową wartość. Możesz ją wygenerować np. w Pythonie:

```Python
>>> import os
>>> os.urandom(24)
```

5. Uruchom aplikację: `python3 main.py`
