"""Exhaustive search for minimum-NAND circuits (experiment E1).  Signals are truth-table bitmasks.
Iterative deepening on gate count g; gate k picks inputs (i<=j) among the n inputs + earlier gates; to cut
permutation duplicates we require each gate to be used later or be an output (checked at the end) and gate
pair indices to be non-decreasing in (j,i) order only when independent -- here simply by requiring distinct truth tables."""
import sys, time, itertools
def search(n, targets, gmax, tlimit=600):
    N = 1 << n; full = (1 << N) - 1
    ins = []
    for v in range(n):
        m = 0
        for r in range(N):
            if (r >> v) & 1: m |= 1 << r
        ins.append(m)
    t0 = time.time(); nodes = [0]
    for g in range(1, gmax + 1):
        sig = list(ins); prog = []
        tg = set(targets)
        def rec(k):
            nodes[0] += 1
            if time.time() - t0 > tlimit: raise TimeoutError
            need = len(tg - set(sig))
            if need > g - k: return False
            if k == g:
                return not (tg - set(sig))
            L = len(sig)
            for j in range(L):
                for i in range(j + 1):
                    t = full ^ (sig[i] & sig[j])
                    if t in sig: continue          # duplicate function: never useful in a minimum circuit
                    sig.append(t); prog.append((i, j))
                    if rec(k + 1): return True
                    sig.pop(); prog.pop()
            return False
        try:
            if rec(0): return g, list(prog), nodes[0], time.time() - t0
        except TimeoutError:
            return None, None, nodes[0], time.time() - t0
    return None, None, nodes[0], time.time() - t0
def tt(n, f):
    m = 0
    for r in range(1 << n):
        if f(*[(r >> v) & 1 for v in range(n)]): m |= 1 << r
    return m
if __name__ == '__main__':
    cases = {
     'not':(1,[tt(1,lambda a:1-a)]),
     'and':(2,[tt(2,lambda a,b:a&b)]),
     'or':(2,[tt(2,lambda a,b:a|b)]),
     'xor':(2,[tt(2,lambda a,b:a^b)]),
     'half_adder':(2,[tt(2,lambda a,b:a^b),tt(2,lambda a,b:a&b)]),
     'mux':(3,[tt(3,lambda a,b,s:b if s else a)]),
     'maj':(3,[tt(3,lambda a,b,c:(a&b)|(a&c)|(b&c))]),
     'xor3':(3,[tt(3,lambda a,b,c:a^b^c)]),
    }
    for k,(n,t) in cases.items():
        g,p,nd,sec=search(n,t,9,120)
        print(k,'min NAND',g,'nodes',nd,f'{sec:.1f}s',p)
