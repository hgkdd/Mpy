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
    packages=setuptools.find_packages(),
    #package_dir = {'':'mpy'},
    #data_files=[('mpy', ['mpy/LICENSE'])],
)
