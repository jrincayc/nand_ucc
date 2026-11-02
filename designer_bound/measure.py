import sys, re, lzma, bz2, zlib, glob, os
R='repo/nand_ucc/'
def rd(p): return open(R+p,'rb').read()
def strip(p,b):
    t=b.decode('utf8','replace')
    out=[]
    for l in t.split('\n'):
        if p.endswith(('.py',)):
            l=re.sub(r'(?<!["\'])#.*$','',l) if not l.strip().startswith(('#!',)) else ''
        elif p.endswith(('.asm','.rs','.s')):
            l=re.sub(r'//.*$','',l)
        elif p.endswith('.hd'):
            l=re.sub(r'(//|#).*$','',l)
        l=l.rstrip()
        if l.strip(): out.append(l)
    return '\n'.join(out).encode()
tiers={
 'A builder source (R6 hack + R2c core builder)':
   ['rndp_r6/hack/'+f for f in 'bhead.asm emit3.asm gen_tmpl.py gvm2.asm huff.asm iface_gen.asm macros.asm mkb.py prog_ram_s.asm prog_s.asm ram_r6.asm shift.asm tile.asm tilecode.asm tmpl.asm'.split()]
   +['r2c/src/builder_c.asm'],
 'B hardware description (R2c core netlist)': ['r2c/hd/core_r7_ram.hd'],
 'C python image generators + asm tools':
   ['rndp_r6/'+f for f in 'plane3_gen.py tile_gen.py ramblock_gen.py iface_gen.py huff_pack.py lay2asm.py tile_enc.py tile_paths.py assemble.py'.split()]
   +['r2c/tools/asm.py','r2c/tools/hd.py','r2c/tools/hd2asm.py'],
 'D layout tool (annealer+router) source': ['c3/layout/src/main.rs','rndp_r6/layout_vp.patch'],
 'E stored layout output (r2c_vp_p5.lay)': ['rndp_r6/r2c_vp_p5.lay'],
 'F world spec': ['RNDP_SPEC.md'],
 'G simulator (rndp Rust)': ['rndp/src/'+f for f in 'lib.rs main.rs netlist.rs run.rs state.rs svg.rs world.rs'.split()],
}
def comp(b):
    return min(len(lzma.compress(b,preset=9|lzma.PRESET_EXTREME)), 10**9), len(bz2.compress(b,9))
allraw=b'';allstr=b''
res={}
for k,fs in tiers.items():
    raw=b''.join(rd(f) for f in fs); st=b''.join(strip(f,rd(f)) for f in fs)
    x,bz=comp(raw); xs,bzs=comp(st)
    res[k]=(len(raw),x,bz,len(st),xs,bzs)
    print(f'{k}\n   files={len(fs)} raw={len(raw)} xz={x} bz2={bz} | stripped raw={len(st)} xz={xs} bz2={bzs}')

print('--- joint')
def joint(keys,stripped=True):
    b=b''
    for k in keys:
        for f in tiers[k]:
            d=rd(f); b+= strip(f,d) if stripped else d
    return len(b),len(lzma.compress(b,preset=9|lzma.PRESET_EXTREME)),len(bz2.compress(b,9))
ks=list(tiers)
core=[ks[0],ks[1],ks[2],ks[3]]
for name,sel in [('A+B (builder+netlist)',[ks[0],ks[1]]),('A+B+C (+image generators)',[ks[0],ks[1],ks[2]]),('A+B+C+D (+layout tool) = designer knowledge',core),('A+B+C+D+G (+simulator as world model)',core+[ks[6]]),('everything but E',[k for k in ks if k!=ks[4]])]:
    for s in (False,True):
        r=joint(sel,s); print(f'{name:55s} stripped={s!s:5} raw={r[0]:7d} xz={r[1]:6d} bz2={r[2]:6d}')
