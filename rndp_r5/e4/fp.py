import sys, os, pickle, collections
import engine2_net as E2, engine_net as EN, elay, eplace, maze2, fmt3
import pattern as PT
W = int(sys.argv[1]); M = 16255; pit = 9
N, sp = E2.build(W, M=M); info = EN.export_nl(N, sp, f'/tmp/fp_{W}_{os.environ.get('RSEED','1')}.nl'); print('NAND', info['nand'], 'DFF', info['dff'])
nl = elay.read_nl(f'/tmp/fp_{W}_{os.environ.get('RSEED','1')}.nl')
cmds, inf = maze2.route_engine(nl, eplace.order(nl, seed=int(os.environ.get('RSEED','1'))), W, pitch=(pit, pit), R=36)
body = [c for c, l in cmds if l == 0]; late = [c for c, l in cmds if l]
words, st = fmt3.encode(body)
npat = len(PT.build_pattern(150, 144, 0))
print('fails', inf['fails'], 'body', len(body), 'late', len(late), 'words', len(words), 'pat', npat)
pickle.dump((cmds, words), open(f'/tmp/fp_{W}_{os.environ.get('RSEED','1')}.pkl', 'wb'))
print('W_next >=', 1 + 15 + npat + len(words) + 3 + len(late) * 3)
