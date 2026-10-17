import collections, os
SD = '/tmp/claude-0/-home-claude/9a27d98d-c0c0-5f21-ada6-c43201a51770/scratchpad/states/states'
def rom_from_state(f, partid):
    d = {}
    for l in open(os.path.join(SD, f)):
        w = l.split()
        if w and w[0] == 'rom' and int(w[1]) == partid: d[int(w[2])] = int(w[3])
    n = max(d) + 1
    return bytes(d.get(i, 0) for i in range(n))
def X_image(): return rom_from_state('quine_gen1_start.txt', 2872)   # length 3962 (last nonzero byte)
def Y_image(g): return open(os.path.join(SD, f'improver_gen{g}_rom.bin'), 'rb').read()
