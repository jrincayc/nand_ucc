"""common.py -- helpers for the R5 experiments: gate counting of the used cone and a small cycle simulator for Net netlists (tools/netlist.py)."""
import os, sys
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'r4', 'tools')]
from netlist import Net

def count(net, roots):
    """(NAND, DFF) in the cone of influence of roots, following DFF D inputs."""
    seen = set(); stack = [r for r in roots if r > 1]
    while stack:
        n = stack.pop()
        if n in seen: continue
        seen.add(n); k = net.kind[n]
        if k[0] == 'in': continue
        for s in k[1:]:
            if s > 1 and s not in seen: stack.append(s)
    return sum(1 for n in seen if net.kind[n][0] == 'nand'), sum(1 for n in seen if net.kind[n][0] == 'dff')

class Sim:
    """cycle simulator: set inputs, comb() evaluates NANDs in id order from inputs and DFF states, tick() latches."""
    def __init__(self, net, roots):
        self.net = net; self.v = [0] * len(net.kind); self.v[1] = 1
        seen = set(); stack = [r for r in roots if r > 1]
        while stack:
            n = stack.pop()
            if n in seen: continue
            seen.add(n); k = net.kind[n]
            if k[0] == 'in': continue
            for s in k[1:]:
                if s > 1 and s not in seen: stack.append(s)
        self.nands = sorted(n for n in seen if net.kind[n][0] == 'nand'); self.dffs = sorted(n for n in seen if net.kind[n][0] == 'dff')
    def set(self, sig, val): self.v[sig] = val & 1
    def comb(self):
        v = self.v; k = self.net.kind
        for n in self.nands: a, b = k[n][1], k[n][2]; v[n] = 1 ^ (v[a] & v[b])
    def tick(self):
        self.comb(); v = self.v; k = self.net.kind
        nxt = {n: v[k[n][1]] for n in self.dffs}
        for n, x in nxt.items(): v[n] = x
        self.comb()
    def bus(self, sigs): return sum(self.v[s] << i for i, s in enumerate(sigs))
