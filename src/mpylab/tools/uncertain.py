# -*- coding: utf-8 -*-

import math
import scipy.stats as stats

sqrt3 = math.sqrt(3)
sqrt2 = math.sqrt(2)


def _quantile(coverage=0.95, both_tails=True):
    """
    return the quantile from the *coverage* depending on the parameter *both_tails*.

    If *both_tails* is *True*, both tails of the distribution are truncated equally. Else,
    only the upper tail is truncated. 
    """
    if both_tails:
        quantile = 0.5 * (1 + coverage)
    else:
        quantile = coverage
    return quantile


def get_k_factor_norm(coverage=0.95, both_tails=True):
    """
    Return the k factor for the normal distribution.
    
    The k-factor is defined as follows: in the interval width 2*k*sigma falls *coverage* * 100 percent of the values.
    The k-factor is used to calculated extended uncertainties from standard deviations (uncertainties) or vice versa.
    """
    quantile = _quantile(coverage, both_tails)
    return stats.norm.ppf(quantile)


def get_k_factor_rect(coverage=0.95, both_tails=True):
    """
    Return the k factor for the rectangular distribution.
    
    The k-factor is defined as follows: in the interval width 2*k*sigma falls *coverage* * 100 percent of the values.
    The k-factor is used to calculated extended uncertainties from standard deviations (uncertainties) or vice versa.
    """
    quantile = _quantile(coverage, both_tails)
    return sqrt3 * (2 * quantile - 1)


def get_k_factor_ushape(coverage=0.95, both_tails=True):
    """
    Return the k factor for the u-shaped distribution.
    
    The k-factor is defined as follows: in the interval width 2*k*sigma falls *coverage* * 100 percent of the values.
    The k-factor is used to calculated extended uncertainties from standard deviations (uncertainties) or vice versa.
    """
    quantile = _quantile(coverage, both_tails)
    # the u-shape dist is a beta-dist with p=q=0.5
    return stats.beta.ppf(quantile, 0.5, 0.5) * sqrt2


def get_dB_factors(dB, k, A=10):
    """
    Calculate a k-factor on the dB scale.
    
    dB: standard uncertainty in dB (dB=A*log10((E+sigma)/sigma)
    k: linear k-factor
    A: transformation factor lin<->dB; 10->power, 20->voltage, field strength,...
    
    A 2-tuple of k-factors on the dB scale is returned
    """
    A = float(A)
    lin = 10 ** (dB / A) - 1
    if dB <= 1e-16:
        return k, k
    #    try:
    #        1./dB
    #        math.log10(1-k*lin)
    #    except (ZeroDivisionError, ValueError):
    #        return k, k
    return -A * math.log10(1 - k * lin) / dB, A * math.log10(1 + k * lin) / dB
