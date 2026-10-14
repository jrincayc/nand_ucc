import sys, os, bisect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_builder import *
def load_syms(outdir):
    s = {}
    for l in open(os.path.join(outdir, 'symbols.txt')):
        n, _, v = l.partition('=')
        try: s[n.strip()] = int(v)
        except: pass
    return s
def lst(outdir):
    d = {}
    for l in open(os.path.join(outdir, 'rom.lst')):
        p = l.split('|')
        if len(p) >= 4:
            try: d[int(l.split()[0], 16)] = (p[1].strip(), p[3].strip()[:60])
            except: pass
    return d
def where(pc, syms):
    names = sorted((v, n) for n, v in syms.items() if v < 0x4000 and not n.startswith('ret') and v>=0x2000)
    i = bisect.bisect_right([v for v, _ in names], pc) - 1
    return f'{names[i][1]}+{pc - names[i][0]}'
if __name__ == '__main__':
    datafile = sys.argv[1]; N = int(sys.argv[2]); out = tempfile.mkdtemp()
    image = assemble(['../src/macros.asm', '../src/builder.asm', datafile], out)
    syms = load_syms(out); L = lst(out)
    m = MR(256); m.load_rom(0, image); cpu = H.CPU(m)
    for i in range(N):
        pc = cpu.pc
        cpu.step()
        if i >= N - int(sys.argv[3]): print(i, hex(pc), where(pc, syms), L.get(pc, ''), 'A=%x D=%x' % (cpu.A, cpu.D))
