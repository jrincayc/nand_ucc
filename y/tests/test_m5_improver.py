"""test_m5_improver.py -- the assembly improver (src/improver.asm) against the normative reference ref_improve.improve_record, byte for byte."""
import sys, os, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asmrun as AR, ref_improve as R, hd as HDM, common

DRIVER = """
.org ROM_BASE
main:                        // test driver: improve type 15 (the test record)
    SET ITY, 15              // type 15
    CALL improve_type        // improve it
halt:
    @halt                    // A = here
    0;JMP                    // stop
.org ROM_BASE + 0x3000       // aligned
hd_dir:                      // directory
    .space 30                // slots 0..14 empty
    .word testrec            // slot 15
testrec:
    .space 120               // the test record is patched in here
.org ROM_BASE + 0x40         // the improver code follows the driver
"""
_img = None


def rec_bytes(n_in, slots, outs):
    S = len(slots); b = [1, n_in, len(outs), S]; k = 0
    for x in slots:
        if x is None: k += 1; continue
        if k: b += [2, k, 0]; k = 0
        b += [0, x[0], x[1]]
    if k: b += [2, k, 0]
    return b + list(outs)


def build():
    global _img
    if _img is None: _img = AR.build(DRIVER)
    return _img


def run_asm(n_in, slots, outs, ramn=256):
    img, syms = build()
    rb = rec_bytes(n_in, slots, outs); ta = syms['testrec']
    m, n = AR.run(img, syms, rom_patch={ta: bytes(rb)}, ramn=ramn)
    if not m.ram[syms['IMPR']]: return None, n, m, syms
    ln = m.ram[syms['RECN']]
    return bytes(m.ram[syms['RECB']:syms['RECB'] + ln]), n, m, syms


def parse(b):
    n_in, n_out, S = b[1], b[2], b[3]; sl = []; q = 4
    while len(sl) < S:
        k, x, y = b[q:q + 3]; q += 3
        if k == 2: sl += [None] * x
        else: sl.append((x, y))
    return n_in, sl, list(b[q:q + n_out])


def expect(n_in, slots, outs):
    r = R.improve_record(n_in, slots, outs)
    return None if r is None else bytes(rec_bytes(n_in, *r))


if __name__ == '__main__':
    import exp_variants as E
    cases = []
    hd = HDM.read(open(os.path.join(HERE, '..', 'hd', 'core_r7.hd')).read())
    for m in hd.modules:
        if R.improvable(m): cases.append((m.name, m.n_in, list(m.gates), list(m.outs)))
    for k, (n, g, o) in E.unlisted().items(): cases.append((k, n, g, o))
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    for s in range(N):
        n, g, o = E.rnd(s)
        if len(set(o)) == len(o) and len(g) <= 14: cases.append((f'rnd{s}', n, g, o))
    # slot-form inputs: holes spread through the module (references renumbered)
    for s in range(N):
        n, g, o = E.rnd(1000 + s)
        if len(set(o)) != len(o) or len(g) > 14: continue
        pos = random.Random(s).randrange(len(g) + 1); sh = lambda x: x if x < n + pos else x + 1
        sl = [(sh(a), sh(b)) for a, b in g]; sl.insert(pos, None); cases.append((f'hole{s}', n, sl, [sh(x) for x in o]))
    bad = 0; tot_i = 0; hw = 0; second = 0
    for name, n, g, o in cases:
        got, ninstr, m, syms = run_asm(n, g, o); want = expect(n, g, o); tot_i += ninstr; hw = max(hw, m.hw)
        ok = got == want
        if ok and got is not None:                                   # the improved record must be a fixed point of the improver
            n2, sl2, o2 = parse(got)
            g2, _, _, _ = run_asm(n2, sl2, o2)
            if g2 is not None: ok = False; print('NOT A FIXED POINT', name)
            second += 1
        if not ok: bad += 1
        if not ok or name in ('not', 'and', 'or', 'xor', 'mux', 'ha', 'fa', 'xnor', 'and3', 'maj'):
            print(('ok  ' if ok else 'FAIL'), name, 'gates', len(g), '->', None if want is None else sum(1 for x in R.improve_record(n, g, o)[0] if x), f'{ninstr:,} instr')
            if not ok: print('   want', want and list(want)); print('   got ', got and list(got))
    print('cases', len(cases), 'bad', bad, f'instructions total {tot_i:,}', f'RAM high-water mark: byte {hw} (so {hw + 1} bytes); fixed-point checks {second}')
    sys.exit(1 if bad else 0)
