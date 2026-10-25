import sys
sys.path[:0]=['/home/claude/r2c/tools','/home/claude/r2c/isa','/home/claude/r2c/tests']
from run_builder import run, decode, norm
m,cpu,n,rom,dt=run(sys.argv[1],int(sys.argv[2]))
for c in decode(m.armlog): print(*c)
