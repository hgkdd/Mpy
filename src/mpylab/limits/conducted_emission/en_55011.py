from inspect import cleandoc
from numpy import piecewise, log10, array, full_like, nan

from mpylab.limits.limit import Limit, log_linear


class LIMIT(Limit):
    description_title = "DIN EN 55011:2022-05 (CISPR-11), conducted"
    description_Group = {'1': """
                            ## Group 1: (general purpose applications)
                            
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
                         '2': """
                             ## Group 2 (ISM RF applications): 
                             
                             All ISM RF equipment in which radio-frequency energy in the frequency 
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
                                        ## Class A (higher emission limits, industrial) 
                                        
                                        **Class A** devices are devices that are suitable for use in all areas other than 
                                        residential and such areas, and they are connected to the public mains.
                                        
                                        Devices must have emissions which are below the limits of Class A, 
                                        but the emissions may exceed the limits of Class B.
                                        
                                        For Class A equipment, the instructions for use accompanying the product shall 
                                        contain the following text: 
                                        
                                        *Caution: This equipment is not intended for use in residential environments 
                                        and may not provide adequate protection to radio reception in such environments.*""",
                                  'B': """
                                        ## Class B (lower emission limits, residential): 
                                        
                                        **Class B** devices are devices that are suitable for use in residential areas 
                                        and such areas, and they are connected to the public mains."""}
    description_TestSetup = {'A': """
                                ## Test Setup:
                                
                                **Class A** equipment may be measured either on a test site or in situ 
                                (at installation site) as preferred by the manufacturer. Due to size, complexity or 
                                operating conditions some equipment may have to be measured in situ in order to 
                                show compliance with disturbance limits.
                                """,
                             'B': """
                                ## Test Setup: 
                                
                                **Class B** equipment shall be measured on a test site."""}
    fmin = 150e3
    fmax = 30e6
    variations = {'Group': ('1', '2'),
                       'Classification': ('A', 'B'),
                       'Detector': ('QP', 'AV'),
                       'Port': ('AC (≤ 20 kVA)', 'AC (≤ 75 kVA)', 'AC (> 75 kVA)',
                                'DC (≤ 20 kVA)', 'DC (≤ 75 kVA)', 'DC (> 75 kVA)')}
    unit = 'dBµV'

    def __init__(self, group=None, classification=None, detector=None, port=None):
        super().__init__()
        self.group = None
        self.classification = None
        self.detector = None
        self.port = None
        self.limitline = None

        if group is None:
            self.group = '1'
        else:
            if group not in  self.variations['Group']:
                raise ValueError(f"EN55011: Group must be in {self.variations['Group']}")
            self.group = group

        if classification is None:
            self.classification = 'A'
        else:
            classification = classification.upper()
            if classification not in self.variations['Classification']:
                raise ValueError(f"EN55011: Classification must be in {self.variations['Classification']}")
            self.classification = classification

        if detector is None:
            self.detector = 'QP'
        else:
            detector = detector.upper()
            if detector not in self.variations['Detector']:
                raise ValueError(f"EN55011: Detector must be in {self.variations['Detector']}")
            self.detector = detector

        if port is None:
            self.port = 'AC (≤ 20 kVA)'
        else:
            if port not in self.variations['Port']:
                raise ValueError(f"EN55011: Ports must be in {self.variations['Port']}")
            self.port = port

        self.description = "".join(('# ', cleandoc(self.description_title), '\n\n',
                                   cleandoc(self.description_Group[self.group]), '\n\n',
                                    cleandoc(self.description_Classification[self.classification]), '\n\n',
                                    cleandoc(self.description_TestSetup[self.classification])))

        try:
            attr = f'limit_G{self.group}_C{self.classification}_{self.port}_{self.detector}'.replace(' ', '_')
            attr = attr.replace('≤', 'less')
            attr = attr.replace('>', 'over')
            attr = attr.replace('(','')
            attr = attr.replace(')','')
            self.limitline = getattr(self, attr)
        except AttributeError:
            # raise UserWarning(f"EN55011: Attribute '{attr}' not found. Using 'no_limit' instead.")
            self.limitline = self.no_limit

    # AC below 20 kVA
    def limit_G1_CB_AC_less_20_kVA_AV(self, f):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 500e3),
                      (f >= 500e3) & (f < 5e6),
                      (f >= 5e6) & (f <= 30e6)]
        functions = [log_linear(150e3,56,500e3,46),
                     46,
                     50,
                     None]
        results = piecewise(f, conditions, functions)
        return results

    def limit_G1_CB_AC_less_20_kVA_QP(self, f):  # 10 dB higher for QP
        return self.limit_G1_CB_AC_less_20_kVA_AV(f) + 10

    def limit_G2_CB_AC_less_20_kVA_AV(self, f):  # same as Group 1
        return self.limit_G1_CB_AC_less_20_kVA_AV(f)

    def limit_G2_CB_AC_less_20_kVA_QP(self, f): # same as Group 1
        return self.limit_G1_CB_AC_less_20_kVA_QP(f)

    def limit_G1_CA_AC_less_20_kVA_AV(self, f):     # only <= 20 kVA
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 500e3),
                      (f >= 500e3) & (f <= 30e6)]
        functions = [66,
                     56,
                     None]
        results = piecewise(f, conditions, functions)
        return results

    def limit_G1_CA_AC_less_20_kVA_QP(self, f):    # only <= 20 kVA
        return self.limit_G1_CA_AC_less_20_kVA_AV(f) + 13

    def limit_G2_CA_AC_less_20_kVA_AV(self, f):     # only <= 75 kVA
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 500e3),
                      (f >= 500e3) & (f <= 5e6),
                      (f >= 5e6) & (f <= 30e6)]
        functions = [90,
                     76,
                     log_linear(5e6,80,30e6,60),
                     None]
        results = piecewise(f, conditions, functions)
        return results

    def limit_G2_CA_AC_less_20_kVA_QP(self, f):     # only <= 75 kVA
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 500e3),
                      (f >= 500e3) & (f <= 5e6),
                      (f >= 5e6) & (f <= 30e6)]
        functions = [100,
                     86,
                     log_linear(5e6,90,30e6,73),
                     None]
        results = piecewise(f, conditions, functions)
        return results

    # AC lower 75 kVA
    def limit_G1_CA_AC_less_75_kVA_AV(self, f):
        return self.limit_G2_CA_AC_less_20_kVA_AV(f)

    def limit_G1_CA_AC_less_75_kVA_QP(self, f):
        return self.limit_G2_CA_AC_less_20_kVA_QP(f)

    def limit_G1_CB_AC_less_75_kVA_AV(self, f):
        return self.limit_G1_CB_AC_less_20_kVA_AV(f)

    def limit_G1_CB_AC_less_75_kVA_QP(self, f):
        return self.limit_G1_CB_AC_less_20_kVA_QP(f)

    def limit_G2_CA_AC_less_75_kVA_AV(self, f):
        return self.limit_G1_CA_AC_less_75_kVA_AV(f)

    def limit_G2_CA_AC_less_75_kVA_QP(self, f):
        return self.limit_G1_CA_AC_less_75_kVA_QP(f)

    def limit_G2_CB_AC_less_75_kVA_AV(self, f):
        return self.limit_G2_CB_AC_less_20_kVA_AV(f)

    def limit_G2_CB_AC_less_75_kVA_QP(self, f):
        return self.limit_G2_CB_AC_less_20_kVA_QP(f)

    # AC over 75 kVA
    def limit_G1_CA_AC_over_75_kVA_AV(self, f):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 500e3),
                      (f >= 500e3) & (f <= 5e6),
                      (f >= 5e6) & (f <= 30e6)]
        functions = [120,
                     115,
                     105,
                     None]
        results = piecewise(f, conditions, functions)
        return results

    def limit_G1_CA_AC_over_75_kVA_QP(self, f):
        return self.limit_G1_CA_AC_over_75_kVA_AV(f) +10

    def limit_G1_CB_AC_over_75_kVA_AV(self, f):
        return self.limit_G1_CB_AC_less_20_kVA_AV(f)

    def limit_G1_CB_AC_over_75_kVA_QP(self, f):
        return self.limit_G1_CB_AC_less_20_kVA_QP(f)

    def limit_G2_CA_AC_over_75_kVA_AV(self, f):
        return self.limit_G1_CA_AC_over_75_kVA_AV(f)

    def limit_G2_CA_AC_over_75_kVA_QP(self, f):
        return self.limit_G1_CA_AC_over_75_kVA_QP(f)

    def limit_G2_CB_AC_over_75_kVA_AV(self, f):
        return self.limit_G2_CB_AC_less_20_kVA_AV(f)

    def limit_G2_CB_AC_over_75_kVA_QP(self, f):
        return self.limit_G2_CB_AC_less_20_kVA_QP(f)

################################# DC ###########################
    # DC below 20 kVA
    def limit_G1_CB_DC_less_20_kVA_AV(self, f):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 500e3),
                      (f >= 500e3) & (f < 5e6),
                      (f >= 5e6) & (f <= 30e6)]
        functions = [log_linear(150e3,74,500e3,64),
                     64,
                     64,
                     None]
        results = piecewise(f, conditions, functions)
        return results

    def limit_G1_CB_DC_less_20_kVA_QP(self, f):  # 10 dB higher for QP
        return self.limit_G1_CB_DC_less_20_kVA_AV(f) + 10

    def limit_G2_CB_DC_less_20_kVA_AV(self, f):  # same as Group 1
        return self.no_limit(f)

    def limit_G2_CB_DC_less_20_kVA_QP(self, f): # same as Group 1
        return self.no_limit(f)

    def limit_G1_CA_DC_less_20_kVA_AV(self, f):     # only <= 20 kVA
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 5e6),
                      (f >= 5e6) & (f <= 30e6)]
        functions = [log_linear(150e3,84,5e6,76),
                     76,
                     None]
        results = piecewise(f, conditions, functions)
        return results

    def limit_G1_CA_DC_less_20_kVA_QP(self, f):    # only <= 20 kVA
        return self.limit_G1_CA_DC_less_20_kVA_AV(f) + 13

    def limit_G2_CA_DC_less_20_kVA_AV(self, f):     # only <= 75 kVA
        return self.no_limit(f)

    def limit_G2_CA_DC_less_20_kVA_QP(self, f):     # only <= 75 kVA
        return self.no_limit(f)

    # DC lower 75 kVA
    def limit_G1_CA_DC_less_75_kVA_AV(self, f):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 5e6),
                      (f >= 5e6) & (f <= 30e6)]
        functions = [log_linear(150e3,106,5e6,96),
                     log_linear(5e6,96,30e6,76),
                     None]
        results = piecewise(f, conditions, functions)
        return results

    def limit_G1_CA_DC_less_75_kVA_QP(self, f):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 5e6),
                      (f >= 5e6) & (f <= 30e6)]
        functions = [log_linear(150e3,116,5e6,106),
                     log_linear(5e6,106,30e6,89),
                     None]
        results = piecewise(f, conditions, functions)
        return results

    def limit_G1_CB_DC_less_75_kVA_AV(self, f):
        return self.limit_G1_CB_DC_less_20_kVA_AV(f)

    def limit_G1_CB_DC_less_75_kVA_QP(self, f):
        return self.limit_G1_CB_DC_less_20_kVA_QP(f)

    def limit_G2_CA_DC_less_75_kVA_AV(self, f):
        return self.no_limit(f)

    def limit_G2_CA_DC_less_75_kVA_QP(self, f):
        return self.no_limit(f)

    def limit_G2_CB_DC_less_75_kVA_AV(self, f):
        return self.no_limit(f)

    def limit_G2_CB_DC_less_75_kVA_QP(self, f):
        return self.no_limit(f)

    # DC over 75 kVA
    def limit_G1_CA_DC_over_75_kVA_AV(self, f):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 5e6),
                      (f >= 5e6) & (f <= 30e6)]
        functions = [log_linear(150e3,122,5e6,112),
                     log_linear(5e6,112,30e6,92),
                     None]
        results = piecewise(f, conditions, functions)
        return results

    def limit_G1_CA_DC_over_75_kVA_QP(self, f):
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 5e6),
                      (f >= 5e6) & (f <= 30e6)]
        functions = [log_linear(150e3,132,5e6,122),
                     log_linear(5e6,122,30e6,105),
                     None]
        results = piecewise(f, conditions, functions)
        return results

    def limit_G1_CB_DC_over_75_kVA_AV(self, f):
        return self.limit_G1_CB_DC_less_20_kVA_AV(f)

    def limit_G1_CB_DC_over_75_kVA_QP(self, f):
        return self.limit_G1_CB_DC_less_20_kVA_QP(f)

    def limit_G2_CA_DC_over_75_kVA_AV(self, f):
        return self.no_limit(f)

    def limit_G2_CA_DC_over_75_kVA_QP(self, f):
        return self.no_limit(f)

    def limit_G2_CB_DC_over_75_kVA_AV(self, f):
        return self.no_limit(f)

    def limit_G2_CB_DC_over_75_kVA_QP(self, f):
        return self.no_limit(f)



CISPR11 = EN55011 = LIMIT

if __name__ == '__main__':
    from matplotlib import pyplot as plt
    from mpylab.tools.spacing import logspace
    limit = LIMIT(group='1', classification='B', detector='QP', port='AC (≤ 20 kVA)')
    print(limit.description)
    freqs = logspace(9e3, 50e6, 1.05)

    limit_values = limit.limitline(freqs)
    fig, ax = plt.subplots()
    ax.set(xlim=(100e3, 100e6), ylim=(45, 135))
    ax.semilogx(freqs, limit_values, freqs)
    ax.grid(True)
    fig.show()


