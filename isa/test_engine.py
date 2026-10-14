import sys, os
import common
if os.environ.get('BIG', '1') == '1':
    common.AMASK = 0x3FFF; common.ROM_BYTES = 0x3000
import builder as B, engine, machine_row as MR

def run(ab, limit=200_000_000):
    a, plan, V, sl = engine.make_program(ab)
    code = a.assemble()
    R, outs = plan.R, plan.outs
    ref = MR.commands(R, outs, code, B.OX, B.OY)
    m, steps, hw = B.run_program(code, limit=limit)
    got = B.decode_cmds(m.armlog)
    gp, rp = [t for t in got if t[0] != 'wire'], [t for t in ref if t[0] != 'wire']
    gw, rw = [t for t in got if t[0] == 'wire'], [t for t in ref if t[0] == 'wire']
    print(f'RAM {1<<ab} B: ROM image {len(code)} B (stream {sum(sl)}), instrs {steps}, accesses {m.accesses}, RAM high-water {hw}')
    ok = gp == rp
    print('place/rom', 'PASS' if ok else 'FAIL', len(gp), len(rp))
    if not ok:
        for i, (g, e) in enumerate(zip(gp, rp)):
            if g != e: print('  first diff', i, g, e); break
    okw = sorted(gw) == sorted(rw)
    print('wires (as a set)', 'PASS' if okw else 'FAIL', len(gw), len(rw))
    print('EN second-to-last group, run wires last:', gw[-3:-2] == rw[-3:-2] and gw[-2:] == rw[-2:])
    if not okw:
        sg, sr = set(gw), set(rw)
        print('  missing', sorted(sr - sg)[:6], 'extra', sorted(sg - sr)[:6], len(sr - sg), len(sg - sr))
    return ok and okw

if __name__ == '__main__':
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 6)
