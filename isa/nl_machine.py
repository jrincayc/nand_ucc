"""Hack-vN machine: CPU + RAM + address decode as one nandgen netlist; ROM and ARM are RNDW parts
outside the netlist.  Netlist inputs: romdata[8] (from the ROM part's DATA pins), run (tie-high NAND).
Netlist outputs: rom_addr[a], arm_addr[4], arm_en, wdata[8] (+ debug buses).
Memory map: RAM 0x0000 .. 2**ram_abits-1, ARM window 0x0FF0-0x0FFF, ROM 0x1000-0x1FFF, anything else reads 0."""
from nandgen import *
from nl_hackvn import hackvn_core


def build_machine(level=2, ram_abits=10, rom_abits=12):
    n = Net(level)
    romdata = n.bus_in('romdata', 8)
    run = n.input('run')
    # run must feed exactly one gate (both of its pins): the child is released by the very last wire.
    # _raw avoids nandgen's double-inverter elimination, which would otherwise fan `run` out to every
    # place that uses not(reset).
    reset = n._raw(run, run)
    words = 1 << ram_abits
    h = ram_abits // 2
    q = [n.dff_bus(8) for _ in range(words)]
    box = {}

    def get_rdata(addr):
        with n.scope('decode'):
            hiz = ONE
            for b in addr[ram_abits:13]:
                hiz = n.and_(hiz, n.not_(b))
            box['ram_sel'] = hiz
            arm = n.not_(addr[12])
            for b in addr[4:12]:
                arm = n.and_(arm, b)
            box['arm_sel'] = arm
        with n.scope('readmux'):
            ram_rd = []
            for j in range(8):
                layer = [q[w][j] for w in range(words)]
                for k in range(ram_abits):
                    layer = [n.mux(layer[i], layer[i + 1], addr[k]) for i in range(0, len(layer), 2)]
                ram_rd.append(layer[0])
        with n.scope('decode'):
            return [ao_(n, box['ram_sel'], ram_rd[j], addr[12], romdata[j]) for j in range(8)]

    s = hackvn_core(n, reset, get_rdata)
    addr, we = s['addr'], s['we']
    with n.scope('decode'):
        we_ram = n.and_(we, box['ram_sel'])
        arm_en = n.and_(we, box['arm_sel'])
        lo = onehot(n, addr[:h])
        hi = onehot(n, addr[h:ram_abits], base=we_ram)
        wen = [n.and_(hi[w >> h], lo[w & ((1 << h) - 1)]) for w in range(words)]
    with n.scope('cells'):
        for w in range(words):
            register(n, q[w], wen[w], s['wdata'])
    outs = {'rom_addr': addr[:rom_abits], 'arm_addr': addr[:4], 'arm_en': [arm_en], 'wdata': s['wdata'],
            'addr': addr, 'we': [we], 'pc': s['pc'], 'a': s['a'], 'd': s['d'], 'st': s['st'], 'ir': s['ir'],
            'mem': [b for w in range(words) for b in q[w]]}
    c = n.finalize(outs)
    c.words = words
    return c


def ao_(n, s1, b1, s2, b2):
    return n.nand(n.nand(s1, b1), n.nand(s2, b2))


if __name__ == '__main__':
    import sys
    c = build_machine(2, int(sys.argv[1]) if len(sys.argv) > 1 else 10)
    g, d = c.by_scope()
    print('NAND', len(c.gates), 'DFF', c.n_dff, g)
