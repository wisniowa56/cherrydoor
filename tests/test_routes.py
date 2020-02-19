import pytest
from flask import url_for
from cherrydoor import User, routes


@pytest.mark.usefixtures("client_class")
class TestSuite:
    def test_login_page(self):
        assert self.client.get(url_for("login")).status_code == 200

    def test_flask_login(self):
        routes.login_user(User(username="admin"), remember=True)
        assert self.client.get(url_for("index")).status_code in [200, 302]

    def test_register(self):
        assert self.client.post(
            url_for("register"), data={"username": "admin1", "password": "admin1"}
        ).status_code in [200, 302]
