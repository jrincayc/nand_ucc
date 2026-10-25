#!/bin/bash
# plane regression: 2 strips
cd /home/claude/r6/hack
python3 mkb.py --test=prog $@ >/dev/null
sed -i 's/JNEB SV, NSTRIP, p_st/JNEB SV, 2, p_st/' t_prog.asm
HACK_AB=15 python3 /home/claude/r2c/tools/asm.py -o o_prog macros.asm ram_r6.asm t_prog.asm | tail -1
NS=2 python3 ../emit_model.py o_prog/rom.bin ref_p.build > /dev/null
python3 shiftb.py ref_p.build ref_ps.build 1990 -14
HACK_AB=15 python3 cmp4.py o_prog ref_ps.build 0 99999999 2>&1 | grep "^cmds\|^missing\|^extra" | cut -c1-300
