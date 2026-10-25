#!/usr/bin/env python3
"""gen_tmpl.py -> tmpl.asm : template data (op|layer<<2, then dx16 dy8 per point).  Must mirror emit_model.py templates."""
XEND=1164; X0=138; LASTX7=X0+127*8+7; STRIPH=53
T={
'inv': [('P',0,1,0),('V',0,1),('T',0,0,1,0,0),('T',0,0,0,1,0),('T',0,0,1,1,1)],
'cell':[('P',0,0,0),('T',0,0,-1,0,0),('V',-1,1),('T',0,-1,1,0,1),('T',0,1,0,3,0),('V',3,0),('T',1,3,0,3,45)],
'gad': [('T',0,-1,0,0,0),('T',0,-1,0,-1,1),('T',0,-1,1,0,1),('P',0,0,0),('T',0,1,0,5,0),('V',3,1),('T',0,3,1,5,1),('P',0,5,0),('T',0,6,0,7,0)],
'pass':[('T',0,-1,0,7,0)],
'conn':[('V',XEND,0),('T',1,XEND,0,XEND,3),('V',XEND,3),('T',0,XEND,3,2,3),('V',2,3),('T',1,2,3,2,STRIPH),('V',2,STRIPH)],
'stg0':[('P',0,0,0),('T',0,1,0,4,0),('T',0,3,0,3,1),('T',0,3,1,4,1),('P',0,4,0)],
'stg1':[('T',0,-3,0,0,0),('P',0,0,0),('T',0,1,0,4,0),('T',0,3,0,3,1),('T',0,3,1,4,1),('P',0,4,0)],
}

import json
TJ=json.load(open('../out/tile.json')); PO=TJ['ports']; H=TJ['H']; TH=H+1
XBUS=92; TX0=116; XGR=36
rt=[]
for idx in range(9):
    px,py=PO['WE' if idx==0 else 'DIN%d'%(idx-1)]; dxb=XBUS+2*idx-TX0
    rt+= [('V',dxb,py),('T',0,dxb,py,px,py)]
T['rtap']=rt
T['rlink']=[('T',0,PO['CO%d'%b][0],H-1,PO['CO%d'%b][0],TH) for b in range(8)]
T['rsel']=[('T',0,XGR+45-TX0,0,PO['SEL'][0],0)]
T['rdout']=[]
for b in range(8):
    cx=PO['CO%d'%b][0]; T['rdout']+= [('P',0,cx,H+3),('T',0,cx,H-1,cx,H+4)]
T['rtie']=[('P',0,2,-6)]+[('T',0,PO['CI%d'%b][0],-4,PO['CI%d'%b][0],0) for b in range(8)]+[('T',0,3,-6,3,-4),('T',0,3,-4,PO['CI7'][0],-4)]

def w(x): return f'{x & 255},{(x >> 8) & 255}'
out=[]
for name,items in T.items():
    out.append(f't_{name}:')
    for it in items:
        if it[0]=='P': out.append(f'    .byte 1,{it[1]},{w(it[2])},{it[3]&255}')
        elif it[0]=='V': out.append(f'    .byte 3,{w(it[1])},{it[2]&255}')
        else: out.append(f'    .byte {2|(it[1]<<2)},{w(it[2])},{it[3]&255},{w(it[4])},{it[5]&255}')
    out.append('    .byte 0')
open('tmpl.asm','w').write('\n'.join(out)+'\n')
print(sum(1 for l in out if l.strip().startswith('.byte')),'items')
