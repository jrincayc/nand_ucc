#!/bin/bash
# build_r6.sh -- rebuild R6 (image + whole board) from the stored inputs, check the fixed point, optionally verify.
# Run from nandgen/rndp_r6.  Every path is overridable from the environment.
#   ./build_r6.sh [WORK]          build (default WORK=./work_r6)
#   CHECK=1  ./build_r6.sh        also load the board in rndp and check every pin (chk_full.py, several minutes)
#   REGEN_TILE=1 ./build_r6.sh    also regenerate the RAM tile with mrouter (needs MROUTER)
#   MODEL=1  ./build_r6.sh        also run the Hack-model emitter check (754 M instructions, hours)
set -euo pipefail
R6=$(cd "$(dirname "$0")" && pwd)
ROOT=${ROOT:-$(cd "$R6/.." && pwd)}                       # directory that holds rndp_r6, rndp_layout, y, rndp_r2c, ...
LAYTOOLS=${LAYTOOLS:-$ROOT/rndp_layout/tools}             # lay.py
ASM=${ASM:-$ROOT/y/tools/asm.py}                          # Hack-vN-AB assembler
R2C_SRC=${R2C_SRC:-$ROOT/rndp_r2c/src}                    # builder_c.asm (mkb.py takes the core path code from it)
NL=${NL:-$R6/data/work_r2.nl}                        # netlist of the R2c core (copy of rndp_layout/data/work_r2.nl)
RNDP=${RNDP:-$ROOT/rndp/target/release/rndp}              # cargo build --release in rndp/
MROUTER=${MROUTER:-$ROOT/rndp_r5/e4/mrouter/mrouter}      # only for REGEN_TILE=1
CHILD_DX=${CHILD_DX:-1730}
OFS=${OFS:-260,40}
IFACE_O=${IFACE_O:-1698 -14}       # child board origin in the arm frame used by the interface bytecode (found by experiment, see R6_DESIGN)
MAXIT=${MAXIT:-4}
W=${1:-$R6/work_r6}; mkdir -p "$W"; W=$(cd "$W" && pwd)
export HACK_AB=15 LAYTOOLS RNDP MROUTER R2C_SRC OFS
step() { echo; echo "=== $*"; }
LAY=$R6/r2c_vp_p5.lay

step "1. core layout -> ROM data (lay2asm --hack, Huffman pack)"
rm -rf "$W/hack"; cp -r "$R6/hack" "$W/hack"; cd "$W/hack"
CHILD_DX=$CHILD_DX PYTHONPATH=$LAYTOOLS python3 "$R6/lay2asm.py" "$LAY" "$NL" lay_data_raw.asm --hack
python3 "$R6/huff_pack.py" lay_data_raw.asm lay_data.asm
cmp lay_data.asm "$R6/hack/lay_data.asm" && echo "lay_data.asm identical to the stored one"

step "2. RAM tile data"
if [ "${REGEN_TILE:-0}" = 1 ]; then
  python3 "$R6/tile_gen.py" "$W/tile.json" 6 | tail -1
  cmp "$W/tile.json" "$R6/data/tile.json" && echo "tile.json identical to data/tile.json"
else
  cp "$R6/data/tile.json" "$W/tile.json"
fi
python3 "$R6/tile_paths.py" "$W/tile.json" "$W/tile_paths.json"
python3 "$R6/tile_enc.py" "$W/tile.json" tile.asm
cmp tile.asm "$R6/hack/tile.asm" && echo "tile.asm identical to the stored one"

step "3. templates (read tile.json for the port offsets)"
TILE_JSON=$W/tile.json python3 gen_tmpl.py > /dev/null; cmp tmpl.asm "$R6/hack/tmpl.asm" && echo "tmpl.asm identical"

step "4. fixed point: image -> plane/RAM/board -> interface wires -> image"
for i in $(seq 1 "$MAXIT"); do
  echo "--- iteration $i"
  python3 mkb.py
  python3 "$ASM" -o "$W/out" macros.asm ram_r6.asm builder_r6.asm | tail -1
  ROM=$W/out/rom.bin; echo "image bytes: $(stat -c %s "$ROM")"
  [ "$(stat -c %s "$ROM")" -le 16384 ] || { echo "image exceeds the 16 KiB ROM window"; exit 1; }
  python3 "$R6/plane3_gen.py" "$ROM" 0 "$W/plane.build" | tail -2
  python3 "$R6/ramblock_gen.py" "$W/tile.json" "$W/ram.build" | tail -2
  python3 "$R6/assemble.py" "$LAY" "$NL" "$W/plane.build" "$W/ram.build" "$W/full" | tail -4
  python3 "$R6/iface_gen.py" "$W/full.wires.pkl" iface_new.asm $IFACE_O
  if cmp -s iface_new.asm iface_gen.asm; then echo "FIXED POINT reached after $i iteration(s)"; break; fi
  echo "interface data changed -> rebuild"; cp iface_new.asm iface_gen.asm
  [ "$i" = "$MAXIT" ] && { echo "no fixed point within $MAXIT iterations"; exit 1; }
done
echo "image: $W/out/rom.bin ($(stat -c %s "$W/out/rom.bin") B); board: $W/full.build"

if [ "${CHECK:-0}" = 1 ]; then
  step "5. board in rndp: every pin on its logical net"
  python3 "$R6/chk_full.py" "$W/full" ${OFS//,/ }
fi
if [ "${MODEL:-0}" = 1 ]; then
  step "6. Hack model runs the emitter; compare with the generator's commands (very slow)"
  python3 "$R6/emit_model.py" "$W/out/rom.bin" "$W/ref.build" > /dev/null
  python3 "$R6/hack/run_emit.py" "$W/out" "$W/ref.build"
fi
echo; echo "R6 build OK"
