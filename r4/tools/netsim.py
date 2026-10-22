#!/usr/bin/env python3
"""netsim.py -- compiles the CPU netlist to a C simulator and runs it against a ROM image.
Semantics = RNDP tick: settle combinational logic (ROM/RAM reads are combinational), then DFFs latch D, RAM writes, arm writes are logged.
The C program prints, per tick, the state vector: upc k ir0 ir1 ir2 ir3 ar A R C Z SA SB (hex), then at the end the RAM and the arm log."""
import os, subprocess, sys, tempfile
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
import cpu_gen


def flat(x):
    for y in x:
        if isinstance(y, list): yield from flat(y)
        else: yield y


def gen_c(net, ports, state):
    roots = list(ports.values()) + list(flat(v if isinstance(v, list) else [v] for v in state.values()))
    used = sorted(net.used_nodes(roots))
    idmap = {n: i for i, n in enumerate(used)}
    def ref(s): return '0' if s == 0 else '1' if s == 1 else f'v[{idmap[s]}]'
    L = ['#include <stdio.h>', '#include <stdlib.h>', '#include <string.h>', 'typedef unsigned char u8;', f'static u8 v[{len(used) + 1}];']
    nands = [n for n in used if net.kind[n][0] == 'nand']
    dffs = [n for n in used if net.kind[n][0] == 'dff']
    # topological order of nands
    order = []; seen = set()
    def visit(n):
        stack = [(n, 0)]
        while stack:
            x, st = stack.pop()
            if x in seen and st == 0: continue
            k = net.kind[x]
            if k[0] != 'nand': continue
            if st == 0:
                seen.add(x); stack.append((x, 1))
                for s in k[1:]:
                    if s > 1 and s not in seen: stack.append((s, 0))
            else: order.append(x)
    for n in nands: visit(n)
    L.append('static void eval(void){')
    for n in order:
        k = net.kind[n]; L.append(f'v[{idmap[n]}]=!({ref(k[1])}&{ref(k[2])});')
    L.append('}')
    L.append('static void latch(void){ u8 t[%d];' % max(1, len(dffs)))
    for i, n in enumerate(dffs): L.append(f't[{i}]={ref(net.kind[n][1])};')
    for i, n in enumerate(dffs): L.append(f'v[{idmap[n]}]=t[{i}];')
    L.append('}')
    def bus(sigs): return '|'.join(f'({ref(s)}<<{i})' for i, s in enumerate(sigs)) or '0'
    L.append(f'static unsigned ar_(void){{ return {bus([ports[f"rom_addr{i}"] for i in range(int(os.environ.get('ROM_BITS', '14')))])}; }}')
    L.append(f'static unsigned ra_(void){{ return {bus([ports[f"ram_addr{i}"] for i in range(int(os.environ.get('RAM_BITS', '8')))])}; }}')
    L.append(f'static unsigned rd_(void){{ return {bus([ports[f"ram_din{i}"] for i in range(8)])}; }}')
    L.append(f'static unsigned aa_(void){{ return {bus([ports[f"arm_addr{i}"] for i in range(4)])}; }}')
    L.append(f'static int we_(void){{ return {ref(ports["ram_we"])}; }}')
    L.append(f'static int ae_(void){{ return {ref(ports["arm_en"])}; }}')
    def sb(sigs): return bus(sigs)
    L.append('static void setin(unsigned rom, unsigned ram){')
    for i in range(8):
        L.append(f'v[{idmap[net.inputs[f"rom{i}"]]}]=(rom>>{i})&1; v[{idmap[net.inputs[f"ramrd{i}"]]}]=(ram>>{i})&1;')
    L.append(f'v[{idmap[net.inputs["run"]]}]=1; }}')
    st = state
    L.append('static void dump(void){ printf("%%02x %%x %%02x%%02x%%02x%%02x %%04x %%02x %%02x %%x%%x%%x%%x\\n", %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s); }' % (
        bus(st['upc']), bus(st['k']), bus(st['ir'][0]), bus(st['ir'][1]), bus(st['ir'][2]), bus(st['ir'][3]), bus(st['ar']), bus(st['A']), bus(st['R']), ref(st['C']), ref(st['Z']), ref(st['SA']), ref(st['SB'])))
    L.append(r'''
int main(int argc, char **argv){
  static unsigned char rom[1<<ROMB]; static unsigned char ram[1<<RAB]; memset(rom,0,sizeof rom); memset(ram,0,sizeof ram);
  FILE *f=fopen(argv[1],"rb"); size_t n=fread(rom,1,sizeof rom,f); fclose(f); (void)n;
  long nt=atol(argv[2]); int trace=argc>3 && argv[3][0]=='1';
  static unsigned armlog[1<<20]; int na=0;
  memset(v,0,sizeof v);
  for(long t=0;t<nt;t++){
    setin(0,0); eval(); setin(rom[ar_()&((1<<ROMB)-1)], ram[ra_()&((1<<RAB)-1)]); eval();
    if(we_()) ram[ra_()&((1<<RAB)-1)]=rd_();
    if(ae_()){ armlog[na++]=(aa_()<<8)|rd_(); }
    latch();
    if(trace) dump();
  }
  if(!trace) dump();
  printf("RAM "); for(int i=0;i<(1<<RAB);i++) printf("%02x",ram[i]); printf("\n");
  printf("ARM %d", na); for(int i=0;i<na;i++) printf(" %x:%02x",armlog[i]>>8,armlog[i]&255); printf("\n");
  return 0; }
''')
    return '\n'.join(L), len(order), len(dffs)


def compile_sim(outdir):
    net, ports, state = cpu_gen.build()
    if os.environ.get('CPU_SEED') == 'mod':      # textbook module seed (modnet.py), flattened with the library
        import modnet, seed_stats
        m = modnet.ModNet(); mn, mpo, ms = cpu_gen.build(net=m)
        net, ports, state = m.flatten(seed_stats.roots_of(mpo, ms), mpo, ms)
    if os.environ.get('CPU_HD'):                  # simulate any HD file (module seed, improved seed, ...)
        import hd as hdlib, hdflat
        net, ports = hdflat.flatten(hdlib.read(open(os.environ['CPU_HD']).read())); state = hdflat.state_of(net)
    src, ng, nf = gen_c(net, ports, state)
    os.makedirs(outdir, exist_ok=True)
    cpath = os.path.join(outdir, 'sim.c'); open(cpath, 'w').write(src)
    exe = os.path.join(outdir, 'sim')
    subprocess.run(['gcc', '-O1', f"-DROMB={os.environ.get('ROM_BITS', '14')}", f"-DRAB={os.environ.get('RAM_BITS', '8')}", '-o', exe, cpath], check=True)
    return exe, (net, ports, state)


if __name__ == '__main__':
    exe, _ = compile_sim(sys.argv[1] if len(sys.argv) > 1 else '/tmp/r3sim')
    print('compiled', exe)
