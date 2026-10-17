"""ctypes wrapper around libhack.so (fast Hack-vN-AB emulator)."""
import ctypes, os
HERE = os.path.dirname(os.path.abspath(__file__))
lib = ctypes.CDLL(os.path.join(HERE, 'libhack.so'))

class Cmd(ctypes.Structure):
    _fields_ = [(n, ctypes.c_int32) for n in ('cmd', 'kind', 'angle', 'ax', 'ay', 'bx', 'by')]
    def tup(self): return (self.cmd, self.kind, self.angle, self.ax, self.ay, self.bx, self.by)

lib.run.restype = ctypes.c_int
lib.run.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int64,
                    ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p]
ST = {0: 'halt', 1: 'timeout', 2: 'illegal', 3: 'badcmd', 4: 'diverged', 5: 'logfull', 6: 'badrom', 7: 'short'}

class Result:
    pass

class RefObj:
    def __init__(self, ref):
        self.n = len(ref); self.arr = (Cmd * max(1, self.n))()
        for i, t in enumerate(ref): self.arr[i] = Cmd(*t)

def run(ab, ramn, rom, max_instr=100_000_000, ram_fill=255, ref=None, rom_origin=(0, 0), want_child=True,
        trace=False, record=False, outcap=0):
    rom_bytes = 1 << (ab - 1)
    r = Result()
    child = (ctypes.c_uint8 * rom_bytes)() if want_child else None
    fetched = (ctypes.c_uint8 * rom_bytes)() if trace else None
    dread = (ctypes.c_uint8 * rom_bytes)() if trace else None
    out = (ctypes.c_int64 * 8)()
    outcmds = (Cmd * outcap)() if record else None
    if ref is not None:
        if not isinstance(ref, RefObj): ref = RefObj(ref)
        refp, nref, cmp_ = ctypes.cast(ref.arr, ctypes.c_void_p), ref.n, 1
    else:
        refp, nref, cmp_ = None, 0, 0
    def P(x): return ctypes.cast(x, ctypes.c_void_p) if x is not None else None
    st = lib.run(ab, ramn, bytes(rom), len(rom), ram_fill, max_instr, refp, nref, cmp_, rom_origin[0], rom_origin[1],
                 P(child), P(fetched), P(dread), P(outcmds), outcap, ctypes.cast(out, ctypes.c_void_p))
    r.status, r.name = st, ST[st]
    r.instr, r.nnon, r.nrom, r.div = out[0], out[1], out[2], out[3]
    r.origin = (out[4], out[5])
    r.child = bytes(child) if want_child else None
    r.fetched = bytes(fetched) if trace else None
    r.dread = bytes(dread) if trace else None
    r.cmds = [outcmds[i].tup() for i in range(r.nnon)] if record else None
    return r
