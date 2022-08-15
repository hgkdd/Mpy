import time
import sys
sys.path.insert(0, '\\herbrig\\new-umddevice')
sys.path.insert(0, '\\herbrig\\scuq')
import new_umddevice
#import pdb

#ini="m://umd-config//largeMSC//ini//umd-rs-fsp.ini"
ini="m://umd-config//largeMSC//ini//umd-rs-fsp-real.ini"

c=new_umddevice.UMDSpectrumanalyzer()
c.Init(ini,1)

##print '\n\n+++++++++++++Zero - Test+++++++++++++'
##fehler,wert=c.Zero(1)
##print 'on:',fehler, wert
##time.sleep(3)
##fehler,wert=c.Zero(0)
##print 'off:',fehler, wert
##time.sleep(3)

##print '\n\n+++++++++++++setFreq-Test+++++++++++++'
##for f in (100000000, 80000000, 90000000):
##    fehler,wert=c.setFreq(f)
##    print 'f=',f,':',fehler, wert
##    time.sleep(5)

##print '\n\n+++++++++++++Trigger - Test+++++++++++++'
##fehler,wert=c.Trigger()
##print fehler, wert
##time.sleep(3)

##print '\n\n+++++++++++++getDataNB - Test+++++++++++++'
###time.sleep(5)
##fehler,wert=c.getDataNB(1)
##print fehler, wert.v.r, wert.v.i

##print '\n\n+++++++++++++getData - Test+++++++++++++'
###time.sleep(5)
##fehler,wert=c.getData()
##print fehler, wert.v.r, wert.v.i

##print '\n\n+++++++++++++SetCenterFreq + GetCenterFreq - Test+++++++++++++'
##fehler,wert=c.SetCenterFreq(100000000)
##print 'set:',fehler, wert
##time.sleep(2)
##fehler,wert=c.GetCenterFreq()
##print 'get:', fehler, wert
##fehler,wert=c.SetCenterFreq(200000000)
##print 'set:',fehler, wert
##time.sleep(2)
##fehler,wert=c.GetCenterFreq()
##print 'get:', fehler, wert

##print '\n\n+++++++++++++SetSpan + GetSpan - Test+++++++++++++'
##fehler,wert=c.SetSpan(200000000)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetSpan()
##print 'get:', fehler, wert
##fehler,wert=c.SetSpan(400000000)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetSpan()
##print 'get:', fehler, wert

##print '\n\n+++++++++++++SetStartFreq + GetStartFreq - Test+++++++++++++'
##fehler,wert=c.SetStartFreq(100000000)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetStartFreq()
##print 'get:', fehler, wert
##fehler,wert=c.SetStartFreq(300000000)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetStartFreq()
##print 'get:', fehler, wert

##print '\n\n+++++++++++++SetStopFreq + GetStopFreq - Test+++++++++++++'
##fehler,wert=c.SetStopFreq(1000000000)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetStopFreq()
##print 'get:', fehler, wert
##fehler,wert=c.SetStopFreq(2000000000)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetStopFreq()
##print 'get:', fehler, wert

##print '\n\n+++++++++++++SetRBW + GetRBW - Test+++++++++++++'
##fehler,wert=c.SetRBW(100000)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetRBW()
##print 'get:', fehler, wert
##fehler,wert=c.SetRBW(300000)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetRBW()
##print 'get:', fehler, wert

##print '\n\n+++++++++++++SetVBW + GetVBW - Test+++++++++++++'
##fehler,wert=c.SetVBW(100000)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetVBW()
##print 'get:', fehler, wert
##fehler,wert=c.SetVBW(300000)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetVBW()
##print 'get:', fehler, wert

##print '\n\n+++++++++++++SetRefLevel + GetRefLevel - Test+++++++++++++'
##fehler,wert=c.SetRefLevel(-30, 0)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetRefLevel()
##print 'get:', fehler, wert
##fehler,wert=c.SetRefLevel(-20, 0)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetRefLevel()
##print 'get:', fehler, wert

