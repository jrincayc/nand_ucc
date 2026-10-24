import sys, subprocess, time
import elay, eplace, maze2
nlf = sys.argv[1]; nl = elay.read_nl(nlf); order = eplace.order(nl, seed=1)
for R, pit in [(26, 7), (28, 7), (30, 7)]:
    try:
        t = time.time(); cmds, info = maze2.route_engine(nl, order, 10000, pitch=(pit, pit), R=R, iters=40, tag='sw')
    except AssertionError as e:
        print(R, pit, 'does not fit', e); continue
    ov = sum(1 for _ in open('/tmp/over.txt'))
    print('R', R, 'pitch', pit, 'grid', info['grid'], 'overused', ov, 'cmds', len(cmds), 'time', round(time.time() - t), flush=True)
