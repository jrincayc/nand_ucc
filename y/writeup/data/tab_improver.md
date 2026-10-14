| improver routine | bytes | what it does | instructions gen 1->2 | gen 2->3 |
|---|---:|---|---:|---:|
| `irdb` | 34 | read a byte (improver copy of rdb) | 0.01 M | 0.00 M |
| `bt` | 48 | test / set / clear bit in a 40-bit set | 0.65 M | 0.07 M |
| `bs` | 54 | bit-set helpers | 0.07 M | 0.01 M |
| `keycmp` | 74 | compare two gates (merge, sort) | 0.12 M | 0.02 M |
| `ins` | 184 | insert a gate | 0.28 M | 0.06 M |
| `load` | 848 | read a record into the gate arrays | 0.02 M | 0.01 M |
| `compact` | 1062 | merge identical gates, drop dead gates and holes | 0.33 M | 0.03 M |
| `nextcut` | 410 | enumerate the next cut of a root | 0.26 M | 0.05 M |
| `cone` | 1270 | cone, saved-gate count, truth tables | 1.18 M | 0.15 M |
| `search` | 598 | exhaustive iterative-deepening NAND search | 4.33 M | 0.84 M |
| `rewrite` | 786 | insert the new gates, rewire the users | 0.03 M | 0.00 M |
| `partition` | 900 | move outputs to the end, ascending | 0.00 M | 0.00 M |
| `layout` | 1208 | slot form: holes as skip entries, size check | 0.02 M | 0.00 M |
| `improve_type` | 482 | driver of the loop | 0.05 M | 0.01 M |
| **improver total** | **7,958** | | **7.35 M** | **1.26 M** |