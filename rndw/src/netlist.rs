//! nandgen text netlist import / export.
//!
//! Format (as written by nandgen.py `Compiled.to_text`):
//!   in N
//!   dff M
//!   q{i} <= w{d}                  (DFF i; its Q is wire n_in + i)
//!   w{k} = NAND w{a} w{b}         (k = n_in + n_dff + gate index)
//! Wire ids: inputs 0..n_in, then DFF outputs, then gates in listed order.

use crate::world::{Kind, Pin, World};
use std::cmp::Reverse;
use std::collections::BinaryHeap;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Netlist {
    pub n_in: usize,
    pub n_dff: usize,
    pub dffd: Vec<usize>,
    pub gates: Vec<(usize, usize)>,
}

/// Part ids created by `Netlist::build`.
pub struct NetMap {
    pub sources: Vec<u32>,
    pub dffs: Vec<u32>,
    pub nands: Vec<u32>,
}

impl Netlist {
    pub fn parse(text: &str) -> Result<Netlist, String> {
        let mut n_in = None;
        let mut n_dff = None;
        let mut dffd: Vec<usize> = Vec::new();
        let mut gates: Vec<(usize, usize)> = Vec::new();
        let wire = |s: &str, ln: usize| -> Result<usize, String> {
            s.strip_prefix('w')
                .and_then(|r| r.parse::<usize>().ok())
                .ok_or_else(|| format!("line {}: bad wire name '{}'", ln, s))
        };
        for (i, line) in text.lines().enumerate() {
            let ln = i + 1;
            let l = line.trim();
            if l.is_empty() || l.starts_with('#') {
                continue;
            }
            let t: Vec<&str> = l.split_whitespace().collect();
            if t[0] == "in" && t.len() == 2 {
                n_in = Some(t[1].parse::<usize>().map_err(|_| format!("line {}: bad count", ln))?);
            } else if t[0] == "dff" && t.len() == 2 {
                n_dff = Some(t[1].parse::<usize>().map_err(|_| format!("line {}: bad count", ln))?);
            } else if t.len() == 3 && t[0].starts_with('q') && t[1] == "<=" {
                let idx: usize = t[0][1..].parse().map_err(|_| format!("line {}: bad DFF name", ln))?;
                if idx != dffd.len() {
                    return Err(format!("line {}: DFFs must be listed in order", ln));
                }
                dffd.push(wire(t[2], ln)?);
            } else if t.len() == 5 && t[0].starts_with('w') && t[1] == "=" && t[2] == "NAND" {
                let k = wire(t[0], ln)?;
                let (ni, nd) = (
                    n_in.ok_or_else(|| format!("line {}: gate before 'in'", ln))?,
                    n_dff.ok_or_else(|| format!("line {}: gate before 'dff'", ln))?,
                );
                if k != ni + nd + gates.len() {
                    return Err(format!("line {}: gate wires must be numbered consecutively", ln));
                }
                gates.push((wire(t[3], ln)?, wire(t[4], ln)?));
            } else {
                return Err(format!("line {}: cannot parse '{}'", ln, l));
            }
        }
        let n_in = n_in.ok_or("missing 'in' line")?;
        let n_dff = n_dff.ok_or("missing 'dff' line")?;
        if dffd.len() != n_dff {
            return Err(format!("expected {} DFF lines, found {}", n_dff, dffd.len()));
        }
        let total = n_in + n_dff + gates.len();
        for &d in &dffd {
            if d >= total {
                return Err(format!("DFF input w{} out of range", d));
            }
        }
        for &(a, b) in &gates {
            if a >= total || b >= total {
                return Err(format!("gate input out of range (w{} / w{})", a, b));
            }
        }
        Ok(Netlist { n_in, n_dff, dffd, gates })
    }

    pub fn to_text(&self) -> String {
        let base = self.n_in + self.n_dff;
        let mut s = format!("in {}\ndff {}\n", self.n_in, self.n_dff);
        for (i, d) in self.dffd.iter().enumerate() {
            s.push_str(&format!("q{} <= w{}\n", i, d));
        }
        for (i, (a, b)) in self.gates.iter().enumerate() {
            s.push_str(&format!("w{} = NAND w{} w{}\n", base + i, a, b));
        }
        s
    }

