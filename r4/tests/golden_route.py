#!/usr/bin/env python3
"""golden_route.py [--write] NL -- normative placement (place_ref, permuted numbering seed 12, order seed 1) -> serpentine fold -> rowchan (R=22, Z=14)
-> arm command list (lay.commands, same text as the rndp build file but without the board offset).  Prints the sha256 of the command text and the .lay text.
--write stores golden/<name>.cmds + .sha256; without it the result is compared with the stored golden."""
import hashlib, os, random, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, '..', 'tools'), HERE]
import lay, rowchan, place_ref
args = [a for a in sys.argv[1:] if not a.startswith('--')]; write = '--write' in sys.argv
path = args[0]; name = os.path.basename(path).replace('.nl', '') + '_' + os.path.basename(os.path.dirname(os.path.abspath(path)))
nl = lay.read_nl(path); N = len(nl.nodes); R = 22
perm = list(range(N)); random.Random(12).shuffle(perm)
def rn(t):
    m = re.match(r'^n(\d+)(.*)$', t); return f'n{perm[int(m.group(1))]}{m.group(2)}' if m else t
new = [None] * N
for k, (kind, ins) in enumerate(nl.nodes): new[perm[k]] = (kind, [rn(t) for t in ins])
nl.nodes = new; nl.ports = [(n, rn(t)) for n, t in nl.ports]
o = place_ref.order(nl, seed=1)
cols = -(-N // R); rc = [None] * N
for rank, k in enumerate(o): r = rank // cols; j = rank % cols; rc[k] = (r, cols - 1 - j if r % 2 else j)
text, st = rowchan.layout(nl, R, 14, rc)
L = lay.read_lay_text(text) if hasattr(lay, 'read_lay_text') else None
open('/tmp/golden_tmp.lay', 'w').write(text); L = lay.read_lay('/tmp/golden_tmp.lay')
cmds = lay.commands(L, nl, [])
lines = []
for c in cmds:
    lines.append(' '.join(str(x) for x in c))
ctext = '\n'.join(lines) + '\n'
h = hashlib.sha256(ctext.encode()).hexdigest(); hl = hashlib.sha256(text.encode()).hexdigest()
gd = os.path.join(HERE, '..', 'golden')
print(f'{name}: board {st["W"]} x {st["H"]}, {len(cmds)} commands, cmds sha256 {h[:16]}, lay sha256 {hl[:16]}')
if write:
    open(f'{gd}/{name}.cmds', 'w').write(ctext); open(f'{gd}/{name}.sha256', 'w').write(f'{h}  cmds\n{hl}  lay\n'); print('golden written')
else:
    ref = open(f'{gd}/{name}.sha256').read().split(); ok = ref[0] == h and ref[2] == hl
    print('golden', 'MATCH' if ok else 'MISMATCH'); sys.exit(0 if ok else 1)
