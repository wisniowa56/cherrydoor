[![python tests](https://github.com/wisniowa56/cherrydoor/workflows/python%20tests/badge.svg)](https://github.com/wisniowa56/cherrydoor/actions?query=workflow%3A%22python+tests%22)
[![Maintainability](https://api.codeclimate.com/v1/badges/7b05467561774c611f8c/maintainability)](https://codeclimate.com/github/oplik0/cherrydoor/maintainability)
[![HitCount](http://hits.dwyl.io/wisniowa56/cherrydoor.svg)](http://hits.dwyl.io/wisniowa56/cherrydoor)

<h1 align="center">cherrydoor</h1>
<p align="center">
  <img src="cherrydoor/static/images/logo/logo.svg">
</p>
Prosta webaplikacja do zarządzania i przeglądania statystyk wykorzystania zamka RFID korzystająca z Flaska i MongoDB.

## Instalacja i uruchamianie:

1. Zaintaluj `Cherrydoor` korzystając z pip i pypi:

```bash
pip3 install Cherrydoor
```

Albo pobierz wheel danego wydania i zainstaluj:

```bash
pip3 install ./Cherrydoor-<version>-py3-none-any.whl
```

2. Doinstaluj dodatkowe zależności i skonfiguruj trochę rzeczy korzystając z wbudowanego skryptu instalacyjnego:

```bash
cherrydoor install
```

3. Program powinien być już uruchomiony przez systemd na porcie 5000. Możesz go restartować/zatrzymywać/itp. korzystając z `systemctl --user <komenda> cherrydoor`. Jeśli chcesz go uruchomić bez korzystania z usługi, skorzystaj ze skryptu `cherrydoor start`.
