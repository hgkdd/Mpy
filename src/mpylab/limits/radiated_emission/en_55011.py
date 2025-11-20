from inspect import cleandoc
from numpy import piecewise, array, full_like, nan

from mpylab.limits.limit import Limit


class LIMIT(Limit):
    description_title = "DIN EN 55011:2022-05 (CISPR-11), radiated"
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
                                
                                On a test site, **Class A** equipment can be measured at a nominal distance d 
                                of 3m, 10m or 30m.
                                
                                **Class A** ***Group 1** equipment can be measured in situ, where the 
                                measurement takes place at a distance of 30m from the outer face of the exterior 
                                wall of the building in which the equipment is situated.
                                
                                **Class A** **Group 2** equipment can be measured in situ, where the measurement 
                                distance d from the exterior wall of the building in which the equipment is situated 
                                equals (30+x/a)m or 100m whichever is smaller, provided that the measuring 
                                distance d is within the boundary of the premises. In the case where the calculated 
                                distance d is beyond the boundary of the premises, the measuring distance 
                                d equals x or 30m, whichever is longer. For the calculation of the above values:

                                - x is the nearest distance between the exterior wall of the building in which 
                                the equipment is situated and the boundary of the user’s premises in each 
                                measuring direction.
                                - a = 2.5 for frequencies lower than 1 MHz.
                                - a = 4.5 for frequencies equal to or higher than 1 MHz.""",
                             'B': """
                                ## Test Setup: 
                                
                                On a test site, Class B equipment can be measured at a nominal distance d of 3m or 10m.
                                
                                - d < 10m. In the frequency range 30MHz to 1000MHz, a distance less than 
                                10m is allowed only for equipment which complies with the definition 
                                for small size equipment. Small size equipment is either positioned on a 
                                table top or standing on the floor which, including its cables fits in an 
                                imaginary cylindrical test volume of 1.2m in diameter and 1.5m height 
                                (to ground plane)."""}
    fmin = 30e6
    fmax = 6e9
    variations = {'Group': ('1', '2'),
                       'Classification': ('A', 'B'),
                       'Detector': ('QP', 'AV', 'PK'),
                       'Port': ('AC (≤ 20 kVA)',  'AC (> 20 kVA)'),
                  'Distance': ('3 m', '10 m', '30 m')}
    unit = 'dBµV/m'

    def __init__(self, group=None, classification=None, detector=None, port=None, distance=None):
        super().__init__()
        self.group = None
        self.classification = None
        self.detector = None
        self.port = None
        self.distance = None
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

        if distance is None:
            self.distance = '10 m'
        else:
            if distance not in self.variations['Distance']:
                raise ValueError(f"EN55011: Distance must be in {self.variations['Distance']}")
            self.distance = distance

        self.description = "".join(('# ', cleandoc(self.description_title), '\n\n',
                                   cleandoc(self.description_Group[self.group]), '\n\n',
                                    cleandoc(self.description_Classification[self.classification]), '\n\n',
                                    cleandoc(self.description_TestSetup[self.classification])))

        try:
            attr = f'limit_G{self.group}_C{self.classification}_{self.port}_{self.detector}_{self.distance}'.replace(' ', '_')
            attr = attr.replace('≤', 'less')
            attr = attr.replace('>', 'over')
            attr = attr.replace('(','')
            attr = attr.replace(')','')
            self.limitline = getattr(self, attr)
        except AttributeError:
            # raise UserWarning(f"EN55011: Attribute '{attr}' not found. Using 'no_limit' instead.")
            self.limitline = self.no_limit

    # AC below 20 kVA
    def limit_G1_CB_AC_less_20_kVA_QP_10_m(self, f):
        if not isinstance(f, type(array)):
            f = array(f)
        conditions = [(f >= 30e6) & (f < 230e6),
                      (f >= 230e6) & (f < 1e9)]
        functions = [30,
                     39,
                     None]
        results = piecewise(f, conditions, functions)
        return results

    def limit_G1_CB_AC_less_20_kVA_QP_3_m(self, f):  # 10 dB higher for 3m
        return self.limit_G1_CB_AC_less_20_kVA_QP_10_m(f) + 10

    def limit_G1_CA_AC_less_20_kVA_QP_10_m(self, f):  #
        return self.limit_G1_CB_AC_less_20_kVA_QP_3_m(f)

    def limit_G1_CA_AC_less_20_kVA_QP_3_m(self, f):  #
        return self.limit_G1_CA_AC_less_20_kVA_QP_10_m(f)

    def limit_G1_CA_AC_over_20_kVA_QP_10_m(self, f):
        if not isinstance(f, type(array)):
            f = array(f)
        return full_like(f, 50)

    def limit_G1_CA_AC_over_20_kVA_QP_3_m(self, f):
        return self.limit_G1_CA_AC_over_20_kVA_QP_10_m(f) + 10

    def limit_G1_CB_AC_less_20_kVA_AV_3_m(self, f):
        if not isinstance(f, type(array)):
            f = array(f)
        conditions = [(f >= 1e9) & (f < 3e9),
                      (f >= 3e9) & (f < 6e9)]
        functions = [50,
                     54,
                     None]
        results = piecewise(f, conditions, functions)
        return results

    def limit_G1_CA_AC_less_20_kVA_AV_3_m(self, f):
        return self.limit_G1_CB_AC_less_20_kVA_AV_3_m(f) + 6

    def limit_G1_CB_AC_less_20_kVA_PK_3_m(self, f):
        return self.limit_G1_CB_AC_less_20_kVA_AV_3_m(f) + 20

    def limit_G1_CA_AC_less_20_kVA_PK_3_m(self, f):
        return self.limit_G1_CB_AC_less_20_kVA_AV_3_m(f) + 26


CISPR11 = EN55011 = LIMIT

if __name__ == '__main__':
    from matplotlib import pyplot as plt
    from mpylab.tools.spacing import logspace
    limit = LIMIT(group='1', classification='B', detector='QP', port='AC (≤ 20 kVA)', distance='10 m')
    print(limit.description)
    freqs = logspace(30e6, 1e9, 1.05)

    limit_values = limit.limitline(freqs)
    fig, ax = plt.subplots()
    ax.set(xlim=(10e6, 1000e6), ylim=(45, 135))
    ax.semilogx(freqs, limit_values, freqs)
    ax.grid(True)
    fig.show()


