#!/usr/bin/env python3
# mkb.py -- compose builder_r6.asm from parts.  usage: mkb.py [gvm file]
import sys
gvmf=next((a for a in sys.argv[1:] if a.endswith('.asm')),'gvm2.asm')
e=open('emit3.asm').read()
def seg(a,b):
    i=e.index(a); j=e.index(b) if b else len(e); return e[i:j]
gvm=open(gvmf).read()
rest=open('prims.asm').read() if 'prims' in sys.argv else seg('emt:                         // TRACK','rdb:')
rdb_all=open(__import__('os').environ.get('R2C_SRC','/home/claude/r2c/src')+'/builder_c.asm').read()
i=rdb_all.index('rdb:'); j=rdb_all.index('\n',rdb_all.index('RET add16'))
rdbadd=rdb_all[i:j+1]
g=rdb_all.index('getlen:'); d=rdb_all.index('rdb:')
dpath=rdb_all[g:d]
dpath=dpath.replace('    SET PSEL, PD\n    CALL rdb\n    ST BYT','    CALL rds\n    ST BYT').replace('    CALL rdb                 // extended length','    CALL rds                 // extended length')
huff=open('huff.asm').read()
core_sub=rdb_all[rdb_all.index('tabpt:'):rdb_all.index('getlen:')].replace('SET PSEL, TP\n','SET PSEL, TPT\n')
core_sub=core_sub.replace('at TP\n','at TPT\n')
tilecode=open('tilecode.asm').read()
prog=open('prog_s.asm').read().replace('JNEB SV, NRUN, p_st','JNEB SV, NSTRIP, p_st')
progr=open('prog_ram_s.asm').read()
tmpl=open('tmpl.asm').read(); tile=open('tile.asm').read(); ifc=open('iface_gen.asm').read()
head=open('bhead.asm').read()
ld=open('lay_data.asm').read().split('\n')
ld_eq='\n'.join(l for l in ld if l.startswith('.equ'))+'\n'
ld_dat='\n'.join(l for l in ld if not l.startswith('.equ'))+'\n'
shiftdef=open('shift.asm').read()
core=rdb_all
cs=core.index('    // ---- every NAND / DFF site'); ce=core.index('    // ---- the RAM part')
sites=core[cs:ce]
ps=core.index('    // ---- the paths of all node pins'); pe=core.index('// ====', ps)
paths=core[ps:pe].replace('SET16 TP, lay_port_starts','SET16 TPT, lay_port_starts').replace('SET16 TP, lay_run_starts','SET16 TPT, lay_run_starts')
paths=paths.replace("halt:                        // finished: the child is built; the model's halt convention\n    GOTO halt\n",'')
NOEMIT='--noemit' in sys.argv
start='''start:
    SET AUH, 0
    SET HM, 0
    SET HN, 0
    WR16 0, CHILD_DX+ARM_X   // the child's arm
    WR16 2, ARM_Y
    WRK 8, 3
    WRK 9, ARM_ROT
    WRK 10, 0
    WRK 15, 1
    WRK 9, 0
'''+sites+'''    // ---- the ROM plane, the RAM tiles, the interface wires (glue VM bytecode)
'''+('' if NOEMIT else '''    SET16 GP, prog
    CALL gvm
    SET16 GP, rprog
    CALL gvm
    SET16 GP, iprog
    CALL gvm
''')+'    SET HM, 1\n    SET HN, 0\n'+paths+'''halt:
    GOTO halt
'''
out=(head+ld_eq+start+rdbadd+'\n'+dpath+'\n'+core_sub+'\n'+huff+'\n'+ld_dat if NOEMIT else '')
if not NOEMIT: out=head+ld_eq+open('shift.asm').read()+'\n'+start+gvm+'\n'+rest+'\n'+rdbadd+'\n'+dpath+'\n'+core_sub+'\n'+huff+'\n'+tilecode+'\n'+prog+'\n'+progr+'\n'+tmpl+'\n'+tile+'\n'+ifc+'\n'+ld_dat
open('builder_noemit.asm' if NOEMIT else 'builder_r6.asm','w').write(out)
if len(sys.argv)>2 and sys.argv[2].startswith('--test='):
    pass

import re
for a in sys.argv:
    if a.startswith('--test='):
        lab=a[7:]
        t=head+shiftdef+"start:\n    SET AUH, 0\n    SET16 GP, "+lab+"\n    CALL gvm\nhalt:\n    GOTO halt\n"+gvm+'\n'+rest+'\n'+rdbadd+'\n'+dpath+'\n'+tilecode+'\n'+prog+'\n'+progr+'\n'+tmpl+'\n'+tile+'\n'+ifc
        open('t_'+lab+'.asm','w').write(t)

if '--quick' in sys.argv:
    qs=start
    qs=qs.replace('SET ROWL, ROWS','SET ROWL, 1').replace('SET COLL, COLS','SET COLL, 2')
    i=qs.index('    // ---- ports'); j=qs.index('halt:')
    qs=qs[:i]+'''    SET HM, 0
    SET16 GP, iprog
    CALL gvm
    SET16 GP, prog
    CALL gvm
'''+qs[j:]
    # emitters in start come before paths: remove the first three gvm calls
    k=qs.index('    // ---- the ROM plane'); k2=qs.index('    SET HM, 1')
    qs=qs[:k]+qs[k2:]
    out2=head+ld_eq+open('shift.asm').read()+'\n'+qs+gvm+'\n'+rest+'\n'+rdbadd+'\n'+dpath+'\n'+core_sub+'\n'+huff+'\n'+tilecode+'\n'+prog+'\n'+progr+'\n'+tmpl+'\n'+tile+'\n'+ifc+'\n'+ld_dat
    open('builder_quick.asm','w').write(out2)
