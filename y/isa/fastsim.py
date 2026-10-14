"""Fast single-lane evaluation of a nandgen Compiled netlist by generating straight-line Python."""
def _compile(c, targets, name):
    base = c.n_in + c.n_dff
    need, stack = set(), list(targets)
    while stack:
        w = stack.pop()
        if w in need: continue
        need.add(w)
        if w >= base:
            a, b = c.gates[w - base]; stack += [a, b]
    lines = [f'def {name}(v):']
    for w in sorted(need):
        if w < base: lines.append(f' w{w}=v[{w}]')
        else:
            a, b = c.gates[w - base]; lines.append(f' w{w}=1^(w{a}&w{b})')
    lines.append(' return [' + ','.join(f'w{t}' for t in targets) + ']')
    ns = {}
    exec('\n'.join(lines), ns)
    return ns[name]


class Fast:
    def __init__(self, c, addr_out):
        self.c = c
        self.v = [0] * c.nwires
        self.f_addr = _compile(c, c.outs[addr_out], 'fa')
        self.dffd = c.dffd
        outs = {k: v for k, v in c.outs.items()}
        self.order = list(outs)
        flat = [w for k in self.order for w in outs[k]]
        self.f_all = _compile(c, list(self.dffd) + flat, 'fb')
        self.nd = len(self.dffd)
        self.sl, i = {}, 0
        for k in self.order:
            self.sl[k] = (i, i + len(outs[k])); i += len(outs[k])

    def setbus(self, name, val):
        for i, w in enumerate(self.c.buses[name]): self.v[w] = (val >> i) & 1

    def addr(self):
        r = self.f_addr(self.v)
        return sum(b << i for i, b in enumerate(r))

    def evaluate(self):
        self.res = self.f_all(self.v)

    def out(self, name):
        a, b = self.sl[name]
        r = self.res[self.nd + a: self.nd + b]
        return sum(x << i for i, x in enumerate(r))

    def tick(self):
        base = self.c.n_in
        for i in range(self.nd): self.v[base + i] = self.res[i]

    def dff_bus(self, idxs):
        return sum(self.v[self.c.n_in + i] << k for k, i in enumerate(idxs))


def _st(self, name):
    return sum(self.v[w] << i for i, w in enumerate(self.c.outs[name]))
Fast.st = _st
