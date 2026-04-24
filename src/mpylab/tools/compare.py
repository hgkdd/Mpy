"""mpylab.tools.compare module."""
from os.path import commonprefix
from Levenshtein import distance as ldistance

def cmp(a, b):
    """cmp function."""
    return (a > b) - (a < b)


def cplx_key(a):
    """cplx_key function."""
    try:
        # komplexer Fall
        re = a.real
        if re == 0:
            # rein imaginär → Vorzeichen nicht definierbar über real
            # fallback: nur Betrag (neutral)
            return abs(a)
        return abs(a) * (re / abs(re))
    except AttributeError:
        # reeller Fall
        return a


def cplx_cmp(a, b):
    # magnituide * sgn(real part)
    """cplx_cmp function."""
    ka = cplx_key(a)
    kb = cplx_key(b)
    return cmp(ka, kb)


def rmcp(seq, ignorecase=True):
    """remove common prefix from sequence elements"""
    if ignorecase:
        seq = [s.lower() for s in seq]
    cp = commonprefix(seq)
    n = len(cp)
    return [s[n:] for s in seq], cp

def relative(a, b, first_must_match=True):
    """
    Computes a relative distance between two strings. It's in the range
    (0-1] where 1 means total equality.
    @type a: string
    @param a: arg one
    @type b: string
    @param b: arg two
    @rtype: float
    @return: the distance
    """
    if not a or not b:
        return 1.0 if a == b else 0.0

    if first_must_match and a[0] != b[0]:
        return 0.0

    d = ldistance(a, b)
    longer = float(max((len(a), len(b))))
    shorter = float(min((len(a), len(b))))
    r = ((longer - d) / longer) * (shorter / longer)
    return r

def fstrcmp(a, possibilities, cutoff=0.0, ignorecase=True, use_rmcp=True):
    """fstrcmp function."""
    a = a.strip("'\"")

    if ignorecase:
        a_cmp = a.lower()
        poss_cmp = [p.lower() for p in possibilities]
    else:
        a_cmp = a
        poss_cmp = possibilities[:]

    # optional common-prefix removal
    if use_rmcp:
        poss_cmp, cp = rmcp(poss_cmp, ignorecase=False)
        if a_cmp.startswith(cp):
            a_cmp = a_cmp[len(cp):]

    scores = []
    for orig, p in zip(possibilities, poss_cmp):
        score = relative(a_cmp, p)

        # boost exact matches
        if ignorecase:
            if a.lower() == orig.lower():
                score = 1.0
        else:
            if a == orig:
                score = 1.0

        scores.append((score, orig))

    return [v for s, v in sorted(scores, reverse=True) if s >= cutoff]

def fstrcmp_scpi(a, possibilities, cutoff=0.0, ignorecase=True):
    """
    Token-based fuzzy matcher for SCPI commands.

    The command is split at ':' and each token is compared separately.
    Ranking prefers:
    1. exact token matches
    2. token prefix matches
    3. token substring matches
    4. best fuzzy token similarity

    Example:
        fstrcmp_scpi("BAND", ["SENS:FREQ:START", "SENS:BAND:RES"])
        -> ["SENS:BAND:RES", "SENS:FREQ:START"]
    """
    a = a.strip("'\"")
    if not a:
        return []

    if ignorecase:
        a_cmp = a.lower()
        poss_cmp = [p.lower() for p in possibilities]
    else:
        a_cmp = a
        poss_cmp = list(possibilities)

    scored = []

    for orig, candidate in zip(possibilities, poss_cmp):
        tokens = candidate.split(":")
        token_scores = []

        for token in tokens:
            score = relative(a_cmp, token)

            # exact token match
            if a_cmp == token:
                score += 1.0
            # token startswith search term
            elif token.startswith(a_cmp):
                score += 0.75
            # search term appears inside token
            elif a_cmp in token:
                score += 0.5

            token_scores.append(score)

        best_token_score = max(token_scores) if token_scores else 0.0

        # exact full-command match gets absolute priority
        if ignorecase:
            if a.lower() == orig.lower():
                best_token_score = 10.0
        else:
            if a == orig:
                best_token_score = 10.0

        scored.append((best_token_score, orig))

    return [v for s, v in sorted(scored, reverse=True) if s >= cutoff]

if __name__ == "__main__":
#    from sys import argv

    # print levenshtein(argv[1],argv[2],ch_cost=float(argv[3]), add_cost=float(argv[4]), del_cost=float(argv[5]))
#    print(old_fstrcmp(argv[1], ('ON', 'OFF')))
#    print(fstrcmp(argv[1], ('ON', 'OFF')))
    print("=== rmcp tests ===")
    seq = ["SENS:FREQ:START", "SENS:FREQ:STOP", "SENS:FREQ:CENT"]
    trimmed, cp = rmcp(seq)
    print("input      :", seq)
    print("prefix     :", repr(cp))
    print("trimmed    :", trimmed)
    print()

    seq = ["ON", "OFF"]
    trimmed, cp = rmcp(seq)
    print("input      :", seq)
    print("prefix     :", repr(cp))
    print("trimmed    :", trimmed)
    print()

    print("=== relative tests ===")
    print("relative('ON', 'ON')            =", relative("ON", "ON"))
    print("relative('ON', 'OFF')           =", relative("ON", "OFF"))
    print("relative('FREQ', 'FREQu')       =", relative("FREQ", "FREQu"))
    print("relative('', '')                =", relative("", ""))
    print("relative('', 'ABC')             =", relative("", "ABC"))
    print()

    print("=== fstrcmp tests ===")
    possibilities = ("ON", "OFF")
    print("fstrcmp('ON', ('ON','OFF'))")
    print(" ->", fstrcmp("ON", possibilities))
    print()

    print("fstrcmp('OF', ('ON','OFF'))")
    print(" ->", fstrcmp("OF", possibilities))
    print()

    possibilities = (
        "SENS:FREQ:START",
        "SENS:FREQ:STOP",
        "SENS:FREQ:CENT",
        "SENS:BAND:RES",
    )

    print("fstrcmp('SENS:FREQ:STAR', possibilities)")
    print(" ->", fstrcmp("SENS:FREQ:STAR", possibilities))
    print()

    print("fstrcmp('freq:start', possibilities, ignorecase=True)")
    print(" ->", fstrcmp("freq:start", possibilities, ignorecase=True))
    print()

    print("fstrcmp('SENS:FREQ:ST', possibilities, cutoff=0.2)")
    print(" ->", fstrcmp("SENS:FREQ:ST", possibilities, cutoff=0.2))
    print()

    print("fstrcmp('BAND', possibilities, use_rmcp=False)")
    print(" ->", fstrcmp("BAND", possibilities, use_rmcp=False))
    print()

    print("=== exact match priority ===")
    possibilities = ("Voltage", "Current", "Power")
    print("fstrcmp('power', possibilities, ignorecase=True)")
    print(" ->", fstrcmp("power", possibilities, ignorecase=True))

    possibilities = (
        "SENS:FREQ:START",
        "SENS:FREQ:STOP",
        "SENS:FREQ:CENT",
        "SENS:BAND:RES",
        "OUTP:STAT",
        "SOUR:POW:LEV",
    )

    print("=== fstrcmp_scpi tests ===")
    tests = [
        "BAND",
        "FREQ",
        "STAR",
        "STOP",
        "CENT",
        "POW",
        "OUTP",
        "STAT",
        "SENS:BAND:RES",
    ]

    for t in tests:
        print(f"{t!r} -> {fstrcmp_scpi(t, possibilities)}")