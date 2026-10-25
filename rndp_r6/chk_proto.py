#!/usr/bin/env python3
"""chk_proto.py TAG -- turn the mrouter result of proto_plane.py into a rndp build, load it, and compare world nets of gate pins with the logical nets."""
import sys, subprocess, collections
tag = sys.argv[1]; RNDP = '/home/claude/rndp/target/release/rndp'
net_of_pad = {}; gates = []; cur = None
for l in open(f'/tmp/{tag}.prob'):
    t = l.split()
    if t[0] == 'pad': net_of_pad[(int(t[1]), int(t[2]))] = int(t[3])
    elif t[0] == 'd' and t[3] == '0': gates.append((int(t[1]) - 1, int(t[2])))
B = []
for x, y in gates: B.append(f'place 0 {x} {y} 0 0')
for l in open(f'/tmp/{tag}.out'):
    t = l.split()
    if t[2] == 'T': B.append(f'track {t[4]} {t[5]} {t[6]} {t[7]} {t[8]}')
    elif t[2] == 'V': B.append(f'via {t[4]} {t[5]}')
OX = OY = 16
def sh(line):
    t = line.split()
    if t[0] == 'place': return f'place {t[1]} {int(t[2])+OX} {int(t[3])+OY} {t[4]} {t[5]}'
    if t[0] == 'track': return f'track {t[1]} {int(t[2])+OX} {int(t[3])+OY} {int(t[4])+OX} {int(t[5])+OY}'
    return f'via {int(t[1])+OX} {int(t[2])+OY}'
open(f'/tmp/{tag}.build', 'w').write('\n'.join(sh(b) for b in B) + '\n')
r = subprocess.run([RNDP, '--build', f'/tmp/{tag}.build', '--rom', 'off', '--ram', 'off', '--layers', '2', '--width', '2048', '--height', '4096', '--steps', '0', '--dump-pads', f'/tmp/{tag}.pads'], capture_output=True, text=True)
print((r.stdout + r.stderr)[-500:])
worlds = collections.defaultdict(set); logical = collections.defaultdict(set); bad = 0
for l in open(f'/tmp/{tag}.pads'):
    pi, kind, pin, x, y, net = l.split(); k = (int(x) - OX, int(y) - OY)
    if k not in net_of_pad: bad += 1; continue
    ln = net_of_pad[k]
    if ln < 0: continue
    worlds[int(net)].add(ln); logical[ln].add(int(net))
opens = {n: s for n, s in logical.items() if len(s) > 1}; shorts = {n: s for n, s in worlds.items() if len(s) > 1}
print(f'gates {len(gates)} logical nets {len(logical)} undeclared pins {bad} opens {len(opens)} shorts {len(shorts)}')
