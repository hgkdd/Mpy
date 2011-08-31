import pickle
import itertools
import sys

name=sys.argv[1]

msc=pickle.load(file(name, 'rb'))

ef=msc.rawData_MainCal['empty']['efield']
freqs=ef.keys()
freqs.sort()

for f in freqs:
    tees=ef[f].keys()
    tees=[int(t.strip('[]')) for t in tees]
    tees.sort()
    for t in tees:
        pees=ef[f]['[%d]'%t].keys()
        pees.sort()
        nns=[len(ef[f]['[%d]'%t][p]) for p in pees]
        print "%.2f\t%d\t%s\t%s"%(f, t, pees,nns)
        