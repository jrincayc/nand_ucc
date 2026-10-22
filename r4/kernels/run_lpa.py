import os, sys, struct, subprocess, collections
os.environ['ROM_BITS']='17'
sys.path[:0]=['/home/claude/r3c/tools','/home/claude/r4/tools']
import rvasm, lay, lpa_order
nl=lay.read_nl('/home/claude/r4/hd/cpu_g1.nl'); adj=lpa_order.graph(nl,anchor=True); NV=len(nl.nodes)+1
assert NV==3770
off=[0]; nbr=[]; wt=[]
for v in range(NV):
    for u,w in adj[v].items(): nbr.append(u); wt.append(max(1,round(w*60)))
    off.append(len(nbr))
ram=bytearray(0x1FFF0)
def put16(base,arr):
    for i,x in enumerate(arr): struct.pack_into('<H',ram,base+2*i,x)
put16(0x1000,off); put16(0xB000,nbr); ram[0x14000:0x14000+len(wt)]=bytes(wt); put16(0x3000,list(range(NV))); put16(0x7000,[1]*NV)
# python model of the kernel
lab=list(range(NV)); size=[1]*NV; CAP=480
for sw in range(4):
    for v in range(NV):
        votes=collections.OrderedDict()
        for i in range(off[v],off[v+1]): votes[lab[nbr[i]]]=votes.get(lab[nbr[i]],0)+wt[i]
        if not votes: continue
        best=max(votes.values()); cur=lab[v]
        if votes.get(cur,0)>=best: continue
        new=next((l for l,x in votes.items() if x==best and size[l]<CAP),None)
        if new is None: continue
        size[cur]-=1; size[new]+=1; lab[v]=new
open('/tmp/lpa_ram.bin','wb').write(ram)
a,img=rvasm.assemble(['/home/claude/r4/kernels/lpa_sweep.s'],'/tmp/lpak'); open('/tmp/lpa_rom.bin','wb').write(bytes(img))
r=subprocess.run(['/home/claude/r4/rvemu_rs/target/release/rvemu','/tmp/lpa_rom.bin','--rom-bits','17','--ram-bytes',str(0x1FFF0),'--load-ram','/tmp/lpa_ram.bin','--dump-ram','/tmp/lpa_out.bin','--max','400000000'],capture_output=True,text=True)
print(r.stderr.strip(), 'ROM bytes',len(img))
out=open('/tmp/lpa_out.bin','rb').read(); got=list(struct.unpack_from('<%dH'%NV,out,0x3000))
print('labels match python model:',got==lab,'; distinct labels',len(set(got)))
