import collections, os, emu, load
def parse(f):
    parts, wires, roms, dffs = {}, collections.Counter(), collections.defaultdict(dict), 0
    for l in open(os.path.join(load.SD, f)):
        w = l.split()
        if not w: continue
        if w[0] == 'part': parts[int(w[1])] = tuple(map(int, w[2:6]))        # kind x y angle
        elif w[0] == 'wire': wires[tuple(map(int, w[1:5]))] += 1
        elif w[0] == 'rom': roms[int(w[1])][int(w[2])] = int(w[3])
    return parts, wires, roms
def check(name, ab, ramn, image, statefile, parent_rom_id, child_rom_id, next_rom_id):
    parts, wires, roms = parse(statefile)
    parent_arm = parts[parent_rom_id + 1]; assert parent_arm[0] == 3, parent_arm
    ox, oy = parent_arm[1], parent_arm[2]
    r = emu.run(ab, ramn, image, max_instr=200_000_000, record=True, outcap=5_000_000)
    print(f'[{name}] emulator: {r.name}, {r.instr} instr, {r.nnon} cmds, {r.nrom} rom cmds; parent arm at ({ox},{oy})')
    exp_parts = collections.Counter((c[1], ox + c[3], oy + c[4], c[2]) for c in r.cmds if c[0] == 1)
    st_parts = collections.Counter(v for i, v in parts.items() if child_rom_id <= i < next_rom_id)
    print('  placements: expected', sum(exp_parts.values()), 'state child parts', sum(st_parts.values()), ' equal multiset:', exp_parts == st_parts)
    if exp_parts != st_parts:
        print('   missing', list((exp_parts - st_parts).items())[:3], 'extra', list((st_parts - exp_parts).items())[:3])
    exp_w = collections.Counter((ox + c[3], oy + c[4], ox + c[5], oy + c[6]) for c in r.cmds if c[0] == 2)
    missing = exp_w - wires
    print('  wires: expected', sum(exp_w.values()), 'present in state (as multiset):', sum((exp_w & wires).values()), 'missing', sum(missing.values()))
    child_rom = bytes(roms[child_rom_id].get(i, 0) for i in range(1 << (ab - 1)))
    print('  child ROM from emulator == child ROM in state:', child_rom == r.child, ' (state programmed bytes', len(roms[child_rom_id]), ')')
    return r
X = load.X_image()
check('X gen1->gen2', 13, 32, X, 'quine_gen2_built_tick8.0M.txt', 2872, 5732, 8592) if False else None
parts, wires, roms = parse('quine_gen3_built_tick16.4M.txt')
print('X rom ids', sorted(roms), ' arms', {i: v for i, v in parts.items() if v[0] == 3})
check('X gen1->gen2', 13, 32, X, 'quine_gen3_built_tick16.4M.txt', 2872, 5732, 8592)
check('X gen2->gen3', 13, 32, X, 'quine_gen3_built_tick16.4M.txt', 5732, 8592, 11452)
check('Y gen1->gen2', 15, 256, load.Y_image(1), 'improver_gen3_built_tick200M.txt', 17613, 17615, 34270)
check('Y gen2->gen3', 15, 256, load.Y_image(2), 'improver_gen3_built_tick200M.txt', 17615, 34270, 51000) 
