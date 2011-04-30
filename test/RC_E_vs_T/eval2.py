from scuq import *
import sys
import cPickle as pickle
import pylab
import numpy
import scipy
import scipy.stats
import ac

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
        self.E_ncomp        = 4 # Ex, Ey, Ez, Eabs # len(dct[self.freq_freqs[0]][self.stir_pos[0]])
        self.Emeas_freqstir = numpy.zeros((self.E_ncomp,self.stir_npos,self.freq_nfreq))  # measured E-values for each frequency and stirrer position
        self.Enorm_freqstir = numpy.zeros((self.E_ncomp,self.stir_npos,self.freq_nfreq))    
        self.Emean_stirpos  = numpy.zeros((self.E_ncomp,self.stir_npos))                  # mean E-values over all frequencies of each stirrer position
        self.Emean_NStirpos = numpy.zeros((self.E_ncomp,self.stir_npos,self.freq_nfreq))
        self.Enorm_var      = numpy.zeros((self.E_ncomp,self.stir_npos))
        self.Emean_var      = numpy.zeros((self.E_ncomp,self.stir_npos))
        self.Epearson       = numpy.zeros((self.E_ncomp,self.stir_npos,self.stir_npos))
        #
        self.Emeas_ACC      = numpy.zeros((self.E_ncomp,self.stir_npos))                  # AutoCorrelationCoeficient from normalized Efield-values
        self.Enorm_PCC1     = numpy.zeros((self.E_ncomp,self.stir_npos))   
        self.Enorm_PCC2     = numpy.zeros((self.E_ncomp,self.stir_npos))   
        #                    
        self.thresholds     = numpy.array([0.9,0.85,0.8,0.75,0.7,0.65,0.6,0.55,0.5,0.45,0.4,0.35])
        self.ISP_ACC        = numpy.zeros((self.E_ncomp,len(self.thresholds)))            # IndependentStirrerPositions from AutoCorrelationCoeficient          
        self.ISP_PCC1       = numpy.zeros((self.E_ncomp,len(self.thresholds))) 
        self.ISP_PCC2       = numpy.zeros((self.E_ncomp,len(self.thresholds))) 
        #
        # Get measured Efield values from pickle-file
        #
        for i in range(0,3,1):
            for j in range(0,self.stir_npos,1):
                for k in range(0,self.freq_nfreq,1):
                    self.Emeas_freqstir[i,j,k] = self.data[self.freq_freqs[k]][self.stir_pos[j]][i].get_expectation_value_as_float()
        #
        # Calculate the absolute value of Efield components
        #
        for j in range(0,self.stir_npos,1):
                for k in range(0,self.freq_nfreq,1):
                    self.Emeas_freqstir[3,j,k]=scipy.sqrt(self.Emeas_freqstir[1,j,k]**2+self.Emeas_freqstir[2,j,k]**2+self.Emeas_freqstir[0,j,k]**2)
        #
        # Normalize Efield values 
        #
        for i in range(0,self.E_ncomp,1):
            self.Emean_stirpos[i,:]=numpy.mean(self.Emeas_freqstir[i,:,:],axis=1)
            for j in range(0,self.stir_npos,1):
                self.Enorm_freqstir[i,j,:]=self.Emeas_freqstir[i,j,:]/self.Emean_stirpos[i,j]
        #
        #
        #
        for i in range(0,3,1):
            for j in range(0,self.stir_npos,1):
                self.Emean_NStirpos[i,j,:]=numpy.mean(self.Enorm_freqstir[i,0:j+1,:],axis=0)        
    
    def CalcAutoCorrCoeffAndNumberOfIndStirPosFromAutoCorrCoeff(self):
        for i in range(0,self.E_ncomp,1):   
            Templist=list(self.Emeas_freqstir[i,:,100]) 
            self.Emeas_ACC[i,:]=numpy.array(list(ac.ac(Templist)))
            #
            for j in range(0,len(self.thresholds),1):
                threshold=self.thresholds[j]
                self.ISP_ACC[i,j]=ac.Nind(Templist,threshold)
        #
        print self.ISP_ACC            
        #
        pylab.rcParams['figure.figsize']=(6,3) 
        pylab.axes([0.125,0.125,0.825,0.825])
        #
        #pylab.title('')
        pylab.ylabel('auto correlation coefficient')
        pylab.xlabel('stirrer position')
        pylab.plot(self.stir_pos,self.Emeas_ACC[0,:],label='Ex')
        pylab.plot(self.stir_pos,self.Emeas_ACC[1,:],label='Ey')
        pylab.plot(self.stir_pos,self.Emeas_ACC[2,:],label='Ez')
        pylab.plot(self.stir_pos,self.Emeas_ACC[3,:],label='Eabs')
        pylab.plot([0,360],[threshold,threshold],'k--')
        pylab.axis([0,360,-1,1])
        pylab.xticks([0,40,80,120,160,200,240,280,320,360])
        pylab.yticks([-1.0,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1.0])
        #pylab.figtext(0.5,0.75,'250MHz',fontsize=12)
        pylab.grid(True)
        pylab.legend(loc='lower center', ncol=6)
        pylab.savefig('001_AutoCorrCoeff_800MHz.png',dpi=200)
        pylab.show()
        #
        pylab.rcParams['figure.figsize']=(6,3) 
        pylab.axes([0.125,0.125,0.825,0.825])
        #
        #pylab.title('')
        pylab.ylabel('independent stirrer positions')
        pylab.xlabel('auto correlation threshold')
        pylab.plot(self.thresholds,self.ISP_ACC[0,:],label='Ex')
        pylab.plot(self.thresholds,self.ISP_ACC[1,:],label='Ey')
        pylab.plot(self.thresholds,self.ISP_ACC[2,:],label='Ez')
        pylab.plot(self.thresholds,self.ISP_ACC[3,:],label='Eabs')
        pylab.axis([1,0.3,0,360])
        pylab.grid(True)
        pylab.legend(loc='lower center', ncol=6)
        pylab.savefig('002_NumberOfIndStirPosFromAutoCorrCoeff_800MHz.png',dpi=200)
        pylab.show()
    
    def PlotPearsonCorrelationCoefficientEnormalized(self):
        for i in range(0,self.E_ncomp,1):   
            pos0=0
            posn=0
            for pos in self.stir_pos:
                temp1=scipy.stats.pearsonr(self.Enorm_freqstir[i,0,:],self.Enorm_freqstir[i,pos,:])
                temp2=scipy.stats.pearsonr(self.Enorm_freqstir[i,pos0,:],self.Enorm_freqstir[i,pos,:])
                self.Enorm_PCC1[i,pos]=temp1[0]
                self.Enorm_PCC2[i,pos]=temp2[0]    
                if temp2[0]<0.37:
                    pos0=pos
                    posn=posn+1    
        #
        pylab.rcParams['figure.figsize']=(6,3.5) 
        pylab.axes([0.125,0.125,0.825,0.825])
        #
        pylab.ylabel('pearson correlation coefficient')
        pylab.xlabel('stirrer position')
        pylab.plot(self.stir_pos,self.Enorm_PCC1[0,:],label='Ex')
        pylab.plot(self.stir_pos,self.Enorm_PCC1[1,:],label='Ey')
        pylab.plot(self.stir_pos,self.Enorm_PCC1[2,:],label='Ez')
        pylab.plot(self.stir_pos,self.Enorm_PCC1[3,:],label='Eabs') 
        pylab.grid(True)
        pylab.legend(loc='lower center', ncol=6)
        pylab.axis([0,360,-1,1])
        pylab.xticks([0,40,80,120,160,200,240,280,320,360])
        pylab.yticks([-1.0,-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1.0])
        pylab.savefig('003_PearsonCorrCoeff_250MHz.png',dpi=200)
        pylab.show()
        #
        pylab.rcParams['figure.figsize']=(6,3.5) 
        pylab.axes([0.125,0.125,0.825,0.825])
        #
        pylab.ylabel('pearson correlation coefficient')
        pylab.xlabel('stirrer position')
        pylab.plot(self.stir_pos,self.Enorm_PCC1[3,:])
        pylab.plot(self.stir_pos,self.Enorm_PCC2[3,:], label='%d independent positions'%posn)
        pylab.plot([0,360],[0.37,0.37],'k--')
        pylab.axis([0,360,-1,1])
        pylab.legend(loc='lower center', ncol=6)
        pylab.savefig('004_EabsPearsonCorrCoeff_250MHz.png',dpi=200)
        pylab.show()
    
    def CalcIndependentStirrerPositionsPearson(self):
        for n in range(0,len(self.thresholds),1):
            pearson=self.thresholds[n]
            #
            # Algorithm 1:
            for i in range(0,4,1):
                positions=sorted(self.data[self.freq_freqs[0]].keys())
                pos0index=0
                pos1index=1
                #
                while len(positions)>pos1index:
                    pcc=scipy.stats.pearsonr(self.Enorm_freqstir[i,positions[pos0index],:],self.Enorm_freqstir[i,positions[pos1index],:])
                    if pcc[0]>pearson:
                        del positions[pos1index]
                    else:
                        pos0index=pos1index
                        pos1index=pos1index+1
                #
                self.ISP_PCC1[i,n]=len(positions)
            #
            # Algorithm 2:
            for i in range(0,4,1):
                positions=sorted(self.data[self.freq_freqs[0]].keys())
                pos0index=0
                pos1index=1
                #
                while len(positions)>pos0index:
                    pos1index=pos0index+1
                    while len(positions)>pos1index:
                        pcc=scipy.stats.pearsonr(self.Enorm_freqstir[i,positions[pos0index],:],self.Enorm_freqstir[i,positions[pos1index],:])
                        if pcc[0]>pearson:
                            del positions[pos1index]
                        else:
                            pos1index=pos1index+1
                    pos0index=pos0index+1
                #
                self.ISP_PCC2[i,n]=len(positions)
        #
        print self.thresholds
        print self.ISP_PCC1
        print self.ISP_PCC2
        #
        # pylab.title('Calculated for Ex-component')
        # pylab.ylabel('Number of independent stirrer positions')
        # pylab.xlabel('Pearson Correlation Coefficient')
        # pylab.plot(self.thresholds,self.ISP_PCC1[0,:],label='algorithm 1')
        # pylab.plot(self.thresholds,self.ISP_PCC2[0,:],label='algorithm 2')
        # pylab.axis([1,0.3,0,100])
        # pylab.legend()
        # pylab.savefig('000_CalcIndependentStirrerPositionsPearson.png',dpi=200)
        # pylab.show()  
        
    def PlotIndStirPosComparisonAutoAndPearsonCorrCoeff(self):    
        pylab.rcParams['figure.figsize']=(6,3.5) 
        pylab.axes([0.125,0.125,0.825,0.825])
        #
        #pylab.title('')
        pylab.ylabel('number of independent stirrer positions')
        pylab.xlabel('correlation threshold')
        pylab.plot(self.thresholds,self.ISP_ACC[3,:],label='ACC')
        pylab.plot(self.thresholds,self.ISP_PCC1[3,:],label='PCC algor1')
        pylab.plot(self.thresholds,self.ISP_PCC2[3,:],label='PCC algor2')
        pylab.axis([1,0.3,0,100])
        pylab.grid(True)
        pylab.legend(loc='upper right')
        pylab.savefig('05_ISP_ACCvcPCC_250MHz.png',dpi=200)
        pylab.show()
    
    
           
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
        
    def PlotVarianceExyzNormalized(self):    
        for i in range(0,3,1):
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
        for i in range(0,3,1):
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
        
    def CalcIndependentStirrerPositionsVariance(self):
        for i in range(0,3,1):
            print 'var E: %f'%scipy.stats.tvar(self.Emeas_freqstir[i,:,:])
            print 'var <E>n: %f'%scipy.stats.tvar(self.Emean_stirpos[i,:])
            N=scipy.stats.tvar(self.Emeas_freqstir[i,:,:])/scipy.stats.tvar(self.Emean_stirpos)
            print 'N= %f' %N       
        
    def PlotPearsonCorrelationCoeffForEfieldOverStirrerposition(self):
        for i in self.stir_pos:
            for j in self.stir_pos:
                pcc=scipy.stats.pearsonr(self.Enorm_freqstir[0,i,:],self.Enorm_freqstir[0,j,:])
                self.Epearson[0,i,j]=pcc[0]
        #       
        pylab.xlabel('Stirrer position')
        pylab.ylabel('Stirrer position')
        pylab.pcolor(self.stir_pos,self.stir_pos,self.Epearson[0,:,:])
        pylab.axis([0,360,0,360])
        temp=pylab.colorbar()
        temp.set_label('Ex Pearson Correction Coefficient')
        pylab.savefig('007_ExPearsonCorrectionCoeff.png',dpi=200)
        pylab.show()
                    
    def CalcIndependentStirrerPositionsPearson_draft(self):
        print 'Algorithm 1:'
        for i in range(0,3,1):
            #positions=sorted(self.data[self.freq_freqs[0]].keys())
            positions=[0,1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17,18,19,20]
            pos0index=0
            pos1index=1
            #
            while len(positions)>pos1index:
                pcc=scipy.stats.pearsonr(self.Enorm_freqstir[i,positions[pos0index],:],self.Enorm_freqstir[i,positions[pos1index],:])
                print positions
                print len(positions), pos0index, positions[pos0index], pos1index, positions[pos1index], pcc[0]
                if pcc[0]>0.6:
                    del positions[pos1index]
                else:
                    pos0index=pos1index
                    pos1index=pos1index+1
            #
            print positions
            print 'E-Component %d: %d positions' %(i,len(positions))
        #        
        print 'Algorithm 2:'
        for i in range(0,3,1):
            #positions=sorted(self.data[self.freq_freqs[0]].keys())
            positions=[0,1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17,18,19,20]
            pos0index=0
            pos1index=1
            #
            while len(positions)>pos0index:
                pos1index=pos0index+1
                while len(positions)>pos1index:
                    pcc=scipy.stats.pearsonr(self.Enorm_freqstir[i,positions[pos0index],:],self.Enorm_freqstir[i,positions[pos1index],:])
                    print positions
                    print len(positions), pos0index, positions[pos0index], pos1index, positions[pos1index], pcc[0]
                    if pcc[0]>0.6:
                        del positions[pos1index]
                    else:
                        pos1index=pos1index+1
                pos0index=pos0index+1
            #
            print 'E-Component %d: %d positions' %(i,len(positions))
                       
    
    
