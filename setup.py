from setuptools import setup, find_packages

setup(
    name="racedbcli",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="CLI tools for interacting with RaceDB",
    long_description=open("racedbcli/README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/stuartlynne/racedbcli",  # Change to your repo URL
    packages=find_packages(),
    package_data={
    },
    include_package_data=True,
    install_requires=[
        "autopage",
        "psycopg2",
        "subprocess"
        "requests",
        "openpyxl",
        "pandas",
        "click",
        "BeautifulSoup",
    ],
    entry_points={
        "console_scripts": [
            "racedbcli=racedbcli.cli.__init__:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
