#!/usr/bin/env python3
"""emit_model.py ROM OUT.build -- reference model of the Hack emitter's plane part: template interpreter (origin + signed 8-bit offsets)
for inverter / cell / gadget / pass, inline code for lines and snake connectors.  Output must equal plane3_gen.py as a command set."""
import sys, collections
rom, out = sys.argv[1], sys.argv[2]
R = C = 128; data = list(open(rom,'rb').read()[:R*C]); data += [0]*(R*C-len(data))
# item: ('P',kind,dx,dy) place | ('T',L,dx0,dy0,dx1,dy1) track | ('V',dx,dy) via ; all offsets signed 8 bit
INV  = [('P',0,1,0),('V',0,1),('T',0,0,1,0,0),('T',0,0,0,1,0),('T',0,0,1,1,1)]           # origin (x-1, INVY)
CELL = [('P',0,0,0),('T',0,0,-1,0,0),('V',-1,1),('T',0,-1,1,0,1),('T',0,1,0,3,0),('V',3,0),('T',1,3,0,3,45)]   # origin (cx,b); 45 = yj(7)-b+1
GAD  = [('T',0,-1,0,0,0),('T',0,-1,0,-1,1),('T',0,-1,1,0,1),('P',0,0,0),('T',0,1,0,5,0),('V',3,1),('T',0,3,1,5,1),('P',0,5,0),('T',0,6,0,7,0)]  # origin (cx,y)
PASS = [('T',0,-1,0,7,0)]
B = []
def run(t, ox, oy):
    for it in t:
        if it[0]=='P': B.append(f'place {it[1]} {ox+it[2]} {oy+it[3]} 0 0')
        elif it[0]=='V': B.append(f'via {ox+it[1]} {oy+it[2]}')
        else: B.append(f'track {it[1]} {ox+it[2]} {oy+it[3]} {ox+it[4]} {oy+it[5]}')
def trk(L,a,b,c,d):
    if (a,b)!=(c,d): B.append(f'track {L} {a} {b} {c} {d}')
def via(x,y): B.append(f'via {x} {y}')
NB=NBH=7; XL0=2; XB=24; XG=XB+4*14+4; X0=XG+8*6+6; XEND=X0+C*8+2; INVY=2; PY0=INVY+4+8*C+8; SH=53
base=lambda s:PY0+3+s*SH; yj=lambda s,j:base(s)+9+5*j
for i in range(14): run(INV, XB+4*i-1, INVY)
for i in range(14): x=XB+4*i; trk(1,x-1,INVY+1,x-1,base(R-1)+8); trk(1,x+1,INVY,x+1,base(R-1)+8)
# lines (inline in asm): same literal logic
def line(y,v,i0,n):
    lit=lambda k:XB+4*(i0+k)+(1 if not (v>>k)&1 else -1)
    for k in range(n-1):
        Xk=XG+8*k
        if k==0:
            via(lit(0),y); trk(0,lit(0),y,Xk,y); via(lit(1),y+2); trk(0,lit(1),y+2,Xk,y+2); trk(0,Xk,y+2,Xk,y+1)
        else:
            trk(0,Xk-3,y,Xk,y); via(lit(k+1),y+2+k); trk(0,lit(k+1),y+2+k,Xk,y+2+k); trk(0,Xk,y+2+k,Xk,y+1)
        B.append(f'place 0 {Xk} {y} 0 0'); trk(0,Xk+1,y,Xk+4,y); trk(0,Xk+3,y,Xk+3,y+1); trk(0,Xk+3,y+1,Xk+4,y+1); B.append(f'place 0 {Xk+4} {y} 0 0')
    return XG+8*(n-2)+5
for l in range(C):
    y=INVY+4+8*l; xo=line(y,l,0,NB); cxl=X0+l*8-1; trk(0,xo,y,cxl,y); via(cxl,y); trk(1,cxl,y,cxl,base(R-1)+1)
import os
NS=int(os.environ.get('NS',R))
for s in range(NS):
    b=base(s); xo=line(b-1,s,NB,NBH); trk(0,xo,b-1,X0+(C-1)*8,b-1)
    for l in range(C):
        v=data[s*C+l]; cx=X0+l*8
        if v: run(CELL,cx,b)
        for j in range(8): run(GAD if (v>>j)&1 else PASS, cx, yj(s,j))
    for j in range(8):
        y=yj(s,j); XE=XEND+2*j; XL=XL0+2*j
        trk(0,X0+(C-1)*8+7,y,XE,y)
        if s<R-1:
            n=yj(s+1,j); via(XE,y); trk(1,XE,y,XE,y+3); via(XE,y+3); trk(0,XE,y+3,XL,y+3); via(XL,y+3); trk(1,XL,y+3,XL,n); via(XL,n); trk(0,XL,n,X0-1,n)
open(out,'w').write('\n'.join(B)+'\n')
ref=open(sys.argv[3]).read().split('\n') if len(sys.argv)>3 else None
if ref:
    def nm(l):
        t=l.split()
        if t[0]=='track' and (int(t[2]),int(t[3]))>(int(t[4]),int(t[5])): t=[t[0],t[1],t[4],t[5],t[2],t[3]]
        return tuple(t)
    a=collections.Counter(map(nm,[l for l in B if l])); b=collections.Counter(map(nm,[l for l in ref if l]))
    print('commands',len(B),'missing',sum((b-a).values()),'extra',sum((a-b).values()))
