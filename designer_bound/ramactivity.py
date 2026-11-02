import os, sys, time, json
R='/tmp/claude-0/-home-claude/30394c41-9cfc-5956-88ca-43f1ddd2587b/scratchpad/repo/nand_ucc/r2c'
os.environ['HACK_AB']='15'
sys.path[:0]=[R+'/tools',R+'/isa',R+'/tests']
import common, isahack, machine_model
class M(machine_model.MR):
    def __init__(s,n):
        super().__init__(n); s.tog=[0]*n; s.vals=[set([0]) for _ in range(n)]; s.writes=[0]*n; s.reads=[0]*n
    def wr(s,a,v):
        a&=common.AMASK
        if a<s.ramn:
            old=s.ram[a]; s.tog[a]|=(old^(v&255)); s.vals[a].add(v&255); s.writes[a]+=1
        super().wr(a,v)
    def rd(s,a,*k):
        a&=common.AMASK
        if a<s.ramn: s.reads[a]+=1
        return super().rd(a,*k)
rom=open(R+'/outc/rom.bin','rb').read()
m=M(128); m.load_rom(0,rom); cpu=isahack.CPU(m)
t0=time.time(); n=0
while True:
    n+=1
    if not cpu.step(): break
    if n%1000000==0: print(f'{n/1e6:.0f}M {time.time()-t0:.0f}s',flush=True)
tb=sum(bin(t).count('1') for t in m.tog)
res=dict(instr=n, bytes_written=sum(1 for w in m.writes if w), bytes_read=sum(1 for r in m.reads if r),
         toggle_bits=tb, bytes_toggled=sum(1 for t in m.tog if t), max_distinct=max(len(v) for v in m.vals),
         distinct_total=sum(len(v) for v in m.vals), tog=m.tog)
json.dump(res,open('out/ramactivity.json','w'))
print({k:v for k,v in res.items() if k!='tog'})
