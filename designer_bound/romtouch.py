import os, sys, time, json
R='/tmp/claude-0/-home-claude/30394c41-9cfc-5956-88ca-43f1ddd2587b/scratchpad/repo/nand_ucc/r2c'
os.environ['HACK_AB']='15'
sys.path[:0]=[R+'/tools',R+'/isa',R+'/tests']
import common, isahack, machine_model
print('ROM_BASE?', [k for k in dir(common) if 'ROM' in k.upper() or 'BASE' in k.upper()], flush=True)
class M(machine_model.MR):
    def __init__(s,n):
        super().__init__(n); s.f=set(); s.d=set()
    def rd(s,a,*k):
        a&=common.AMASK
        if a>=16384 and a<32768:
            (s.f if (k and k[0]=='f') else s.d).add(a-16384)
        return super().rd(a,*k)
rom=open(R+'/outc/rom.bin','rb').read()
m=M(128); m.load_rom(0,rom); cpu=isahack.CPU(m)
n=0
while True:
    n+=1
    if not cpu.step(): break
nz=[i for i,b in enumerate(rom) if b]
touched=m.f|m.d
print(dict(instr=n, image=len(rom), nonzero=len(nz), fetched=len(m.f), read=len(m.d), both=len(m.f&m.d), untouched_nonzero=len([i for i in nz if i not in touched]), untouched_all=len(rom)-len([i for i in range(len(rom)) if i in touched])))
