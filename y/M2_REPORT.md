# M2 report: text assembler, listing and coverage checker

Files (nandgen/y/): tools/asm.py (300 lines incl. docstring), tools/trace_check.py (181), examples/demo.asm, tests/test_m2.py. Works for any AB 13..15 (`HACK_AB`, default 14).

## asm.py
`python3 asm.py -o OUTDIR a.asm b.asm ...` -> rom.bin, rom.lst, rom.map.json, symbols.txt. Hack syntax with `//` comments; `.org .equ .byte .word .space .macro .endm`; expressions `+ - *`, parentheses, `lo()`, `hi()`; macros are text substitution (`\\name` for parameters, `\\@` for a unique number); a macro call is listed as a zero-byte line and each expanded line is listed with its definition line and call site. Errors (unknown comp, bad dest/jump, A-value outside 0..AMASK, byte/word range, undefined or duplicate symbol, address outside ROM, overlapping bytes, macro arity, unterminated macro, unknown directive) stop the build with file:line.
Two points to know: (1) an instruction with a=1 whose comp ignores M (e.g. word 0xFAA0, "A=0" with a=1) has no text spelling; the assembler never produces it and the decoder reports it as "not an instruction". The CPU treats it as the a=0 form except for a read of M with no visible effect. (2) `.org` gaps stay unprogrammed (read 0) and appear in the listing as gap lines; `.space n` programs n zero bytes and is listed.

## trace_check.py
Imports nothing from asm.py; has its own comp/dest/jump tables written from HACK_VN.md and its own expression evaluator.
C1 listing bytes equal rom.bin, no overlaps. C2 every non-zero ROM byte is covered by a listing entry. C3 each entry's text is the real text of its source line (macro lines: matches the macro definition with arguments wildcarded). C4 each entry has a non-empty `//` comment. C5 each 2-byte instruction decodes (own decoder) to the instruction in the source; `@expr` is re-evaluated against symbols.txt. C6 every emitting source line of the given files is in the listing. The report prints counts.
Known limit: data lines (`.byte`, `.word`) are checked for bytes, coverage, text and comment, but nothing can check that the comment says the right thing; that is for the reader (and for hd2asm, which will generate the comment from the HD text).

## Tests (tests/test_m2.py, AB=14 and AB=13: ALL PASS, 31 checks)
- demo.asm: audit passes (40 entries, 28 emitting lines); model result SUM=55, CNT=0, OUT=0x11,0x22 in 130 instructions; gate-level CPU in lockstep with the model, 131 instructions, 336 ticks.
- Round trip against the verified Python assembler/decoder path: K1-K4 code and 30 fuzz images (48,798 bytes, covering all comps, dests, jumps, AP, 15-bit A values) are disassembled by trace_check's decoder to text, reassembled by asm.py, and are byte-identical.
- Every comp x dest-spelling x jump combination (2,880 lines, both M and A spellings) equals isahack.Asm.C; commutative spellings (A+D, M|D ...) normalise.
- 14 assembler error cases are rejected with file:line.
- 8 tampering cases are caught by the intended check: flipped rom.bin byte (C1), extra non-zero byte (C2), deleted listing line (C6), comment removed from the listing (C4), source edited after assembling (C3), bytes changed consistently in listing and rom.bin (C5), source line added after assembling (C6), comment removed from the source (C3).
Not done: a mutation test of asm.py itself (the round trip and the exhaustive combination test play that role); a check that every macro body line is used.
