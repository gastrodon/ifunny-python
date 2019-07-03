from setuptools import setup, find_packages

setup(
    name = "ifunny",
    version = "0.1.0",
    description = "iFunny interface in python",
    url = "https://github.com/basswaver/iFunny",
    download_url = "https://github.com/basswaver/iFunny/tarball/master",
    author = "Zero",
    author_email = "dakoolstwunn@gmail.com",
    licence = "GPLv3",
    classifiers = [
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
    ],
    keywords = [
        "ifunny",
        "ifunny-bot",
        "bot",
        "reverse-engineering",
        "api",
        "http-api",
        "python",
        "python3",
        "python3.x",
        "unofficial"
    ],
    install_requires = [
        "requests",
        "websocket-client"
    ],
    setup_requires = [
        "wheel"
    ],
    packages = find_packages(),

)
