import os
from distutils.core import setup
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
      packages=['mpy', 
                'mpy.device', 
                'mpy.env', 
                'mpy.tools'],
      data_files=[('mpy', ['mpy/LICENSE'])],
      )
