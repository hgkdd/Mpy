from inspect import cleandoc
from numpy import piecewise, log10, array


def log_linear(f1,v1,f2,v2):
    return lambda f: (v2-v1) * log10(f/f1) / log10(f2/f1) + v1

class EN55011:
    description_Group = {1: """
                            # **Group 1**: (general purpose applications)
                            
                            All equipment in the scope of EN 55011 (CISPR 11) which is not classified as Group 2 equipment. 
                            
                            Examples of **Group 1** equipment:
                            
                            - Laboratory equipment
                            - Medical electrical equipment
                            - Scientific equipment
                            - Semiconductor-converters
                            - Industrial electric heating equipment with operating frequencies less than or equal to 9 kHz
                            - Machine tools
                            - Industrial process measurement and control equipment
                            - Semiconductor manufacturing equipment
                            - Switch mode power supplies""",
                         2: """
                             # **Group 2** (ISM RF applications): All ISM RF equipment in which radio-frequency energy in the frequency 
                             range 9kHz to 400GHz is intentionally generated and used or only used locally, in the form 
                             of electromagnetic radiation, inductive and/or capacitive coupling, for the treatment 
                             of material, for inspection/analysis purposes, or for transfer of electromagnetic energy. 
                             
                             Examples of **Group 2** equipment:
                             
                             - Microwave-powered UV irradiating apparatus
                             - Microwave lighting apparatus
                             - Industrial induction heating equipment operating at frequencies above 9 kHz
                             - Dielectric heating equipment Industrial microwave heating equipment
                             - Arc Welding equipment
                             - Microwave ovens
                             - Medical electrical equipment
                             - Electric welding equipment
                             - Electro-discharge machining (EDM) equipment
                             - Demonstration models for education and training
                             - Battery chargers and power supplies – wireless power transfer (WPT) mode"""}
    description_Classification = {'A': """
                                        # **Class A** (higher emission limits, industrial) 
                                        
                                        **Class A** devices are devices that are suitable for use in all areas other than 
                                        residential and such areas, and they are connected to the public mains.
                                        
                                        Devices must have emissions which are below the limits of Class A, 
                                        but the emissions may exceed the limits of Class B.
                                        
                                        For Class A equipment, the instructions for use accompanying the product shall 
                                        contain the following text: 
                                        
                                        *Caution: This equipment is not intended for use in residential environments 
                                        and may not provide adequate protection to radio reception in such environments.*""",
                                  'B': """
                                        # **Class B** (lower emission limits, residential): 
                                        
                                        **Class B** devices are devices that are suitable for use in residential areas 
                                        and such areas, and they are connected to the public mains."""}
    description_TestSetup = {'A': """
                                # Test Setup:
                                
                                **Class A** equipment may be measured either on a test site or in situ 
                                (at installation site) as preferred by the manufacturer. Due to size, complexity or 
                                operating conditions some equipment may have to be measured in situ in order to 
                                show compliance with disturbance limits.
                                """,
                             'B': """
                                # Test Setup: 
                                
                                **Class B** equipment shall be measured on a test site."""}

    def __init__(self, group=None, classification=None, detector=None, ports=None):
        self.group = None
        self.classification = None
        self.detector = None
        self.ports = None
        self.unit = 'dBuV'
        self.limitline = None

        if group is None:
            self.group = 1
        else:
            if group not in  (1, 2):
                raise ValueError("EN55011: Group must be 1 or 2")
            self.group = group

        if classification is None:
            self.classification = 'A'
        else:
            classification = classification.upper()
            if classification not in ('A', 'B'):
                raise ValueError("EN55011: Class must be 'A' or 'B'")
            self.classification = classification

        if detector is None:
            self.detector = 'QP'
        else:
            detector = detector.upper()
            if detector not in ('QP', 'AV'):
                raise ValueError("EN55011: Detector must be 'QP' or 'AV'")
            self.detector = detector

        if ports is None:
            self.ports = 'AC'
        else:
            ports = ports.upper()
            if ports not in ('AC', 'DC'):
                raise ValueError("EN55011: Ports must be 'AC' or 'DC'")
            self.ports = ports

        self.description = "".join((cleandoc(self.description_Group[self.group]), '\n\n',
                                    cleandoc(self.description_Classification[self.classification]), '\n\n',
                                    cleandoc(self.description_TestSetup[self.classification])))

        try:
            self.limitline = getattr(self, f'limit_G{self.group}_C{self.classification}_{self.ports}_{self.detector}')
        except AttributeError:
            raise



    def limit_G1_CB_AC_AV(self, f):
        if not isinstance(f, type(array)):
            f = array(f)
        conditions = [(f >= 150e3) & (f < 500e3),
                      (f >= 500e3) & (f < 5e6),
                      (f >= 5e6) & (f <= 30e6)]
        functions = [log_linear(150e3,56,500e3,46),
                     46,
                     50,
                     None]
        results = piecewise(f, conditions, functions)
        return results

    def limit_G1_CB_AC_QP(self, f):  # 10 dB higher for QP
        return self.limit_G1_CB_AC_AV(f) + 10

    def limit_G2_CB_AC_AV(self, f):  # same as Group 1
        return self.limit_G1_CB_AC_AV(f)

    def limit_G2_CB_AC_QP(self, f): # same as Group 1
        return self.limit_G2_CB_AC_QP(f)

if __name__ == '__main__':
    from matplotlib import pyplot as plt
    from mpylab.tools.spacing import logspace
    limit = EN55011(group=1, classification='B', detector='QP', ports='AC')
    print(limit.description)
    freqs = logspace(9e3, 50e6, 1.05)

    limit_values = limit.limitline(freqs)
    fig, ax = plt.subplots()
    ax.set(xlim=(100e3, 100e6), ylim=(45, 135))
    ax.semilogx(freqs, limit_values, freqs)
    ax.grid(True)
    fig.show()


