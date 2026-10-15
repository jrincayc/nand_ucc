"""run_y_world.py -- RNDW end-to-end for Y/M4:  the driver builds generation 1 from the reference commands (real ROM image);
generation 1 runs the builder and builds generation 2 through its own arm.  usage: run_y_world.py HDFILE STEPS [OUTDIR]     (HDFILE = the seed description; the improved child is computed with ref_improve)
M6: the ROM carries builder + improver; generation 1 (seed) builds generation 2 (improved), generation 2 builds generation 3 (= generation 2)."""
import os, sys, subprocess, time, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ('tools', 'isa', 'tests', '.'):
    sys.path.insert(0, os.path.join(HERE, '..', d))
import hd as HDM, ref_flatten as RF, run_builder as RB, hd2asm, ref_improve as RI
import common as _c
AB_ = _c.AB
from script_world import to_script, reg_writes      # tools/script_world.py (vendored from X)
# the simulator: $RNDW, else <nandgen>/rndw/target/release/rndw (cargo build --release --offline in nandgen/rndw)
RNDW = os.environ.get('RNDW', os.path.join(HERE, '..', '..', 'rndw', 'target', 'release', 'rndw'))


def seed_commands(f, image):
    cmds = RF.commands(f, image, 0, RF.STRIDE)
    # the driver (the harness) waits a few ticks before the EN wire and before the RUN wires, as in X
    en = max(i for i, c in enumerate(cmds) if c[0] == 'wire' and c[3] == 0 and c[4] == RF.STRIDE + 4)
    run = len(cmds) - 2
    return cmds[:en] + [('nop', 3), cmds[en], ('nop', 3)] + cmds[en + 1:]


SRC = [os.path.join(HERE, '..', 'src', f) for f in ('macros.asm', 'ram.asm', 'builder.asm', 'improver.asm')]


def image_of(hd, out, tag):
    os.makedirs(out, exist_ok=True); data = os.path.join(out, tag + '_data.asm')
    open(data, 'w').write(hd2asm.Enc(hd).encode().text())
    img = RB.assemble(SRC + [data], os.path.join(out, 'asm_' + tag)); open(os.path.join(out, tag + '.bin'), 'wb').write(img)
    return img


if __name__ == '__main__':
    hdfile, steps = sys.argv[1], int(sys.argv[2])
    out = sys.argv[3] if len(sys.argv) > 3 else tempfile.mkdtemp(); os.makedirs(out, exist_ok=True)
    hd0 = HDM.read(open(hdfile).read()); hd1 = RI.improve_hd(hd0)[0]
    open(os.path.join(out, 'child.hd'), 'w').write(HDM.write(hd1))
    img0, img1 = image_of(hd0, out, 'seed'), image_of(hd1, out, 'child')
    cmds = seed_commands(RF.flatten(hd0), img0); nw = reg_writes(cmds)
    sf = os.path.join(out, 'seed.script'); open(sf, 'w').write(to_script(cmds))
    final = os.path.join(out, 'final.txt')
    # Checkpointing (the simulator has no periodic save, so the run is cut into segments, each ending with --save).
    # CHUNK (env, ticks per segment; default 10,000,000) ; set RESUME=1 to continue an interrupted run in the same OUTDIR from its newest
    # OUT/ckpt_<ticks>.txt (ticks = ticks run after the driver script).  A resumed state restores the DFF values (checked: bit-identical result).
    import glob, re
    chunk = int(os.environ.get('CHUNK', 10_000_000))
    done, prev = 0, None
    if os.environ.get('RESUME'):
        cks = sorted(glob.glob(os.path.join(out, 'ckpt_*.txt')), key=lambda f: int(re.search(r'ckpt_(\d+)', f).group(1)))
        if cks: prev = cks[-1]; done = int(re.search(r'ckpt_(\d+)', prev).group(1))
    base = ['--width', '65536', '--height', '4096', '--rom-bits', str(AB_ - 1)]
    print('ROM image', len(img0), 'B; script register writes', nw, '; running', steps, 'ticks after the script; checkpoint every', chunk,
          ('; resuming from ' + prev) if prev else '', flush=True)
    t = time.time(); r = None
    while done < steps:
        n = min(chunk, steps - done); done += n; ck = os.path.join(out, f'ckpt_{done}.txt')
        args = [RNDW] + (['--world', prev, '--steps', str(n)] if prev else base + ['--script', sf, '--steps', str(nw + n)]) + ['--save', ck]
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(ck):
            print(r.stdout[-1500:], r.stderr[-500:]); sys.exit(f'segment ending at {done} ticks failed; rerun with RESUME=1 to continue from {prev}')
        print(f'  {done}/{steps} ticks  wall {time.time()-t:.0f}s  saved {ck}', flush=True)
        if prev and os.path.basename(prev) != 'final.txt': os.remove(prev)     # keep only the newest checkpoint
        prev = ck
    os.replace(prev, final)
    print(r.stdout[-1500:] if r else '', r.stderr[-500:] if r else ''); print(f'wall {time.time()-t:.0f}s; final state {final}')
