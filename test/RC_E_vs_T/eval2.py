from scuq import *
import sys
import cPickle as pickle
import pylab
import numpy
import scipy
import scipy.stats

class Data(object):
    def __init__(self, dct):
        self.data           = dct
        self.freq_freqs     = numpy.array(sorted(dct.keys()))
        self.freq_nfreq     = len(self.freq_freqs)
        self.freq_start     = self.freq_freqs[0]
        self.freq_stop      = self.freq_freqs[self.freq_nfreq-1]
        self.stir_pos       = numpy.array(sorted(dct[self.freq_freqs[0]].keys()))
        self.stir_npos      = len(self.stir_pos)
        self.E_ncomp        = len(dct[self.freq_freqs[0]][self.stir_pos[0]])
        self.Emeas_freqstir = numpy.zeros((self.E_ncomp,self.stir_npos,self.freq_nfreq))  # measured E-values for each frequency and stirrer position
        self.Enorm_freqstir = numpy.zeros((self.E_ncomp,self.stir_npos,self.freq_nfreq))    
        self.Emean_stirpos  = numpy.zeros((self.E_ncomp,self.stir_npos))                  # mean E-values over all frequencies of each stirrer position
        self.Emean_NStirpos = numpy.zeros((self.E_ncomp,self.stir_npos,self.freq_nfreq))
        
        #
        self.Exnorm_Var     = numpy.zeros((360))
        self.Ex_mean_Var    = numpy.zeros((360)) 
        #
        for i in range(0,self.E_ncomp,1):
            for j in range(0,self.stir_npos,1):
                for k in range(0,self.freq_nfreq,1):
                    self.Emeas_freqstir[i,j,k] = self.data[self.freq_freqs[k]][self.stir_pos[j]][i].get_expectation_value_as_float()
        
        #
        for i in range(0,self.E_ncomp,1):
            self.Emean_stirpos[i,:]=numpy.mean(self.Emeas_freqstir[i,:,:],axis=1)
            for j in range(0,self.stir_npos,1):
                self.Enorm_freqstir[i,j,:]=self.Emeas_freqstir[i,j,:]/self.Emean_stirpos[i,j]
        #
        for i in range(0,self.E_ncomp,1):
            for j in range(0,self.stir_npos,1):
                self.Emean_NStirpos[i,j,:]=numpy.mean(self.Enorm_freqstir[i,0:j+1,:],axis=0)        
                
    def PlotExyzOverFreqAndStirpos(self):
        pylab.xlabel('Frequency f in Hz')
        pylab.ylabel('Stirrer position in degree')
        pylab.pcolor(self.freq_freqs,self.stir_pos,self.Emeas_freqstir[0,:,:])
        temp=pylab.colorbar()
        temp.set_label('Ex in V/m')
        pylab.axis([self.freq_start,self.freq_stop,0,360])
        pylab.savefig('001_ExOverFreqStirpos.png',dpi=200)
        pylab.show()
        #
        pylab.xlabel('Frequency f in Hz')
        pylab.ylabel('Stirrer position in degree')
        pylab.pcolor(self.freq_freqs,self.stir_pos,self.Emeas_freqstir[1,:,:])
        temp=pylab.colorbar()
        temp.set_label('Ey in V/m')
        pylab.axis([self.freq_start,self.freq_stop,0,360])
        pylab.savefig('001_EyOverFreqStirpos.png',dpi=200)
        pylab.show()
        #
        pylab.xlabel('Frequency f in Hz')
        pylab.ylabel('Stirrer position in degree')
        pylab.pcolor(self.freq_freqs,self.stir_pos,self.Emeas_freqstir[2,:,:])
        temp=pylab.colorbar()
        temp.set_label('Ez in V/m')
        pylab.axis([self.freq_start,self.freq_stop,0,360])
        pylab.savefig('001_EzOverFreqStirpos.png',dpi=200)
        pylab.show()
        #
        pylab.xlabel('Frequency f in Hz')
        pylab.ylabel('Stirrer position in degree')
        pylab.pcolor(self.freq_freqs,self.stir_pos,self.Enorm_freqstir[0,:,:])
        temp=pylab.colorbar()
        temp.set_label('Ex_norm in V/m')
        pylab.axis([self.freq_start,self.freq_stop,0,360])
        pylab.savefig('001_ExnormOverFreqStirpos.png',dpi=200)
        pylab.show()
        
    def PlotScatterDiagram(self):
        pylab.xlabel('Ex for stirrer position 0')
        pylab.ylabel('Ex for stirrer position 1, 3 & 10')
        pylab.plot(self.Enorm_freqstir[0,0,:],self.Enorm_freqstir[0,1,:].transpose(), label='1')
        pylab.plot(self.Enorm_freqstir[0,0,:],self.Enorm_freqstir[0,3,:].transpose(),label='3')
        pylab.plot(self.Enorm_freqstir[0,0,:],self.Enorm_freqstir[0,10,:].transpose(),label='10')
        pylab.legend()
        pylab.savefig('002_ExnormScatterDiagramStirpos.png',dpi=200)
        pylab.show()
        #
        pearson1=numpy.zeros((360))
        pearson2=numpy.zeros((360))
        pos0=0
        for pos in self.stir_pos:
            cc1=scipy.stats.pearsonr(self.Enorm_freqstir[0,0,:],self.Enorm_freqstir[0,pos,:])
            cc2=scipy.stats.pearsonr(self.Enorm_freqstir[0,pos0,:],self.Enorm_freqstir[0,pos,:])
            pearson1[pos]=cc1[0]
            pearson2[pos]=cc2[0]
            if cc2[0]<0.5:
                pos0=pos+1
        #
        pylab.ylabel('Pearson correlation coefficient')
        pylab.xlabel('Stirrer position')
        pylab.plot(self.stir_pos,pearson1)
        pylab.plot(self.stir_pos,pearson2)
        pylab.axis([0,360,-1,1])
        pylab.savefig('002_ExnormPearsonCorrelation.png',dpi=200)
        pylab.show()
        #
        for j in range(0,self.stir_npos):
            self.Exnorm_Var[j]=scipy.stats.tvar(self.Enorm_freqstir[0,j,:])
        #
        pylab.ylabel('Variance Ex_norm')
        pylab.xlabel('Stirrer position')
        pylab.plot(self.stir_pos,self.Exnorm_Var)
        pylab.savefig('002_VarExOverStirpos.png',dpi=200)
        pylab.show()
        #
        pearson1=numpy.zeros((360))
        pearson2=numpy.zeros((360))
        pos0=0
        for pos in self.stir_pos:
            cc1=scipy.stats.pearsonr(self.Enorm_freqstir[1,0,:],self.Enorm_freqstir[1,pos,:])
            cc2=scipy.stats.pearsonr(self.Enorm_freqstir[1,pos0,:],self.Enorm_freqstir[1,pos,:])
            pearson1[pos]=cc1[0]
            pearson2[pos]=cc2[0]
            if cc2[0]<0.5:
                pos0=pos+1
        #
        pylab.ylabel('Pearson correlation coefficient')
        pylab.xlabel('Stirrer position')
        pylab.plot(self.stir_pos,pearson1)
        pylab.plot(self.stir_pos,pearson2)
        pylab.axis([0,360,-1,1])
        pylab.savefig('002_EynormPearsonCorrelation.png',dpi=200)
        pylab.show()
        #
        
        
    def PlotEmeanOverNStirpos(self):
        pylab.xlabel('Frequency f in Hz')
        pylab.ylabel('N Stirrer positions')
        pylab.pcolor(self.freq_freqs,self.stir_pos,self.Emean_NStirpos[0,:,:])
        temp=pylab.colorbar()
        temp.set_label('Ex_mean over N stirrer positions in V/m')
        pylab.axis([self.freq_start,self.freq_stop,0,360])
        pylab.savefig('003_EmeanOverNStirpos.png',dpi=200)
        pylab.show()
        #
        pylab.xlabel('Frequency f in Hz')
        pylab.ylabel('Ex_mean over N stirrer positions in V/m')
        pylab.plot(self.freq_freqs,self.Emean_NStirpos[0,0,:],label='1')
        pylab.plot(self.freq_freqs,self.Emean_NStirpos[0,359,:],label='360')
        pylab.legend()
        pylab.savefig('003_EmeanOverNStirpos_1_360.png',dpi=200)
        pylab.show()
        #
        for j in range(0,self.stir_npos):
            self.Ex_mean_Var[j]=scipy.stats.tvar(self.Emean_NStirpos[0,j,:])
        #
        pylab.ylabel('Variance Ex_mean')
        pylab.xlabel('Stirrer position')
        pylab.plot(self.stir_pos,self.Ex_mean_Var)
        pylab.savefig('003_VarExmeanOverNStirpos.png',dpi=200)
        pylab.show()
    
 
    
 
if __name__ == '__main__':
    
    infile = sys.argv[1]
    dct=pickle.load(file(infile, 'rb'))
    
    D=Data(dct)
      
    #D.PlotExyzOverFreqAndStirpos()
    D.PlotScatterDiagram()
    #D.PlotEmeanOverNStirpos()
     
     
  