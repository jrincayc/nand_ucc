#!/usr/bin/env python3
"""trace_check.py -- independent audit of an assembled ROM image (Y project, T2).  Does NOT import asm.py.

usage: python3 trace_check.py OUTDIR source1.asm [source2.asm ...]
Reads OUTDIR/rom.bin, rom.lst, symbols.txt and checks:
  C1 every listing byte equals the byte in rom.bin; listing entries do not overlap
  C2 every non-zero byte of rom.bin is covered by exactly one listing entry (no unexplained byte)
  C3 each entry's text is really the text of its source line (macro lines: matches the macro definition line)
  C4 each entry has a non-empty // comment
  C5 each instruction entry decodes (by this file's own decoder) to the instruction written in the source
  C6 every emitting source line of the given files appears in the listing (nothing silently skipped)
Exit status 0 only if all checks pass.  Prints counts so the reviewer sees what was covered."""
import os, re, sys

AB = int(os.environ.get('HACK_AB', 15))
ROM_BASE = 1 << (AB - 1)

# --- independent decoder tables: comp bits -> text (a=0 spelling; a=1 turns A into M) --------------------------
COMP_TXT = {0b101010: '0', 0b111111: '1', 0b111010: '-1', 0b001100: 'D', 0b110000: 'A', 0b001101: '!D',
            0b110001: '!A', 0b001111: '-D', 0b110011: '-A', 0b011111: 'D+1', 0b110111: 'A+1', 0b001110: 'D-1',
            0b110010: 'A-1', 0b000010: 'D+A', 0b010011: 'D-A', 0b000111: 'A-D', 0b000000: 'D&A', 0b010101: 'D|A'}
JUMP_TXT = ['', 'JGT', 'JEQ', 'JGE', 'JLT', 'JNE', 'JLE', 'JMP']


def decode(lo, hi):
    """bytes -> canonical text, or None if the word is not an instruction"""
    w = lo | hi << 8
    if w >> 15 == 0: return ('A', w)
    if w >> 13 == 6: return 'AP' if w & 0x1FFF == 0 else None
    if w >> 13 != 7: return None
    a, c, d, j = w >> 12 & 1, w >> 6 & 63, w >> 3 & 7, w & 7
    if c not in COMP_TXT: return None
    if a and 'A' not in COMP_TXT[c]: return None        # a=1 with a comp that ignores M: not expressible in text
    comp = COMP_TXT[c].replace('A', 'M') if a else COMP_TXT[c]
    dest = ''.join(ch for ch, bit in (('A', 4), ('M', 1), ('D', 2)) if d & bit)
    dest = ''.join(sorted(dest, key='AMD'.index))
    return (dest + '=' if dest else '') + comp + (';' + JUMP_TXT[j] if j else '')


def canon_source_c(stmt):
    s = stmt.replace(' ', '')
    for sep in '+&|':                                  # commutative spelling: M+D == D+M
        m = re.fullmatch(r'(?:(\w*=))?([AM])([+&|])D(;\w+)?', s)
        if m: s = (m.group(1) or '') + 'D' + m.group(3) + m.group(2) + (m.group(4) or ''); break
    if '=' in s:
        d, rest = s.split('=', 1)
        s = ''.join(sorted(d, key='AMD'.index)) + '=' + rest
    return s


def mini_eval(expr, syms):
    t = re.findall(r'0x[0-9a-fA-F]+|0b[01]+|\d+|[A-Za-z_.][\w.]*|[-+*(),]', expr)
    p = [0]
    def pk(): return t[p[0]] if p[0] < len(t) else None
    def tk(): p[0] += 1; return t[p[0] - 1]
    def atom():
        x = tk()
        if x == '(': v = add(); tk(); return v
        if x == '-': return -atom()
        if x in ('lo', 'hi') and pk() == '(':
            tk(); v = add(); tk(); return v & 255 if x == 'lo' else v >> 8 & 255
        if re.fullmatch(r'0x[0-9a-fA-F]+|0b[01]+|\d+', x): return int(x, 0)
        return syms[x]
    def mul():
        v = atom()
        while pk() == '*': tk(); v *= atom()
        return v
    def add():
        v = mul()
        while pk() in ('+', '-'): v = v + mul() if tk() == '+' else v - mul()
        return v
    return add()


def strip_labels(code):
    c = code.strip()
    while True:
        m = re.match(r'^[A-Za-z_.][\w.]*:\s*(.*)$', c)
        if not m: return c
        c = m.group(1)


def norm(s): return re.sub(r'\s+', ' ', s.strip())


