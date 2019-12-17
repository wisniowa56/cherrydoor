<h1 align="center">cherrydoor</h1>
<p align="center">
  <img src="static/images/logo/logo.svg">
</p>
Prosta webaplikacja do zarządzania i przeglądania statystyk wykorzystania zamka RFID korzystająca z Flaska i MongoDB.

## Obecny stan (v0.1)
* Podstawa backendu działa
* Działa REST API
* Są zalążki websocketów
* Jest działające logowanie
* Fronetnd jest w zupełnych powijakach - poza logowaniem ma niedziałający wykres i opcję  dodawania użytkowników.

## Instalacja i uruchamianie:
1. Zainstaluj MongoDB ([instrukcje](https://docs.mongodb.com/manual/administration/install-community/)) i uruchom.
2. Sklonuj projekt `git clone https://github.com/oplik0/cherrydoor cherrydoor` i przejdź do powstałego folderu `cd cherrydoor`
3. Zainstaluj wymagane biblioteki: `pip install -r requirements.txt`
4. (opcjonalne, ale zalecane) Zmień klucz w [`config.json`](config.json) na losową wartość. Możesz ją wygenerować np. w Pythonie:
```Python
>>> import os
>>> os.urandom(24)
```
5. Uruchom serwer flaska: `python3 main.py`
6. Ciesz się aplikacją która praktycznie jeszcze nie działa :)

Aby stworzyć pierwszego użytkownika obecnie trzeba usunąć `@login_required` nad `def register():` w [`routes.py`](cherrydoor/routes.py#L33) - albo stworzyć go manualnie w bazie danych
