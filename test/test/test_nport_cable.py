#import time
import sys
sys.path.insert(0, '..')
import mpylab.device.device as device
#import pdb

#ini='m://umd-config//smallMSC//ini//cbl_sg_ant-py.ini'
ini='m://umd-config//smallMSC//ini//cbl_sg_ant.ini'
#ini='m://umd-config//largeMSC//ini//umd-nport1.ini'

#c=umddevice.UMDCable()
c=device.NPort()
c.Init(ini,3)
fehler,wert=c.SetFreq(9e8)
##if fehler != 0:
##    print 'Fehler:',fehler,'=>', c.ErrorDict[fehler]
##else:
##    for w in ('S21'):#, 's99', 'S31', 'S42', 'f44'):
##        print '\n\n'
##        err, obj=c.getData(w)
##        if err == 0:
##            print obj
##            print obj.time
##        else:
##            print 'Fehler bei der Objekterstellung; Nr.', err, '=>', c.ErrorDict[err]
w='S21'
err, obj=c.GetData(w)
print(obj)


#print wert, fehler
c.Quit()
