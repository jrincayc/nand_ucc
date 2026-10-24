import sys, time
import elay, eplace, maze2
nl = elay.read_nl(sys.argv[1]); order = eplace.order(nl, seed=1)
for R, px, py in [(36, 7, 6), (35, 7, 6), (34, 7, 6), (36, 6, 7)]:
    try:
        t = time.time(); cmds, info = maze2.route_engine(nl, order, 10000, pitch=(px, py), R=R, iters=60, tag='sw2')
    except AssertionError as e:
        print('R', R, px, py, 'does not fit', e, flush=True); continue
    ov = sum(1 for _ in open('/tmp/over.txt'))
    print('R', R, 'pitch', px, py, 'grid', info['grid'], 'overused', ov, 'cmds', len(cmds), 'time', round(time.time() - t), flush=True)
