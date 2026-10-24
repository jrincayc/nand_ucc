import sys, time, collections
import elay, eplace, maze, streamcost as SC
nl = elay.read_nl('/tmp/eng.nl'); order = eplace.order(nl, seed=1)
W = 932; RX = 100
R = int(sys.argv[1]); pit = int(sys.argv[2]); lf = sys.argv[3] == 'long'
pri = set()
for it in range(int(sys.argv[4]) if len(sys.argv) > 4 else 1):
    t = time.time(); cmds, info = maze.route_engine(nl, order, W, RX, pitch=(pit, pit), R=R, longfirst=lf, priority=pri)
    print('iter', it, 'time', round(time.time() - t), 'fails', info['fails'], 'nets failed', len(info['failed']), flush=True)
    if not info['failed']: break
    pri |= info['failed']
print(collections.Counter(c[0] for c, l in cmds))
body = [c for c, l in cmds if l == 0]; tail = [c for c, l in cmds if l]
norm = lambda c: ('track', c[1], c[4], c[5], c[2], c[3]) if c[0] == 'track' and (c[3], c[2]) > (c[5], c[4]) else c
print('words', SC.cost(sorted([norm(c) for c in body], key=SC.key) + [norm(c) for c in tail]))
