reset
#set macros
fname='cable.dat'
iname='cable.ini'
set parametric

set grid
set style data lines
plot '<  python ../dataparser.py '.fname using 2:3 t fname,\
     '<  python cbl-test.py '.iname using 2:3 t iname


