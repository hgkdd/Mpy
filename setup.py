from ez_setup import use_setuptools
use_setuptools()
import os
from setuptools import setup, find_packages
import version

ver=''
version.remember_version(ver)

setup(name='mpy',
      version=version.get_version(),
      author="Hans Georg Krauthaeuser",
      author_email="hgk@ieee.org",
      description='instrument control framework',
      license='All rights reserved',
      url='http://tu-dresden.de/et/tet',
      install_requires=[#'numpy',
                        #'scipy',
                        #'pydot',
                        #'pyvisa',
                        #'ply'
                        ],
      packages=find_packages(),
      #package_dir = {'':'mpy'},
      #data_files=[('mpy', ['mpy/LICENSE'])],
      )
