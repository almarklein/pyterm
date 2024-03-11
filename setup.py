import re

from setuptools import find_packages, setup


with open("pyterm/__init__.py", "rb") as fh:
    init_text = fh.read().decode()
    VERSION = re.search(r"__version__ = \"(.*?)\"", init_text).group(1)

setup(
    name="pyterm",
    version=VERSION,
    packages=find_packages(
        exclude=["tests", "tests.*", "examples", "examples.*"]
    ),
    python_requires=">=3.6.0",
    install_requires=[],
    license="MIT",
    description="A Python repl that stays responsive in GUI loops, and has superb debugging support.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Almar Klein",
    author_email="almar.klein@gmail.com",
    # url="https://github.com/not/sure/yet",
    data_files=[("", ["LICENSE"])],
    zip_safe=True,
    entry_points={
        "console_scripts": [
            "pyterm = pyterm:cli",
        ],
    },
)
