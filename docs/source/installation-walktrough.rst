============================================
Walk Through the Installation Process of mpy 
============================================

Walk Through the Installation Process of mpy
--------------------------------------------

The following walk-through shows the installation process for mpy (and scuq) in a virtual environment beginnig with freshly cloned repositories.::

    user:path > mkdir test-mpy
    user:path > cd test-mpy 
    user:path/test-mpy > hg clone /Volumes/tetemv1/Forschung/Labore/repositories_hgk/scuq 
    destination directory: scuq
    updating to branch default                                                                                                                                      
    43 files updated, 0 files merged, 0 files removed, 0 files unresolved
    user:path/test-mpy > hg clone /Volumes/tetemv1/Forschung/Labore/repositories_hgk/mpy 
    destination directory: mpy
    updating to branch default                                                                                                                                      
    396 files updated, 0 files merged, 0 files removed, 0 files unresolved
    user:path/test-mpy > python3 -m venv venv
    user:path/test-mpy > source venv/bin/activate
    (venv) user:path/test-mpy > pip install -e scuq    
    Obtaining file:///path-to/test-mpy/scuq
    Installing build dependencies ... done
    Checking if build backend supports build_editable ... done
    Getting requirements to build editable ... done
    Preparing editable metadata (pyproject.toml) ... done
    Building wheels for collected packages: scuq-hgk
    Building editable for scuq-hgk (pyproject.toml) ... done
    Created wheel for scuq-hgk: filename=scuq_hgk-0.1-0.editable-py3-none-any.whl size=1581 sha256=a7dc3fa5489c1d31715add869cdb51e5a131c4dc0044ba3e72b4f41ffbb374e4
    Stored in directory: /private/var/folders/88/b_718t6d4tgfg4f1g67wkg8r0000gn/T/pip-ephem-wheel-cache-rv6be28b/wheels/9b/cc/ef/ebfea4cdf61378658b6e3d9bb50cdf88742d1d0866f293222f
    Successfully built scuq-hgk
    Installing collected packages: scuq-hgk
    Successfully installed scuq-hgk-0.1
    (venv) user:path/test-mpy > pip install -r mpy/requirements.txt 
    Collecting bidict
    Using cached bidict-0.22.0-py3-none-any.whl (36 kB)
    Collecting getch
    Using cached getch-1.0-cp310-cp310-macosx_12_0_arm64.whl
    Collecting gpib-ctypes
    Using cached gpib_ctypes-0.3.0-py2.py3-none-any.whl (16 kB)
    Collecting Levenshtein
    Using cached Levenshtein-0.20.2-cp310-cp310-macosx_11_0_arm64.whl (106 kB)
    Collecting numpy
    Using cached numpy-1.23.2-cp310-cp310-macosx_11_0_arm64.whl (13.3 MB)
    Collecting ply
    Using cached ply-3.11-py2.py3-none-any.whl (49 kB)
    Collecting pydot
    Using cached pydot-1.4.2-py2.py3-none-any.whl (21 kB)
    Collecting pyparsing
    Using cached pyparsing-3.0.9-py3-none-any.whl (98 kB)
    Collecting pyserial
    Using cached pyserial-3.5-py2.py3-none-any.whl (90 kB)
    Collecting pyusb
    Using cached pyusb-1.2.1-py3-none-any.whl (58 kB)
    Collecting PyVISA
    Using cached PyVISA-1.12.0-py3-none-any.whl (175 kB)
    Collecting PyVISA-py
    Using cached PyVISA_py-0.5.3-py3-none-any.whl (59 kB)
    Collecting SciPy
    Using cached scipy-1.9.1-cp310-cp310-macosx_12_0_arm64.whl (29.9 MB)
    Collecting simpleeval
    Using cached simpleeval-0.9.12-py2.py3-none-any.whl (14 kB)
    Collecting traits
    Using cached traits-6.4.1-cp310-cp310-macosx_10_9_universal2.whl (5.0 MB)
    Collecting traitsui
    Using cached traitsui-7.4.0-py3-none-any.whl (1.5 MB)
    Collecting rapidfuzz<3.0.0,>=2.3.0
    Downloading rapidfuzz-2.6.1-cp310-cp310-macosx_11_0_arm64.whl (1.5 MB)
    ---------------------------- 1.5/1.5 MB 5.3 MB/s eta 0:00:00
    Collecting typing-extensions
    Using cached typing_extensions-4.3.0-py3-none-any.whl (25 kB)
    Collecting pyface>=7.4.1
    Using cached pyface-7.4.2-py3-none-any.whl (1.3 MB)
    Collecting jarowinkler<2.0.0,>=1.2.0
    Using cached jarowinkler-1.2.1-cp310-cp310-macosx_11_0_arm64.whl (57 kB)
    Installing collected packages: simpleeval, pyserial, ply, gpib-ctypes, getch, typing-extensions, traits, pyusb, pyparsing, numpy, jarowinkler, bidict, SciPy, rapidfuzz, PyVISA, pyface, pydot, traitsui, PyVISA-py, Levenshtein
    Successfully installed Levenshtein-0.20.2 PyVISA-1.12.0 PyVISA-py-0.5.3 SciPy-1.9.1 bidict-0.22.0 getch-1.0 gpib-ctypes-0.3.0 jarowinkler-1.2.1 numpy-1.23.2 ply-3.11 pydot-1.4.2 pyface-7.4.2 pyparsing-3.0.9 pyserial-3.5 pyusb-1.2.1 rapidfuzz-2.6.1 simpleeval-0.9.12 traits-6.4.1 traitsui-7.4.0 typing-extensions-4.3.0
    (venv) user:path/test-mpy > pip install -e mpy
    Obtaining file:///path-to/test-mpy/mpy
    Installing build dependencies ... done
    Checking if build backend supports build_editable ... done
    Getting requirements to build editable ... done
    Preparing editable metadata (pyproject.toml) ... done
    Building wheels for collected packages: mpy-hgkTUD
    Building editable for mpy-hgkTUD (pyproject.toml) ... done
    Created wheel for mpy-hgkTUD: filename=mpy_hgkTUD-0.1.dev316+hdc6350c-0.editable-py3-none-any.whl size=3209 sha256=ab259c8dfb232ad4069ed7300d3e817fd04a40dc493475a93a9d960c3c83b24c
    Stored in directory: /private/var/folders/88/b_718t6d4tgfg4f1g67wkg8r0000gn/T/pip-ephem-wheel-cache-h5fhgia2/wheels/8f/1e/f3/229415052fed5d1f0f674ac00a6c99e4bae22223ce2e07eac7
    Successfully built mpy-hgkTUD
    Installing collected packages: mpy-hgkTUD
    Successfully installed mpy-hgkTUD-0.1.dev316+hdc6350c
    (venv) user:path/test-mpy >

Finish

