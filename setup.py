import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setuptools.setup(
    name='mpy-hgkTUD',
    author="Hans Georg Krauthaeuser",
    author_email="hgk@ieee.org",
    description='instrument control framework',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='http://tu-dresden.de/et/tet',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: all rights reserved",
        "Operating System :: OS Independent",
    ],
    package_dir={"mpy": "src/mpy"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)
