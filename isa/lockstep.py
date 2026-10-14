"""Run a gate-level CPU netlist in lockstep with its behavioral model on the four kernels.
Per instruction: compare PC, A/ACC, D/... via a per-ISA `arch_state` hook; at the end compare memory,
arm log and the kernel's own result check."""
import random, sys, time
import common
from fastsim import Fast


def run_lockstep(isa, comp, arch_ref, arch_net, kernel, seed=1, max_ticks=3_000_000, verbose=False):
    rng1 = random.Random(f'{seed}-{kernel}'); rng2 = random.Random(f'{seed}-{kernel}')
    code = isa.assemble(kernel, common.P)
    mr, mn = common.Machine(), common.Machine()
    for m in (mr, mn): m.load_rom(0, code)
    common.prepare(kernel, mr, rng1)
    check = common.prepare(kernel, mn, rng2)
    ref = isa.CPU(mr)
    mn_pre = bytes(mn.ram)                       # SUBLEQ-style loaders handled by isa.CPU only
    fs = Fast(comp, 'addr')
    # reset
    fs.setbus('reset', 1); fs.setbus('rdata', 0); fs.evaluate(); fs.tick(); fs.setbus('reset', 0)
    ticks = instrs = 0
    while True:
        alive = ref.step(); instrs += 1
        # run netlist until it returns to a fetch boundary (state F0 / equivalent) after one instruction
        while True:
            a = fs.addr(); fs.setbus('rdata', mn.peek(a)); fs.evaluate()
            if fs.out('we'): mn.wr(a, fs.out('wdata'))
            fs.tick(); ticks += 1
            if fs.boundary(): break
            if ticks > max_ticks: raise RuntimeError('tick limit')
        if alive and arch_ref(ref) != arch_net(fs):
            raise AssertionError(f'{kernel} instr {instrs}: ref {arch_ref(ref)} net {arch_net(fs)}')
        if not alive: break
    err = check(mn)
    same = (mr.ram == mn.ram and mr.armlog == mn.armlog)
    return dict(kernel=kernel, ok=err is None and same, err=err, instrs=instrs, ticks=ticks,
                accesses=mr.accesses, code=len(code))


def run_image(isa, comp, arch_ref, arch_net, image, seed=0, max_instr=20000):
    """Lockstep on an arbitrary ROM image with random RAM contents."""
    rng = random.Random(seed)
    ram = bytes(rng.getrandbits(8) for _ in range(common.ARM_BASE))
    mr, mn = common.Machine(), common.Machine()
    for m in (mr, mn):
        m.ram[:] = ram; m.load_rom(0, image)
    ref = isa.CPU(mr)
    fs = Fast(comp, 'addr')
    fs.setbus('reset', 1); fs.setbus('rdata', 0); fs.evaluate(); fs.tick(); fs.setbus('reset', 0)
    instrs = ticks = 0
    while instrs < max_instr:
        alive = ref.step(); instrs += 1
        while True:
            a = fs.addr(); fs.setbus('rdata', mn.peek(a)); fs.evaluate()
            if fs.out('we'): mn.wr(a, fs.out('wdata'))
            fs.tick(); ticks += 1
            if fs.boundary(): break
            if ticks > 20 * (instrs + 10): raise RuntimeError('netlist stuck')
        if not alive: break
        if arch_ref(ref) != arch_net(fs):
            raise AssertionError(f'instr {instrs}: ref {arch_ref(ref)} net {arch_net(fs)}')
        assert mr.ram == mn.ram, f'RAM differs after instr {instrs}'
        assert mr.armlog == mn.armlog, f'armlog differs after instr {instrs}'
    return instrs, ticks
