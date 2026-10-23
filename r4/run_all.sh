#!/bin/sh
# R4 end-to-end check.  Usage: sh run_all.sh [quick|full]   (full adds the ~1 h gate-level run; needs gcc-free Rust only)
set -e; cd "$(dirname "$0")"; export ROM_BITS=16 AB=18 RAM_BITS=18
W=${WORK:-/tmp/r4work}; mkdir -p $W
(cd rvemu_rs && cargo build --release -q); (cd gatesim_rs && cargo build --release -q)
EMU=rvemu_rs/target/release/rvemu; GS=gatesim_rs/target/release/gatesim
echo "== whole program on the emulator vs Python reference (seed HD, then improved HD = fixed point)"
python3 tests/test_pipeline.py | tail -3; HDFILE=cpu_mod_improved.hd python3 tests/test_pipeline.py | tail -3
echo "== every ROM byte traced to a source line"
python3 tools/build_rom.py $W/o >/dev/null; python3 tests/trace_check.py $W/o
echo "== emulator arm log -> rndp build file"
$EMU $W/o/rom.bin --rom-bits 16 --ab 18 --ram-bytes 262144 --max 100000000 --armlog $W/arm.log --dump-ram $W/emu.ram 2>&1 | tail -1
python3 tools/armlog2build.py $W/arm.log $W/emu.build
if [ -x "${RNDP:-}" ]; then
  python3 - <<'P'
import sys; sys.path.insert(0, 'tools'); import hd as H, hd2nl, os
t, _ = hd2nl.convert(H.read(open('hd/m18/cpu_mod_improved.hd').read()), 18); open(os.environ.get('WORK', '/tmp/r4work') + '/imp.nl', 'w').write(t)
P
  $RNDP --build $W/emu.build --steps 0 --layers 2 --max-ram-addr-bits 18 --dump-pads $W/emu.pads | tail -4
  python3 tests/validate_world.py $W/imp.nl $W/emu.build $W/emu.pads
else echo "(set RNDP=/path/to/rndp to also build the world in rndp)"; fi
if [ "$1" = full ]; then
  echo "== gate-level CPU (NAND/DFF netlist) runs the whole program from reset"
  $GS hd/m18/cpu_g1.nl $W/o/rom.bin --stop-arm $(wc -l < $W/arm.log) --checkpoint $W/ck --every 100000000 --armlog $W/g.arm --dump-ram $W/g.ram
  $GS hd/m18/cpu_g1.nl $W/o/rom.bin --resume $W/ck --ticks 1000000000 --dump-ram $W/g.ram   # runs on past the last arm write to the halt loop (last checkpoint is at 900M ticks)
  python3 tools/cmp_gate.py $W/arm.log $W/g.arm $W/emu.ram $W/g.ram
fi
