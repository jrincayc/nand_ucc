# R3c design notes
* Builder (`src/builder_c.s`): place child ROM and ARM; sites (kind bitmap; row and column loops); RAM; PROGRAM_ROM image copy; per-sink paths (`dpath`); ports; RUN sinks; halt.
* `dpath` clobbers t0-t2, a4, a5 and RAM[0x50]; RAM[0x51] keeps the site kind across calls. It reads a segment byte, takes length (or the extension byte; 0 = return), emits VIA first when bit 6 is set, moves point B in the direction, TRACKs, returns on bit 7.
* CPU parameters for ROM_BITS=15: ROM_BASE 1<<15, ARM window at ROM_BASE-16, 16-bit address bus, 15-bit PC, ARHI data byte (1<<(RB-8))|AR[RB-1:8].
* Layout data encoding is documented in `rndp_layout/README.md`.
* Quine-check caveats: see `rndp_layout/tests/compare_gen.py` (margin and chunk merge).
