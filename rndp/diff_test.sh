#!/bin/sh
# Differential test: rndp (netlists laid out as copper on the diagonal test layout) vs the Python reference nandgen.Sim.
# usage: ./diff_test.sh [ticks] [seed]      Needs nandgen.py (Project: nandgen/nandgen.py) on PYTHONPATH.
set -e
cd "$(dirname "$0")"
TICKS=${1:-3000}; SEED=${2:-1}; OUT=${OUT:-diff_out}
cargo build --release
PYTHONPATH="${PYTHONPATH:-..}:." python3 tools/gen_vectors.py "$OUT" "$TICKS" "$SEED"
status=0
for v in "$OUT"/*.vec; do
  n=${v%.vec}
  printf '%s: ' "$(basename "$n")"
  ./target/release/rndp --netlist "$n.netlist.txt" --vectors "$v" | grep '^vectors' || status=1
done
[ $status -eq 0 ] && echo "ALL DESIGNS MATCH" || echo "MISMATCHES FOUND"
exit $status
