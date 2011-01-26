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
        self.stir_ipos      = []
        self.E_ncomp        = len(dct[self.freq_freqs[0]][self.stir_pos[0]])
        self.Emeas_freqstir = numpy.zeros((self.E_ncomp,self.stir_npos,self.freq_nfreq))  # measured E-values for each frequency and stirrer position
        self.Enorm_freqstir = numpy.zeros((self.E_ncomp,self.stir_npos,self.freq_nfreq))    
        self.Emean_stirpos  = numpy.zeros((self.E_ncomp,self.stir_npos))                  # mean E-values over all frequencies of each stirrer position
        self.Emean_NStirpos = numpy.zeros((self.E_ncomp,self.stir_npos,self.freq_nfreq))
        self.Enorm_var      = numpy.zeros((self.E_ncomp,self.stir_npos))
        self.Emean_var      = numpy.zeros((self.E_ncomp,self.stir_npos))
        self.Epearson       = numpy.zeros((self.E_ncomp,self.stir_npos,self.stir_npos))
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
        # for i in range(0,self.E_ncomp,1):
            # self.Emean_stirpos[i,:]=numpy.mean(self.Enorm_freqstir[i,:,:],axis=1)
        # print self.Emean_stirpos
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
        temp.set_label('Ex_norm (Ex / Ex_mean_stirpos')
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
    
    def PlotPearsonCorrelationCoefficientExyzNormalized(self):
        pearson1=numpy.zeros((360))
        pearson2=numpy.zeros((360))
        pos0=0
        posn=0
        for pos in self.stir_pos:
            cc1=scipy.stats.pearsonr(self.Enorm_freqstir[0,0,:],self.Enorm_freqstir[0,pos,:])
            cc2=scipy.stats.pearsonr(self.Enorm_freqstir[0,pos0,:],self.Enorm_freqstir[0,pos,:])
            pearson1[pos]=cc1[0]
            pearson2[pos]=cc2[0]
            if cc2[0]<0.8:
                pos0=pos
                posn=posn+1
        #
        pylab.ylabel('Ex_norm Pearson correlation coefficient')
        pylab.xlabel('Stirrer position')
        pylab.plot(self.stir_pos,pearson1)
        pylab.plot(self.stir_pos,pearson2,label='%d independent positions'%posn)
        pylab.axis([0,360,-1,1])
        pylab.legend(loc='best')
        pylab.savefig('003_ExnormPearsonCorrelation.png',dpi=200)
        pylab.show()
        #
        pearson1=numpy.zeros((360))
        pearson2=numpy.zeros((360))
        pos0=0
        posn=0
        for pos in self.stir_pos:
            cc1=scipy.stats.pearsonr(self.Enorm_freqstir[1,0,:],self.Enorm_freqstir[1,pos,:])
            cc2=scipy.stats.pearsonr(self.Enorm_freqstir[1,pos0,:],self.Enorm_freqstir[1,pos,:])
            pearson1[pos]=cc1[0]
            pearson2[pos]=cc2[0]
            if cc2[0]<0.8:
                pos0=pos
                posn=posn+1
        #
        pylab.ylabel('Ey_norm Pearson correlation coefficient')
        pylab.xlabel('Stirrer position')
        pylab.plot(self.stir_pos,pearson1)
        pylab.plot(self.stir_pos,pearson2,label='%d independent positions'%posn)
        pylab.axis([0,360,-1,1])
        pylab.legend(loc='best')
        pylab.savefig('003_EynormPearsonCorrelation.png',dpi=200)
        pylab.show()
        #
        pearson1=numpy.zeros((360))
        pearson2=numpy.zeros((360))
        pos0=0
        posn=0
        for pos in self.stir_pos:
            cc1=scipy.stats.pearsonr(self.Enorm_freqstir[2,0,:],self.Enorm_freqstir[2,pos,:])
            cc2=scipy.stats.pearsonr(self.Enorm_freqstir[2,pos0,:],self.Enorm_freqstir[2,pos,:])
            pearson1[pos]=cc1[0]
            pearson2[pos]=cc2[0]
            if cc2[0]<0.8:
                pos0=pos
                posn=posn+1
        #
        pylab.ylabel('Ez_norm Pearson correlation coefficient')
        pylab.xlabel('Stirrer position')
        pylab.plot(self.stir_pos,pearson1)
        pylab.plot(self.stir_pos,pearson2,label='%d independent positions'%posn)
        pylab.axis([0,360,-1,1])
        pylab.legend(loc='best')
        pylab.savefig('003_EznormPearsonCorrelation.png',dpi=200)
        pylab.show()
        
    def PlotVarianceExyzNormalized(self):    
        for i in range(0,self.E_ncomp,1):
            for j in range(0,self.stir_npos):
                self.Enorm_var[i,j]=scipy.stats.tvar(self.Enorm_freqstir[i,j,:])
        #
        pylab.ylabel('Variance of normalized Exyz')
        pylab.xlabel('Stirrer position')
        pylab.plot(self.stir_pos,self.Enorm_var[0],label='Ex_norm')
        pylab.plot(self.stir_pos,self.Enorm_var[1],label='Ey_norm')
        pylab.plot(self.stir_pos,self.Enorm_var[2],label='Ez_norm')
        pylab.axis([0,360,0,2])
        pylab.legend()
        pylab.savefig('004_VarianceEnormOverStirpos.png',dpi=200)
        pylab.show()
        
    def PlotEmeanOverNStirpos(self):
        pylab.xlabel('Frequency f in Hz')
        pylab.ylabel('N Stirrer positions')
        pylab.pcolor(self.freq_freqs,self.stir_pos,self.Emean_NStirpos[0,:,:])
        temp=pylab.colorbar()
        temp.set_label('Ex_mean over N stirrer positions in V/m')
        pylab.axis([self.freq_start,self.freq_stop,0,360])
        pylab.savefig('005_EmeanOverNStirpos.png',dpi=200)
        pylab.show()
        #
        pylab.xlabel('Frequency f in Hz')
        pylab.ylabel('Ex_mean over N stirrer positions in V/m')
        pylab.plot(self.freq_freqs,self.Emean_NStirpos[0,0,:],label='1')
        pylab.plot(self.freq_freqs,self.Emean_NStirpos[0,359,:],label='360')
        pylab.legend()
        pylab.savefig('005_EmeanOverNStirpos_1_360.png',dpi=200)
        pylab.show()
    
    def PlotVarianceExyzMeanOverNStirrerposition(self):
        for i in range(0,self.E_ncomp,1):
            for j in range(0,self.stir_npos):
                self.Emean_var[i,j]=scipy.stats.tvar(self.Emean_NStirpos[i,j,:])
        #
        pylab.ylabel('Variance Exyz_mean')
        pylab.xlabel('Stirrer position')
        pylab.plot(self.stir_pos,self.Emean_var[0,:],label='Ex_mean')
        pylab.plot(self.stir_pos,self.Emean_var[1,:],label='Ey_mean')
        pylab.plot(self.stir_pos,self.Emean_var[2,:],label='Ez_mean')
        pylab.axis([0,360,0,1])
        pylab.legend()
        pylab.savefig('006_VarExyzmeanOverNStirpos.png',dpi=200)
        pylab.show()
        
    

    def NindependentStirrerPositions(self):
        for i in range(0,self.E_ncomp,1):
            print 'var E: %f'%scipy.stats.tvar(self.Emeas_freqstir[i,:,:])
            print 'var <E>n: %f'%scipy.stats.tvar(self.Emean_stirpos[i,:])
            N=scipy.stats.tvar(self.Emeas_freqstir[i,:,:])/scipy.stats.tvar(self.Emean_stirpos)
            print 'N= %f' %N
    
    
    def temp(self):
        ipos=[]
        pos0=0
        for pos in self.stir_pos:
            pcc=scipy.stats.pearsonr(self.Enorm_freqstir[1,pos0,:],self.Enorm_freqstir[1,pos,:])
            print pos, pcc
            if pcc[0]<0.8:
                pos0=pos
                ipos.append(pos)
        print ipos        
        #
        ipos=numpy.array(ipos)
        nipos=len(ipos)
        print nipos
        
        ipos_pcc=numpy.zeros((nipos,nipos))
        for i in range(0,nipos,1):
            for j in range(0,nipos,1):
                pcc=scipy.stats.pearsonr(self.Enorm_freqstir[1,ipos[i],:],self.Enorm_freqstir[1,ipos[j],:])
                ipos_pcc[i,j]=pcc[0]
        #        
        
    def PlotEpearsonOverStirrerposition(self):
        for i in self.stir_pos:
            for j in self.stir_pos:
                pcc=scipy.stats.pearsonr(self.Enorm_freqstir[0,i,:],self.Enorm_freqstir[0,j,:])
                self.Epearson[0,i,j]=pcc[0]
        #       
        pylab.xlabel('Stirrer position')
        pylab.ylabel('Stirrer position')
        pylab.pcolor(self.stir_pos,self.stir_pos,self.Epearson[0,:,:])
        temp=pylab.colorbar()
        temp.set_label('Ex Pearson Correction Coefficient')
        pylab.savefig('007_ExPearsonCorrectionCoeff.png',dpi=200)
        pylab.show()
                
    
    def test(self):
        print 'Algorithm 1:'
        for i in range(0,3,1):
            positions=sorted(self.data[self.freq_freqs[0]].keys())
            #positions=[0,1,2,3,4,5,6,7,8,9,10]
            pos0index=0
            pos1index=1
            #
            while len(positions)>pos1index:
                pos1index=pos0index+1
                pcc=scipy.stats.pearsonr(self.Enorm_freqstir[i,positions[pos0index],:],self.Enorm_freqstir[i,positions[pos1index],:])
                #print positions
                #print len(positions), pos0index, positions[pos0index], pos1index, positions[pos1index], pcc[0]
                if pcc[0]>0.7:
                    del positions[pos1index]
                else:
                    pos0index=pos1index
            #
            print 'E-Component %d: %d positions' %(i,len(positions))
        
        
        print 'Algorithm 2:'
        for i in range(0,3,1):
            positions=sorted(self.data[self.freq_freqs[0]].keys())
            #positions=[0,1,2,3,4,5,6,7,8,9,10]
            pos0index=0
            pos1index=1
            #
            while len(positions)>pos0index:
                pos1index=pos0index+1
                while len(positions)>pos1index:
                    pcc=scipy.stats.pearsonr(self.Enorm_freqstir[i,positions[pos0index],:],self.Enorm_freqstir[i,positions[pos1index],:])
                    #print positions
                    #print len(positions), pos0index, positions[pos0index], pos1index, positions[pos1index], pcc[0]
                    if pcc[0]>0.7:
                        del positions[pos1index]
                    else:
                        pos1index=pos1index+1
                pos0index=pos0index+1
            #
            print 'E-Component %d: %d positions' %(i,len(positions))
            
            
            
            
                    
                
            
        
    
if __name__ == '__main__':
    
    infile = sys.argv[1]
    dct=pickle.load(file(infile, 'rb'))
    
    D=Data(dct)
      
    #D.PlotExyzOverFreqAndStirpos()
    #D.PlotScatterDiagram()
    D.PlotPearsonCorrelationCoefficientExyzNormalized()
    #D.PlotVarianceExyzNormalized()
    #D.PlotEmeanOverNStirpos()
    #D.PlotVarianceExyzMeanOverNStirrerposition()
    #D.NindependentStirrerPositions()
    #D.PlotEpearsonOverStirrerposition()
    #D.temp()
    D.test()