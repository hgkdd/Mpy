import pickle
import sys

name = sys.argv[1]

msc = pickle.load(open(name, 'rb'), encoding='latin1')

ef = msc.rawData_MainCal['empty']['efield']
freqs = ef.keys()
#freqs.sort()

for f in sorted(freqs):
    tees = ef[f].keys()
    tees = [int(t.strip('[]')) for t in tees]
    # tees.sort()
    for t in sorted(tees):
        pees = sorted(ef[f]['[%d]' % t].keys())
        # pees.sort()
        nns = [len(ef[f]['[%d]' % t][p]) for p in pees]
        print("%.2f\t%d\t%s\t%s" % (f, t, pees, nns))