if __name__ == '__main__':
    
    infile = sys.argv[1]
    dct=pickle.load(file(infile, 'rb'))
    #
    params = {'backend': 'ps',
            'font.size': 10,
            'axes.titlesize': 10,
            'axes.labelsize': 10,
            'text.fontsize': 10,
            'legend.fontsize': 10,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'text.usetex': False,   
            'figure.figsize': (6,3.5)}
    pylab.rcParams.update(params)         
    #        
    D=Data(dct)
    
    ################################################################
    
    D.CalcAutoCorrCoeffAndNumberOfIndStirPosFromAutoCorrCoeff() 
    #D.PlotPearsonCorrelationCoefficientEnormalized()
    D.CalcIndependentStirrerPositionsPearson()
    D.PlotIndStirPosComparisonAutoAndPearsonCorrCoeff()
    
    ################################################################
    
    #D.PlotExyzOverFreqAndStirpos()
    #D.PlotScatterDiagram()
    #D.PlotVarianceExyzNormalized()
    #D.PlotEmeanOverNStirpos()
    #D.PlotVarianceExyzMeanOverNStirrerposition()
    #D.CalcIndependentStirrerPositionsVariance()
    #D.PlotPearsonCorrelationCoeffForEfieldOverStirrerposition()
    #D.CalcIndependentStirrerPositionsPearson()
    