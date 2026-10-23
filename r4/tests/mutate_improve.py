#!/usr/bin/env python3
"""mutate_improve.py -- Y's V8 for the assembly improver: apply single-line rule mutations to a copy of kernels/improve.s; the comparison with
ref_improve (test_improve_asm.py) must FAIL for every mutant ('killed').  A surviving mutant means the test is too weak.
Not in the list (no discriminating module exists or was found): "outputs not protected in saved" is redundant because FO already counts every output; "GMAX 6 -> 5" gives the same result as GMAX 6 on all 255 three-variable sum-of-products modules and 6000 random modules tried.
Also not mutated: the skip of a table already present in the search (changes only the cost)."""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); K = os.path.join(HERE, '..', 'kernels')
src = open(os.path.join(K, 'improve.s')).read()
MUT = [
 ("gmax = saved - 1 (not saved)",  "    addi a0, a0, -1\n    li   t0, 6", "    li   t0, 6"),
 ("fan-out test ignored",          "    bne  a3, a4, tc8\n", "    nop\n"),
 ("cuts not sorted (key order)",   "    bleu a2, a0, mc5", "    j    mc5"),
 ("compact: no merge of identical gates", "    bne  a0, t2, cp4\n    add  a0, s0, a5", "    j    cp4\n    add  a0, s0, a5"),
 ("strict gain test off",          "    bgeu a0, t0, ir_none\n    // layout", "    nop\n    // layout"),
 ("record limit 40 -> 60",         "    li   t1, 40", "    li   t1, 60"),
 ("topological layout check off",  "    bgeu a1, t1, ir_none\n    bgeu a5, t1, ir_none", "    nop\n    nop"),
 ("partition: outputs not last",   "    beq  t1, a3, pt2\n    li   t2, 2", "    nop\n    li   t2, 2"),
 ("rewrite: users keep the root",  "    bne  a1, a3, rw11\n    mv   a1, a4", "    j    rw11\n    mv   a1, a4"),
]
killed = 0
for name, old, new in MUT:
    if old not in src: print('PATTERN NOT FOUND', name); sys.exit(2)
    d = tempfile.mkdtemp()
    for f in ('memmap_imp.s',): shutil.copy(os.path.join(K, f), d)
    open(os.path.join(d, 'improve.s'), 'w').write(src.replace(old, new, 1))
    r = subprocess.run([sys.executable, os.path.join(HERE, 'test_improve_asm.py')], env=dict(os.environ, IMP_KDIR=d, IMP_NRAND='120', IMP_NSOP='30'), capture_output=True, text=True)
    dead = r.returncode != 0
    killed += dead; print(('killed   ' if dead else 'SURVIVED ') + name)
print(f'{killed}/{len(MUT)} mutants killed'); sys.exit(0 if killed == len(MUT) else 1)
