| builder routine | bytes | what it does | instructions gen 1->2 | gen 2->3 |
|---|---:|---|---:|---:|
| `start` | 416 | reset code: init, chain record, place ROM + arm | 0.00 M | 0.00 M |
| `group` | 562 | phase/group loop and the instance walk (incl. skip) | 0.70 M | 0.70 M |
| `phase_done` | 160 | tie node, start of the RAM tile code | 0.00 M | 0.00 M |
| `tile_loop` | 220 | RAM tile loop | 0.06 M | 0.06 M |
| `tiles_done` | 80 | end of tiles, phase switch | 0.00 M | 0.00 M |
| `rom_loop` | 158 | bulk ROM copy (skips the record area) | 0.70 M | 0.70 M |
| `pass2_tail` | 352 | ports, EN and RUN wires, halt | 0.00 M | 0.00 M |
| `rdb` | 40 | read one ROM/RAM byte through a pointer | 3.82 M | 3.82 M |
| `add16` | 100 | 16-bit add with carry test | 5.11 M | 5.11 M |
| `put5` | 44 | copy a 5-byte source | 2.64 M | 2.64 M |
| `skiprefs` | 112 | step over references (no decoding) | 0.80 M | 0.80 M |
| `progrec` | 264 | PROGRAM_ROM one record | 0.01 M | 0.02 M |
| `lookup` | 172 | directory -> record header | 0.81 M | 0.81 M |
| `decref` | 698 | decode one reference to a pin position | 0.64 M | 0.64 M |
| `resolve` | 984 | signal -> source pin (core and tile rules) | 2.26 M | 2.26 M |
| `emit` | 356 | one PLACE or the WIRE commands of one gate | 3.60 M | 3.60 M |
| `gates` | 252 | walk the gate entries of a record (incl. skip entries) | 3.17 M | 3.17 M |
| **builder total** | **4,970** | | **24.32 M** | **24.32 M** |