#!/bin/sh
# Replicator 3 pipeline: netlist -> data -> ROM image -> checks -> seed -> simulate (second half optional: ./run_all.sh sim)
set -e; cd "$(dirname "$0")"; R=${RNDP:-/home/claude/rndp/target/release/rndp}; mkdir -p work
python3 tools/hdexport.py hd/cpu.hd
python3 tools/hd2asm.py hd/cpu.hd hd/cpu_data.asm
python3 tools/rvasm.py -o out src/builder.s hd/cpu_data.asm
python3 tests/trace_check.py out
python3 tests/run_builder.py out hd/cpu.hd
python3 tests/validate_geometry.py hd/cpu.hd 2>&1 | tail -3 || true
python3 tools/make_seed.py hd/cpu.hd out/rom.bin work
if [ "$1" = sim ]; then
  $R --rom on --ram on --layers 2 --build work/seed.build --steps 40 --save work/s1.state
  $R --world work/s1.state --build work/run.build --steps 12000000 --dump-on-en work/gen1 --save work/gen1.state
  python3 tests/compare_gen.py work/gen1.state 6200
fi
