"""Shared harness for the ISA comparison (von Neumann: code and data in one address space).

Memory map (13-bit address bus, 8-bit data, one memory port):
  0x0000-0x0FEF  RAM (4080 bytes)
  0x0FF0-0x0FFF  ARM registers (write-only window; reads give 0).  ARM ADDR = A[3:0], DATA = data bus,
                 EN = write strobe & window select.  Writing register r = one arm register write.
  0x1000-0x1FFF  ROM (4 KiB, writes ignored).  Reset PC = 0x1000.  Child ROM address = A - 0x1000.
Cost proxy for time: memory accesses (instruction bytes fetched + data reads + data writes).
"""
import random

ARM_BASE, ROM_BASE = 0x0FF0, 0x1000
AMASK = 0x1FFF           # address mask; dev-only tests may widen it to model a larger ROM (set before use)
ROM_BYTES = 0x1000
P = dict(K1_N=300,                                   # K1: ROM bytes copied to the arm
         K2_M=40, K2_S=ROM_BASE + 0x800, K2_OUT=0x0200,           # K2: 9-bit fields unpacked
         K3_G=60, K3_NIN=8, K3_TBL=ROM_BASE + 0xA00, K3_VAL=0x0300,  # K3: bit-parallel NAND sim
         K4_NW=130, K4_X0=100, K4_Y0=50)              # K4: RAM-tile PLACE emitter
KERNELS = ['K1', 'K2', 'K3', 'K4']
DESC = {'K1': 'ROM->arm copy loop (PROGRAM_ROM per byte, 12-bit address)',
        'K2': 'unpack 9-bit node indices from a packed stream',
        'K3': 'bit-parallel NAND simulation loop (8 lanes per byte)',
        'K4': 'RAM-tile emitter: PLACE a DFF at computed 16-bit coordinates'}


class Machine:
    def __init__(self):
        self.ram = bytearray(ARM_BASE)
        self.rom = bytearray(ROM_BYTES)
        self.armlog = []
        self.fetch = self.dread = self.dwrite = 0

    def load_rom(self, off, data):
        self.rom[off:off + len(data)] = data

    def peek(self, a):
        a &= AMASK
        if a < ARM_BASE:
            return self.ram[a]
        return 0 if a < 0x1000 else self.rom[a - 0x1000]

    def rd(self, a, kind='d'):
        if kind == 'f':
            self.fetch += 1
        else:
            self.dread += 1
        return self.peek(a)

    def wr(self, a, v):
        a &= AMASK
        v &= 255
        self.dwrite += 1
        if a < ARM_BASE:
            self.ram[a] = v
        elif a < 0x1000:
            self.armlog.append((a - ARM_BASE, v))

    @property
    def accesses(self):
        return self.fetch + self.dread + self.dwrite


def snapshots(log):
    """Arm register state (regs 0..10) plus the command, at every CMD write (registers persist)."""
    regs, out = [0] * 16, []
    for r, v in log:
        if r == 15:
            out.append(tuple(regs[:11]) + (v,))
        else:
            regs[r] = v
    return out


def prepare(kernel, m, rng):
    """Load data for the kernel into m; return check(m) -> None or an error string."""
    if kernel == 'K1':
        n = P['K1_N']
        return lambda m: _cmp(snapshots(m.armlog),
                              snapshots([w for p in range(n) for w in
                                         [(10, m.peek(ROM_BASE + p)), (4, p & 255), (5, p >> 8), (15, 3)]]))
    if kernel == 'K2':
        mm = P['K2_M']
        stream = bytes(rng.getrandbits(8) for _ in range((9 * mm + 7) // 8 + 2))
        m.load_rom(P['K2_S'] - ROM_BASE, stream)
        exp = []
        for k in range(mm):
            v = 0
            for i in range(9):
                bp = 9 * k + i
                v |= ((stream[bp >> 3] >> (bp & 7)) & 1) << i
            exp += [v & 255, v >> 8]
        out = P['K2_OUT']
        return lambda m: None if [m.peek(out + i) for i in range(2 * mm)] == exp else 'K2 output mismatch'
    if kernel == 'K3':
        g, nin, tbl, val = P['K3_G'], P['K3_NIN'], P['K3_TBL'], P['K3_VAL']
        v = [rng.getrandbits(8) for _ in range(nin)]
        for i, x in enumerate(v):
            m.ram[val + i] = x
        table = bytearray()
        for gi in range(g):
            a, b = rng.randrange(nin + gi), rng.randrange(nin + gi)
            table += bytes([(val + a) & 255, (val + a) >> 8, (val + b) & 255, (val + b) >> 8])
            v.append(~(v[a] & v[b]) & 255)
        m.load_rom(tbl - ROM_BASE, bytes(table))
        return lambda m: None if [m.peek(val + i) for i in range(nin + g)] == v else 'K3 value mismatch'
    if kernel == 'K4':
        x0, y0 = P['K4_X0'], P['K4_Y0']
        w = [(8, 1), (9, 0)]
        for wd in range(P['K4_NW']):
            for j in range(8):
                x, y = x0 + 24 * (wd & 63) + 3 * j, y0 + 4 * (wd >> 6)
                w += [(0, x & 255), (1, x >> 8), (2, y & 255), (3, y >> 8), (15, 1)]
        return lambda m: _cmp(snapshots(m.armlog), snapshots(w))
    raise KeyError(kernel)


def _cmp(got, exp):
    if got == exp:
        return None
    for i, (g, e) in enumerate(zip(got, exp)):
        if g != e:
            return f'command #{i}: got {g}, expected {e}'
    return f'{len(got)} commands, expected {len(exp)}'


def run(isa, kernel, seed=1, max_steps=5_000_000):
    """Assemble `kernel` for `isa`, run it, check results.  Returns a dict of measurements."""
    rng = random.Random(f'{seed}-{kernel}')
    m = Machine()
    code = isa.assemble(kernel, P)
    assert len(code) < 0x800, 'code too large for the layout'
    m.load_rom(0, code)
    check = prepare(kernel, m, rng)
    cpu = isa.CPU(m)
    steps = 0
    while cpu.step():
        steps += 1
        if steps > max_steps:
            raise RuntimeError(f'{isa.NAME} {kernel}: did not halt')
    err = check(m)
    return dict(ok=err is None, err=err, code=len(code), instrs=steps, fetch=m.fetch,
                dread=m.dread, dwrite=m.dwrite, accesses=m.accesses, armw=len(m.armlog))


def report(isa, seeds=(1, 2, 3)):
    rows = []
    for k in KERNELS:
        rs = [run(isa, k, s) for s in seeds]
        bad = [r['err'] for r in rs if not r['ok']]
        r = rs[0]
        rows.append((k, r['code'], r['instrs'], r['accesses'], 'PASS' if not bad else 'FAIL: ' + bad[0]))
    return rows
