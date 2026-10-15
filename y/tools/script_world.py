"""script_world.py -- the two helpers of X's isa/script_world.py that the Y harness needs (copied so that Y does not depend on the
X tree): to_script(cmds) writes a command list as an rndw driver script, reg_writes(cmds) counts the arm register writes the driver issues.
A command is ('place', kind, x, y) | ('wire', x1, y1, x2, y2) | ('rom', x, y, addr, val) | ('nop', n)."""


def to_script(cmds):
    out = []
    for cm in cmds:
        out.append(' '.join(str(v) for v in cm))
    return '\n'.join(out) + '\n'


def reg_writes(cmds):
    """Register writes the driver issues (same shadow logic: skip unchanged non-CMD registers)."""
    shadow = [None] * 16; n = 0; kinds = {'nand': 0, 'dff': 1, 'rom': 2, 'arm': 3}
    def w(r, v):
        nonlocal n
        if r != 15 and shadow[r] == v: return
        shadow[r] = v; n += 1
    def w16(lo, v): w(lo, v & 255); w(lo + 1, (v >> 8) & 255)
    for cm in cmds:
        if cm[0] == 'place': w16(0, cm[2]); w16(2, cm[3]); w(8, kinds[cm[1]]); w(9, 0); w(15, 1)
        elif cm[0] == 'wire': w16(0, cm[1]); w16(2, cm[2]); w16(4, cm[3]); w16(6, cm[4]); w(15, 2)
        elif cm[0] == 'rom': w16(0, cm[1]); w16(2, cm[2]); w16(4, cm[3]); w(10, cm[4]); w(15, 3)
        elif cm[0] == 'nop': n += cm[1]
    return n
