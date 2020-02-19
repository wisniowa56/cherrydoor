import pytest
from cherrydoor import app as cherryapp


@pytest.fixture
def app():
    return cherryapp
