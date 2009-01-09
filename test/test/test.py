#import time
import umddevice
import pdb

#ini='cbl_sg_ant-py.ini'
#ini='cbl_sg_ant.ini'
ini='umd-nport1.ini'

#c=umddevice.UMDCable()
c=umddevice.UMDNPort()
c.Init(ini,1)
fehler,wert=c.setFreq(9e8)
##if fehler != 0:
##    print 'Fehler:',fehler,'=>', c.ErrorDict[fehler]
##else:
##    for w in ('S21', 's21', 'S 21', 's11', 'f44'):
##        err, obj=c.getData(w)
##        if err == 0:
##            print obj
##            print obj.time
##        else:
##            print 'Fehler bei der Objekterstellung; Nr.', err, '=>', c.ErrorDict[err]
w='S42'
err, obj=c.getData(w)
print obj, err
##

#print wert, fehler
c.Quit()
