from os.path import dirname, join
import re

import setuptools


def find_version(fname):
    """Attempts to find the version number in the file names fname.
    Raises RuntimeError if not found.

    """
    version = ""
    with open(fname, "r") as fp:
        regex = re.compile(r'__version__ = [\'"]([^\'"]*)[\'"]')
        for line in fp:
            m = regex.match(line)
            if m:
                version = m.group(1)
                break
    if not version:
        raise RuntimeError("Cannot find version information")
    return version


def read(fname):
    with open(join(dirname(__file__), fname), "r") as fh:
        return fh.read()


setuptools.setup(
    name="sqlalchemy-easy-profile",
    version=find_version("easy_profile/__init__.py"),
    author="Dmitri Vasilishin",
    author_email="vasilishin.d.o@gmail.com",
    description="An easy profiler for SQLAlchemy queries",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/dmvass/sqlalchemy-easy-profile",
    packages=setuptools.find_packages(exclude=("test*",)),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords=["sqlalchemy", "easy", "profile", "profiler", "profiling"],
    install_requires=["sqlalchemy<1.5", "sqlparse>=0.3.0"],
    tests_require=["coverage"],
    extras_require={"dev": ["tox"]}
)
