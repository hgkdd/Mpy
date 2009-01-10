from distutils.core import setup
import version

ver=''
version.remember_version(ver)

setup(name='mpy',
      version=version.get_version(),
      author="Hans Georg Krauthaeuser",
      author_email="hgk@ieee.org",
      description='instrument control framework',
      licence='All rights reserved',
      packages=['mpy', 
                'mpy.device', 
                'mpy.env', 
                'mpy.tools'],
      )
