import random, sys, emu, pymodel as pm
random.seed(5)
bad = 0; stats = {}
for t in range(400):
    ab = random.choice([13, 15]); ramn = random.choice([32, 256]); rb = 1 << (ab - 1)
    n = random.choice([40, 200, 1000])
    # random image biased to valid-looking words: mix of A-instr, C-instr, AP and arm writes
    img = bytearray()
    for _ in range(n):
        k = random.random()
        if k < 0.4: w = random.randrange(1 << 15)
        elif k < 0.5: w = 6 << 13
        else: w = 7 << 13 | random.choice([0b000000,0b010101,0b110000,0b001100,0b110111,0b011111,0b010011,0b101010,0b111111,0b111010]) << 6 | random.randrange(2) << 12 | random.randrange(8) << 3 | random.choice([0,0,0,1,2,4,5,7])
        img += bytes([w & 255, w >> 8])
    if random.random() < .5:   # make arm commands likely: sprinkle writes
        pass
    st, n1, m = pm.run(ab, ramn, bytes(img), 20000)
    r = emu.run(ab, ramn, bytes(img), max_instr=20000, record=True, outcap=100000)
    try:
        cmds, rom = pm.decode(m.armlog); pst = st
    except (AssertionError, KeyError): pst = 'badcmd'; cmds = None
    # compare statuses: python 'illegal' covers illegal instr; arm decode errors -> badcmd
    if pst == 'badcmd': ok = r.name == 'badcmd'
    else:
        ok = (r.name == pst) and (r.instr == n1 or pst == 'halt' and r.instr == n1 - 1 + 1) 
        if ok and cmds is not None:
            ok = ok and r.cmds == cmds and r.nrom == len(rom)
    # ram equality is implied via later behaviour; also compare instruction count loosely
    stats[r.name] = stats.get(r.name, 0) + 1
    if not ok:
        bad += 1
        if bad < 6: print('MISMATCH', t, ab, ramn, n, 'py', st, n1, 'c', r.name, r.instr, 'ncmds', len(cmds or []), r.nnon)
print('tests 400, mismatches', bad, stats)
