"""Conducted-emission limits according to EN 55032 (CISPR 32)."""

from inspect import cleandoc
from numpy import piecewise, log10, array, full_like, nan

from mpylab.limits.limit import Limit, log_linear


class LIMIT(Limit):
    """Configurable EN 55032 conducted-emission limit model."""
    description_title = "DIN EN 55032:2022-08 (CISPR-32), conducted"
    description_Group = """
                          EN 55032 applies to multimedia equipment (MME) and having a rated RMS AC or DC 
                          supply voltage not exceeding 600 V. 
                          Equipment within the scope of CISPR 13 or CISPR 22 is within the scope of EN 55032. 
                          MME intended primarily for professional use is within the scope of EN 55032. 
                          The radiated emission requirements in EN 55032 are not intended to be applicable 
                          to the intentional transmissions from a radio transmitter as defined by the ITU, 
                          nor to any spurious emissions related to these intentional transmissions. 
                          Equipment, for which emission requirements in the frequency range covered by EN 55032
                          are explicitly formulated in other CISPR publications (except CISPR 13 and CISPR 22), 
                          are excluded from the scope of this publication. EN 55032 does not contain 
                          requirements for in-situ assessment (in other words: the tests have to be done in 
                          an EMC test laboratory). 
                          The objectives of EN 55032 publication are:
    
                          - To establish requirements which provide an adequate level of 
                             protection of the radio spectrum, allowing radio services to operate as 
                             intended in the frequency range 9 kHz to 400 GHz.
                          - To specify procedures to ensure the reproducibility of measurement and the 
                            repeatability of results.
    
                          The EN 55032 is often referenced by other product and product family standards, 
                          outside of the scope defined above."""
    description_Classification = {'A': """
                                        ## Class A (higher emission limits, industrial) 
                                        
                                        **Class A** devices must have emissions which are below the limits of Class A, 
                                        but the emissions exceed the limits of Class B.
                                        Class A devices shall have a warning notice in their manual (e.g.                                         
                                        *"Warning! This is a Class A device. This device may cause radio 
                                        interference in residential areas; in this case, the operator may be 
                                        required to take appropriate measures"*.).""",
                                  'B': """
                                        ## Class B (lower emission limits, residential): 
                                        
                                        **Class B** devices must have emissions which are below the limits of 
                                        Class B. This is applicable for devices which are used in a residual and 
                                        domestic environment. In other words: commercial devices. E.g.:
                                        
                                        - No permanent location (e.g. battery powered devices)
                                        - Telecommunication terminal equipment
                                        - Personal computers"""}

    fmin = 150e3
    fmax = 30e6
    variations = {'Classification': ('A', 'B'),
                       'Detector': ('QP', 'AV'),
                       'Port': ('Mains', 'Telecom/LAN')}
    unit = 'dBµV'

    def __init__(self, classification=None, detector=None, port=None):
        super().__init__()
        self.classification = None
        self.detector = None
        self.port = None
        self.limitline = None

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
            self.port = 'Mains'
        else:
            if port not in self.variations['Port']:
                raise ValueError(f"EN55011: Ports must be in {self.variations['Port']}")
            self.port = port

        self.description = "".join(('# ', cleandoc(self.description_title), '\n\n',
                                   cleandoc(self.description_Group), '\n\n',
                                    cleandoc(self.description_Classification[self.classification])))

        try:
            attr = f'limit_C{self.classification}_{self.port}_{self.detector}'.replace(' ', '_')
            attr = attr.replace('≤', 'less')
            attr = attr.replace('>', 'over')
            attr = attr.replace('(','')
            attr = attr.replace(')','')
            attr = attr.replace('/','_')
            self.limitline = getattr(self, attr)
        except AttributeError:
            # raise UserWarning(f"EN55011: Attribute '{attr}' not found. Using 'no_limit' instead.")
            self.limitline = self.no_limit

    # Mains
    def limit_CB_Mains_AV(self, f):
        """Return Class B mains-port AV limits."""
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

    def limit_CB_Mains_QP(self, f):  # 10 dB higher for QP
        """Return Class B mains-port QP limits."""
        return self.limit_CB_Mains_AV(f) + 10

    def limit_CA_Mains_AV(self, f):     # only <= 20 kVA
        """Return Class A mains-port AV limits."""
        if not isinstance(f, type(array)):
            f = array(f, dtype=float)
        conditions = [(f >= 150e3) & (f < 500e3),
                      (f >= 500e3) & (f <= 30e6)]
        functions = [66,
                     60,
                     None]
        results = piecewise(f, conditions, functions)
        return results

    def limit_CA_Mains_QP(self, f):    # only <= 20 kVA
        """Return Class A mains-port QP limits."""
        return self.limit_CA_Mains_AV(f) + 13

################################# Telekom / LAN ###########################
    # DC below 20 kVA
    def limit_CB_Telecom_LAN_AV(self, f):
        """Return Class B telecom/LAN-port AV limits."""
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

    def limit_CB_Telecom_LAN_QP(self, f):  # 10 dB higher for QP
        """Return Class B telecom/LAN-port QP limits."""
        return self.limit_CB_Telecom_LAN_AV(f) + 10

    limit_CA_Telecom_LAN_AV = limit_CB_Telecom_LAN_QP

    def limit_CA_Telecom_LAN_QP(self, f):
        """Return Class A telecom/LAN-port QP limits."""
        return self.limit_CA_Telecom_LAN_AV(f) + 13

CISPR32 = EN55032 = LIMIT

if __name__ == '__main__':
    from matplotlib import pyplot as plt
    from mpylab.tools.spacing import logspace
    limit = LIMIT(classification='B', detector='QP', port='Mains')
    print(limit.description)
    freqs = logspace(9e3, 50e6, 1.05)

    limit_values = limit.limitline(freqs)
    fig, ax = plt.subplots()
    ax.set(xlim=(100e3, 100e6), ylim=(45, 135))
    ax.semilogx(freqs, limit_values, freqs)
    ax.grid(True)
    fig.show()

