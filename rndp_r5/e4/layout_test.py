import sys, time
import elay, eplace, eroute
nl = elay.read_nl('/tmp/eng.nl')
t=time.time(); order = eplace.order(nl, seed=1); print('place', time.time()-t, len(order))
cmds, info = eroute.route(nl, order, R=int(sys.argv[1]) if len(sys.argv)>1 else 22, Z=14)
print('cmds', len(cmds), 'W', info['W'], 'H', info['H'], 'nlate', info['nlate'], 'xa', info['pb'])
import collections; print(collections.Counter(c[0] for c in cmds))
