#!/usr/bin/env python


def levenshtein(a,b, ch_cost=1, add_cost=1, del_cost=1):
    "Calculates the Levenshtein distance between a and b."
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space
        a,b = b,a
        n,m = m,n
        
    current = range(n+1)
    for i in range(1,m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1,n+1):
            add, delete = previous[j]+add_cost, current[j-1]+del_cost
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + ch_cost
            current[j] = min(add, delete, change)
            
    return current[n]

if __name__=="__main__":
    from sys import argv
    print levenshtein(argv[1],argv[2],ch_cost=float(argv[3]), add_cost=float(argv[4]), del_cost=float(argv[5]))
