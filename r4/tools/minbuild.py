import sys
mn = 10**9
for l in open(sys.argv[1]):
    w = l.split()
    if not w: continue
    if w[0] in ('place', 'track'): v = [int(w[2]), int(w[3])] + ([int(w[4]), int(w[5])] if w[0] == 'track' else [])
    elif w[0] == 'via': v = [int(w[1]), int(w[2])]
    else: continue
    mn = min(mn, *v)
print(mn)