##print '\n\n+++++++++++++SetAtt + GetAtt  + SetAttAuto - Test+++++++++++++'
##fehler,wert=c.SetAtt(20)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetAtt()
##print 'get:', fehler, wert
##
##
##fehler,wert=c.SetAtt(30)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetAtt()
##print 'get:', fehler, wert
##
##fehler,wert=c.SetAttAuto(1)
##print 'auto:', fehler, wert
##fehler,wert=c.GetAtt()
##print 'get:', fehler, wert

##print '\n\n+++++++++++++SetPreAmp + GetPreAmp - Test+++++++++++++' ####???
##fehler,wert=c.SetPreAmp(10)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetPreAmp()
##print 'get:', fehler, wert

##print '\n\n+++++++++++++SetDetector + GetDetector - Test+++++++++++++'
##fehler,wert=c.SetDetector(3)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetDetector()
##print 'get:', fehler, wert
##fehler,wert=c.SetDetector(4)
##print 'set:', fehler, wert
##time.sleep(2)
##fehler,wert=c.GetDetector()
##print 'get:', fehler, wert

##print '\n\n+++++SetTrace + GetTrace + SetTraceMode + GetTraceMode -  Test+++++'
##fehler,wert=c.SetTrace(1)
##print 'SetTrace:', fehler, wert
##fehler,wert=c.GetTrace()
##print 'GetTrace:', fehler, wert
##fehler,wert=c.SetTraceMode(0)
##print 'SetTraceMode:', fehler, wert
##fehler,wert=c.GetTraceMode()
##print 'GetTraceMode:', fehler, wert

##fehler,wert=c.SetTrace(2)
##print 'SetTrace:', fehler, wert
##fehler,wert=c.GetTrace()
##print 'GetTrace:', fehler, wert
##fehler,wert=c.SetTraceMode(1)
##print 'SetTraceMode:', fehler, wert
##fehler,wert=c.GetTraceMode()
##print 'GetTraceMode:', fehler, wert

##fehler,wert=c.SetTrace(3)
##print 'SetTrace:', fehler, wert
##fehler,wert=c.GetTrace()
##print 'GetTrace:', fehler, wert
##fehler,wert=c.SetTraceMode(2)
##print 'SetTraceMode:', fehler, wert
##fehler,wert=c.GetTraceMode()
##print 'GetTraceMode:', fehler, wert

##print '\n\n+++++++++++++SetSweepCount + GetSweepCount - Test+++++++++++++'
##fehler,wert=c.SetTrace(1)
##fehler,wert=c.SetTraceMode(2)
##fehler,wert=c.SetSweepCount(50)
##print 'set:', fehler, wert
##fehler,wert=c.GetSweepCount()
##print 'get:', fehler, wert

##print '\n\n+++++++++++++SetSweepTime + GetSweepTime - Test+++++++++++++'
##time.sleep(2)
##fehler,wert=c.SetSweepTime(0.005)
##print 'set:', fehler, wert
##fehler,wert=c.GetSweepTime()
##print 'get:', fehler, wert
##time.sleep(2)
##fehler,wert=c.SetSweepTime(0.05)
##print 'set:', fehler, wert
##fehler,wert=c.GetSweepTime()
##print 'get:', fehler, wert

print('\n\n+++++++++++++GetSpectrum - Test+++++++++++++')
#time.sleep(5)
fehler,wert=c.GetSpectrum(0)
print((fehler, wert.l, wert.v, wert.u))

##print '\n\n+++++++++++++GetSpectrumNB - Test+++++++++++++'
###time.sleep(5)
##fehler,wert=c.GetSpectrumNB(0, 1)
##print fehler, wert.l, wert.v, wert.u



##fehler,wert=c.SetTraceMode(5)
##print '\nSetTraceMode:', fehler,wert
###0 clear
###1 view
###2 avg
###4 maxh
###5 minh

c.Quit()
