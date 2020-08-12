from setuptools import setup, find_packages
from os import environ

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.6.b5"
__status__ = "Prototype"

try:
    __version__ = environ["CHERRYDOOR_VERSION"]
except KeyError:
    pass
if "CI" in environ:
    with open("VERSION", "w", encoding="utf-8") as f:
        if __version__[0] == "v":
            f.write(__version__)
        else:
            f.write(f"v{__version__}")

with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read().replace(
        "cherrydoor/static",
        f"https://raw.githubusercontent.com/wisniowa56/cherrydoor/v{__version__}/cherrydoor/static/",
    )

setup(
    name="Cherrydoor",
    version=__version__,
    author="oplik0",
    description=(
        "An overengineered rfid lock manager created for my school community. Made for Raspberry Pi connected with another microcontroler that send and recieved rfid data via UART"
    ),
    long_description=readme,
    long_description_content_type="text/markdown",
    license="MIT",
    keywords="wisniowasu mongodb flask rfid lock cherrydoor",
    url="https://github.com/oplik0/cherrydoor",
    packages=find_packages(),
    include_package_data=True,
    package_data={"": ["templates/*", "static/*/*", "static/images/*/*"]},
    zip_safe=False,
    scripts=["scripts/cherrydoor-install"],
    entry_points={"console_scripts": ["cherrydoor = cherrydoor.cli:cherrydoor"]},
    python_requires=">=3.7",
    install_requires=[
        "aiohttp>=3.6",
        "aioserial>=1.3",
        "argon2-cffi>=19",
        "motor>=2.1",
        "confuse>=1.3",
    ],
    extras_require={"speedups": ["aiodns>=1.1", "Brotli", "cchardet",]},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: Home Automation",
        "Topic :: Terminals :: Serial",
        "Topic :: Internet :: WWW/HTTP",
    ],
)