    /// Place every wire as a part on a canonical grid (pitch 3) and connect them.
    /// Inputs become harness Source parts.
    pub fn build(&self, w: &mut World) -> Result<NetMap, String> {
        let total = self.n_in + self.n_dff + self.gates.len();
        let cols = ((total as f64).sqrt().ceil() as usize).max(1);
        let slot = |s: usize| (2 + (s % cols) as i32 * 3, 2 + (s / cols) as i32 * 3);
        let mut sources = Vec::new();
        let mut dffs = Vec::new();
        let mut nands = Vec::new();
        for s in 0..total {
            let (x, y) = slot(s);
            if s < self.n_in {
                sources.push(w.place(Kind::Source, x, y, 0)?);
            } else if s < self.n_in + self.n_dff {
                dffs.push(w.place(Kind::Dff, x, y, 0)?);
            } else {
                nands.push(w.place(Kind::Nand, x, y, 0)?);
            }
        }
        let out_part = |id: usize| -> u32 {
            if id < self.n_in {
                sources[id]
            } else if id < self.n_in + self.n_dff {
                dffs[id - self.n_in]
            } else {
                nands[id - self.n_in - self.n_dff]
            }
        };
        for (i, &d) in self.dffd.iter().enumerate() {
            let o = w.pin_site(out_part(d), Pin::Out(0)).unwrap();
            let t = w.pin_site(dffs[i], Pin::In(0)).unwrap();
            w.connect(o, t)?;
        }
        for (i, &(a, b)) in self.gates.iter().enumerate() {
            let oa = w.pin_site(out_part(a), Pin::Out(0)).unwrap();
            let ob = w.pin_site(out_part(b), Pin::Out(0)).unwrap();
            let ta = w.pin_site(nands[i], Pin::In(0)).unwrap();
            let tb = w.pin_site(nands[i], Pin::In(1)).unwrap();
            w.connect(oa, ta)?;
            w.connect(ob, tb)?;
        }
        Ok(NetMap { sources, dffs, nands })
    }
}

/// Export a world made only of Source / DFF / NAND parts with every input driven and an
/// acyclic combinational network.  Source parts become netlist inputs (in part order).
pub fn export(w: &World) -> Result<Netlist, String> {
    let mut sources = Vec::new();
    let mut dffs = Vec::new();
    let mut nands = Vec::new();
    for (i, p) in w.parts.iter().enumerate() {
        match p.kind {
            Kind::Source => sources.push(i as u32),
            Kind::Dff => dffs.push(i as u32),
            Kind::Nand => nands.push(i as u32),
            k => return Err(format!("cannot export a world containing a {}", k.name())),
        }
    }
    let driver = |part: u32, pin: u32| -> Result<u32, String> {
        let s = w.in_src[(w.parts[part as usize].in_base + pin) as usize];
        if s == crate::world::NONE {
            Err(format!("part {} has an undriven input", part))
        } else {
            Ok(w.sig_owner[s as usize])
        }
    };
    // Kahn order over NAND -> NAND dependencies, smallest part id first (stable).
    let mut indeg = vec![0usize; w.parts.len()];
    let mut deps: Vec<Vec<u32>> = vec![Vec::new(); w.parts.len()];
    for &n in &nands {
        for pin in 0..2 {
            let d = driver(n, pin)?;
            if w.parts[d as usize].kind == Kind::Nand {
                indeg[n as usize] += 1;
                deps[d as usize].push(n);
            }
        }
    }
    let mut heap: BinaryHeap<Reverse<u32>> = nands.iter().filter(|&&n| indeg[n as usize] == 0).map(|&n| Reverse(n)).collect();
    let mut order = Vec::new();
    while let Some(Reverse(n)) = heap.pop() {
        order.push(n);
        for &c in &deps[n as usize] {
            indeg[c as usize] -= 1;
            if indeg[c as usize] == 0 {
                heap.push(Reverse(c));
            }
        }
    }
    if order.len() != nands.len() {
        return Err("combinational cycle: cannot export".into());
    }
    let mut wid = vec![usize::MAX; w.parts.len()];
    for (i, &s) in sources.iter().enumerate() {
        wid[s as usize] = i;
    }
    for (i, &d) in dffs.iter().enumerate() {
        wid[d as usize] = sources.len() + i;
    }
    for (i, &n) in order.iter().enumerate() {
        wid[n as usize] = sources.len() + dffs.len() + i;
    }
    let mut dffd = Vec::new();
    for &d in &dffs {
        dffd.push(wid[driver(d, 0)? as usize]);
    }
    let mut gates = Vec::new();
    for &n in &order {
        gates.push((wid[driver(n, 0)? as usize], wid[driver(n, 1)? as usize]));
    }
    Ok(Netlist { n_in: sources.len(), n_dff: dffs.len(), dffd, gates })
}