def main(argv):
    if len(argv) < 2: print(__doc__); return 2
    out, srcs = argv[0], argv[1:]
    rom = open(os.path.join(out, 'rom.bin'), 'rb').read()
    syms = {}
    for line in open(os.path.join(out, 'symbols.txt')):
        k, v = line.split(' = '); syms[k] = int(v)
    fails = []
    def fail(msg):
        if len(fails) < 40: fails.append(msg)
    srcl = {}
    for p in srcs: srcl[p] = open(p).read().split('\n')
    # ---- parse the listing
    entries, cur = [], None
    for ln in open(os.path.join(out, 'rom.lst')):
        ln = ln.rstrip('\n')
        m = re.match(r'^([0-9A-F]{4})  ([0-9A-F ]*?)\s*\| (.*)$', ln)
        if not m: fail(f'unparsable listing line {ln!r}'); continue
        addr, hexs, rest = int(m.group(1), 16), m.group(2).split(), m.group(3)
        if rest.startswith('gap |'): cur = None; continue
        f = rest.split(' | ', 2)
        if f[0].strip() == '' and cur is not None:               # continuation of the previous entry
            cur['bytes'] += bytes(int(h, 16) for h in hexs); continue
        if len(f) < 3: fail(f'bad listing line {ln!r}'); continue
        mf = re.match(r'^(.*):(\d+)$', f[0])
        cur = dict(addr=addr, bytes=bytes(int(h, 16) for h in hexs), file=mf.group(1), line=int(mf.group(2)),
                   macro=f[1].strip(), text=f[2]); entries.append(cur)
    # ---- C1 / C2: bytes and coverage
    cov = {}
    for e in entries:
        for k, b in enumerate(e['bytes']):
            a = e['addr'] + k
            if a in cov: fail(f'C1 overlap at {a:#x}: {e["file"]}:{e["line"]} and {cov[a]}')
            cov[a] = f'{e["file"]}:{e["line"]}'
            i = a - ROM_BASE
            if i >= len(rom) or rom[i] != b: fail(f'C1 byte mismatch at {a:#x}: listing {b:02X}, rom.bin {rom[i] if i < len(rom) else "missing":}')
    unexplained = [ROM_BASE + i for i, b in enumerate(rom) if b and (ROM_BASE + i) not in cov]
    for a in unexplained[:10]: fail(f'C2 unexplained non-zero byte at {a:#x}')
    # ---- C3 / C4 / C5
    n_dec = n_cmt = 0
    called_lines = set(); listed = set()
    for e in entries:
        key = (e['file'], e['line']); listed.add(key)
        lines = srcl.get(e['file'])
        if lines is None: fail(f'C3 source file {e["file"]} not given on the command line'); continue
        src = lines[e['line'] - 1] if e['line'] <= len(lines) else ''
        if e['macro']:
            mm = re.match(r'macro (\w+) @(.*):(\d+)$', e['macro'])
            called_lines.add((mm.group(2), int(mm.group(3))))
            pat = '^' + '.+?'.join(re.escape(x) for x in re.split(r'\\[A-Za-z_@]\w*', norm(src))) + '$'
            if not re.match(pat, norm(e['text'])): fail(f'C3 {key}: listing text {e["text"]!r} does not match macro body {src!r}')
        else:
            if e['bytes'] == b'':                      # macro call line
                called_lines.add(key)
                a = norm(e['text']); b = norm(strip_labels(src.split('//')[0]) + ' // ' + src.split('//', 1)[1].strip() if '//' in src else strip_labels(src))
                pat = '^' + '.+?'.join(re.escape(x) for x in re.split(r'\\[A-Za-z_@]\w*', b)) + '$'     # a macro call inside a macro body: \arg stands for the argument
                if a != b and not ('\\' in b and re.match(pat, a)): fail(f'C3 {key}: call text {a!r} != source {b!r}')
            elif norm(e['text']) != norm(src): fail(f'C3 {key}: listing text {e["text"]!r} != source line {src!r}')
        if re.search(r'//\s*\S', e['text']): n_cmt += 1
        else: fail(f'C4 {key}: no // comment: {e["text"]!r}')
        stmt = strip_labels(e['text'].split('//')[0]).strip()
        if stmt and not stmt.startswith('.') and e['bytes']:
            d = decode(e['bytes'][0], e['bytes'][1]) if len(e['bytes']) == 2 else None
            if stmt.startswith('@'):
                try: v = mini_eval(stmt[1:], syms)
                except KeyError as ex: fail(f'C5 {key}: unknown symbol {ex}'); continue
                ok = d == ('A', v)
            elif stmt.replace(' ', '') == 'AP': ok = d == 'AP'
            else: ok = d == canon_source_c(stmt)
            if not ok: fail(f'C5 {key}: bytes {e["bytes"].hex()} decode to {d!r}, source says {stmt!r}')
            else: n_dec += 1
    # ---- C6: every emitting source line is listed
    n_src = 0
    for p, lines in srcl.items():
        inmac = False
        for n, raw in enumerate(lines, 1):
            code = strip_labels(raw.split('//')[0])
            w = code.split()
            if w and w[0] == '.macro': inmac = True; continue
            if w and w[0] == '.endm': inmac = False; continue
            if inmac or not w or w[0] in ('.org', '.equ'): continue
            n_src += 1
            if (p, n) not in listed: fail(f'C6 source line not in listing: {p}:{n}: {raw.strip()}')
    # ---- report
    total_nz = sum(1 for b in rom if b)
    print(f'rom.bin {len(rom)} bytes ({total_nz} non-zero), {len(entries)} listing entries covering {len(cov)} bytes')
    print(f'  C2 unexplained non-zero bytes: {len(unexplained)}')
    print(f'  C4 entries with comments: {n_cmt}/{len(entries)}')
    print(f'  C5 instructions re-decoded and matched: {n_dec}')
    print(f'  C6 emitting source lines: {n_src}')
    if fails:
        print('FAILED:'); [print('  ', f) for f in fails]; return 1
    print('trace_check: PASS'); return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
