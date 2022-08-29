from os.path import commonprefix
from Levenshtein import distance as ldistance

def rmcp(seq, ignorecase=True):
    """remove common prefix from sequence elements"""
    if ignorecase is True:
        seq = [s.lower() for s in seq]
    cp = commonprefix(seq)
    n = len(cp)
    return [s[n:] for s in seq]


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
    if first_must_match and a[0] != b[0]:
        r = 0.0
    else:
        d = distance(a, b)
        longer = float(max((len(a), len(b))))
        shorter = float(min((len(a), len(b))))
        r = ((longer - d) / longer) * (shorter / longer)
    return r


def distance(a, b):
    dist = levenshtein(a, b, ch_cost=1, add_cost=1, del_cost=1)
    #    print a, b, dist
    return dist


def old_fstrcmp(a, possibilities, n=None, cutoff=None, ignorecase=True):
    a = a.strip("'")
    a = a.strip('"')
    if n is None:
        n = 3  # difflibs default
    if cutoff is None:
        cutoff = 0.0  # don't sort out not-so-good matches

    if ignorecase:
        dists = [relative(a.lower(), p) for p in rmcp(possibilities, ignorecase=ignorecase)]
        # print rmcp(possibilities,ignorecase=ignorecase)
    else:
        dists = [relative(a, p) for p in rmcp(possibilities, ignorecase=ignorecase)]
    # handle perfect matches
    for i, p in enumerate(possibilities):
        if (ignorecase and a.lower() == p.lower()) or a == p:
            dists[i] = 1

    pairs = list(zip(dists, possibilities))
    # print pairs
    # return [v for d,v in sorted(pairs,None,None,True) if d >= cutoff] 2.7
    return [v for d, v in sorted(pairs, key=None, reverse=True) if d >= cutoff]

def fstrcmp(a, possibilities, n=None, cutoff=None, ignorecase=True):
    a = a.strip("'")
    a = a.strip('"')

    if ignorecase:
        dists = [ldistance(a.lower(), p) for p in rmcp(possibilities, ignorecase=ignorecase)]
        # print rmcp(possibilities,ignorecase=ignorecase)
    else:
        dists = [ldistance(a, p) for p in rmcp(possibilities, ignorecase=ignorecase)]

    pairs = list(zip(dists, possibilities))
    return [v for d, v in sorted(pairs, key=None)]


def levenshtein(a, b, ch_cost=1, add_cost=1, del_cost=1):
    """Calculates the Levenshtein distance between a and b."""
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space
        a, b = b, a
        n, m = m, n

    current = list(range(n + 1))
    for i in range(1, m + 1):
        previous, current = current, [i] + [0] * n
        for j in range(1, n + 1):
            add, delete = previous[j] + add_cost, current[j - 1] + del_cost
            change = previous[j - 1]
            if a[j - 1] != b[i - 1]:
                change = change + ch_cost
            current[j] = min(add, delete, change)

    return current[n]


if __name__ == "__main__":
    from sys import argv

    # print levenshtein(argv[1],argv[2],ch_cost=float(argv[3]), add_cost=float(argv[4]), del_cost=float(argv[5]))
    print(old_fstrcmp(argv[1], ('ON', 'OFF')))
    print(fstrcmp(argv[1], ('ON', 'OFF')))
