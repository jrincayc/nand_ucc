import sys, time, collections
import elay, eplace, maze2, fmt2
nlf = sys.argv[1]; R = int(sys.argv[2]); pit = int(sys.argv[3]); W = int(sys.argv[4]) if len(sys.argv) > 4 else 10000
nl = elay.read_nl(nlf); order = eplace.order(nl, seed=1)
t = time.time(); cmds, info = maze2.route_engine(nl, order, W, pitch=(pit, pit), R=R); print('time', round(time.time() - t), 'fails', info['fails'], 'grid', info['grid'])
print(collections.Counter(c[0] for c, l in cmds))
body = [c for c, l in cmds if l == 0]
words, st = fmt2.encode(body); ones = sum(bin(w).count('1') for w in words)
print('data words', len(words), dict(st), 'ones', ones)
