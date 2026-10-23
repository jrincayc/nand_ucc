//! nandgen text netlist import, plus differential-test vector replay.
//!
//! Format (nandgen.py `Compiled.to_text`):
//!   in N / dff M / q{i} <= w{d} / w{k} = NAND w{a} w{b}
//! Wire ids: inputs 0..n_in (SOURCE parts), then DFF outputs, then gates in listed order.
//!
//! `Netlist::build` is a *correct-by-construction, area-wasteful* layout for testing the simulator, not an
//! area-optimised one.  Part i sits on a diagonal at (2+5i, 3+5i), so every pad has its own row and the
//! driver pads their own column.  Per net: a layer-1 trunk on the driver's column; per sink a layer-0 stub
//! along the sink's own row to that column, joined by a via.  A-type inputs (NAND A, DFF D) use the spare
//! row above the part; B uses its own row.  No two nets can share a row or a column, so no shorts, and
//! every wire is laid with ordinary TRACK / VIA calls.

use crate::world::{Kind, Pin, World};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Netlist {
    pub n_in: usize,
    pub n_dff: usize,
    pub dffd: Vec<usize>,
    pub gates: Vec<(usize, usize)>,
}

pub struct NetMap {
    pub sources: Vec<u32>,
    pub dffs: Vec<u32>,
    pub nands: Vec<u32>,
}

impl Netlist {
    pub fn parse(text: &str) -> Result<Netlist, String> {
        let (mut n_in, mut n_dff) = (None, None);
        let mut dffd: Vec<usize> = Vec::new();
        let mut gates: Vec<(usize, usize)> = Vec::new();
        let wire = |s: &str, ln: usize| -> Result<usize, String> {
            s.strip_prefix('w').and_then(|r| r.parse::<usize>().ok()).ok_or_else(|| format!("line {}: bad wire name '{}'", ln, s))
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
                let ni = n_in.ok_or_else(|| format!("line {}: gate before 'in'", ln))?;
                let nd = n_dff.ok_or_else(|| format!("line {}: gate before 'dff'", ln))?;
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
        if dffd.iter().any(|&d| d >= total) || gates.iter().any(|&(a, b)| a >= total || b >= total) {
            return Err("wire id out of range".into());
        }
        Ok(Netlist { n_in, n_dff, dffd, gates })
    }

    pub fn total(&self) -> usize {
        self.n_in + self.n_dff + self.gates.len()
    }

    /// Diagonal layout; needs at least 2 copper layers.
    pub fn build(&self, w: &mut World) -> Result<NetMap, String> {
        if w.cfg.layers < 2 {
            return Err("netlist layout needs at least 2 layers".into());
        }
        let total = self.total();
        let maxc = 2 + 5 * total as i64 + 2;
        if maxc >= w.cfg.width.min(w.cfg.height) as i64 {
            return Err(format!("netlist of {} wires needs a grid of at least {}", total, maxc + 1));
        }
        let pos = |i: usize| (2 + 5 * i as i32, 3 + 5 * i as i32);
        let mut map = NetMap { sources: vec![], dffs: vec![], nands: vec![] };
        for i in 0..total {
            let (x, y) = pos(i);
            if i < self.n_in {
                map.sources.push(w.place(Kind::Source, x, y, 0, 0)?);
            } else if i < self.n_in + self.n_dff {
                map.dffs.push(w.place(Kind::Dff, x, y, 0, 0)?);
            } else {
                map.nands.push(w.place(Kind::Nand, x, y, 0, 0)?);
            }
        }
        // sinks per driver wire: (pad x, pad y, is_b)
        let mut sinks: Vec<Vec<(i32, i32, bool)>> = vec![Vec::new(); total];
        for (i, &d) in self.dffd.iter().enumerate() {
            let (x, y) = pos(self.n_in + i);
            sinks[d].push((x, y, false));
        }
        for (g, &(a, b)) in self.gates.iter().enumerate() {
            let (x, y) = pos(self.n_in + self.n_dff + g);
            sinks[a].push((x, y, false));
            sinks[b].push((x, y + 1, true));
        }
        for d in 0..total {
            if sinks[d].is_empty() {
                continue;
            }
            let (dx, dy) = pos(d);
            let tc = if d < self.n_in { dx } else { dx + 1 };
            let (mut lo, mut hi) = (dy, dy);
            for &(sx, sy, is_b) in &sinks[d] {
                let row = if is_b {
                    w.track(0, (sx, sy), (tc, sy))?;
                    sy
                } else {
                    w.track(0, (sx, sy - 1), (sx, sy))?;
                    w.track(0, (sx, sy - 1), (tc, sy - 1))?;
                    sy - 1
                };
                w.via(tc, row)?;
                lo = lo.min(row);
                hi = hi.max(row);
            }
            w.track(1, (tc, lo), (tc, hi))?;
        }
        Ok(map)
    }

    pub fn part_of(&self, map: &NetMap, id: usize) -> u32 {
        if id < self.n_in {
            map.sources[id]
        } else if id < self.n_in + self.n_dff {
            map.dffs[id - self.n_in]
        } else {
            map.nands[id - self.n_in - self.n_dff]
        }
    }
}

pub struct VecReport {
    pub ticks: usize,
    pub compared: usize,
    pub mismatches: usize,
    pub first: Vec<String>,
}

fn bits(s: &str, ln: usize) -> Result<Vec<u8>, String> {
    s.bytes()
        .map(|b| match b {
            b'0' => Ok(0u8),
            b'1' => Ok(1u8),
            _ => Err(format!("line {}: bad bit '{}'", ln, b as char)),
        })
        .collect()
}

/// Replay a `rndw-vectors 1` trace: per tick set inputs, settle, compare watched wires, step.
pub fn run_vectors(w: &mut World, nl: &Netlist, map: &NetMap, text: &str) -> Result<VecReport, String> {
    let mut watch: Vec<usize> = Vec::new();
    let (mut seen, mut n_hdr) = (false, None);
    let mut rep = VecReport { ticks: 0, compared: 0, mismatches: 0, first: vec![] };
    let total = nl.total();
    for (i, line) in text.lines().enumerate() {
        let ln = i + 1;
        let t: Vec<&str> = line.split_whitespace().collect();
        if t.is_empty() {
            continue;
        }
        match t[0] {
            "rndw-vectors" => seen = true,
            "n_in" => {
                let n: usize = t.get(1).and_then(|s| s.parse().ok()).ok_or_else(|| format!("line {}: bad n_in", ln))?;
                if n != nl.n_in {
                    return Err(format!("vector file has {} inputs, netlist has {}", n, nl.n_in));
                }
                n_hdr = Some(n);
            }
            "watch" => {
                watch = t[1..].iter().map(|s| s.parse::<usize>().map_err(|_| format!("line {}: bad wire id", ln))).collect::<Result<_, _>>()?;
                if watch.iter().any(|&x| x >= total) {
                    return Err("watch wire out of range".into());
                }
            }
            "t" => {
                if !seen || n_hdr.is_none() || t.len() != 3 {
                    return Err(format!("line {}: bad tick record", ln));
                }
                let (ins, exp) = (bits(t[1], ln)?, bits(t[2], ln)?);
                if ins.len() != nl.n_in || exp.len() != watch.len() {
                    return Err(format!("line {}: wrong number of bits", ln));
                }
                for (k, &b) in ins.iter().enumerate() {
                    w.set_source(map.sources[k], b);
                }
                w.settle();
                for (k, &id) in watch.iter().enumerate() {
                    rep.compared += 1;
                    let got = w.out_value(nl.part_of(map, id), 0);
                    if got != exp[k] {
                        rep.mismatches += 1;
                        if rep.first.len() < 10 {
                            rep.first.push(format!("tick {} wire w{}: expected {}, got {}", rep.ticks, id, exp[k], got));
                        }
                    }
                }
                w.step();
                rep.ticks += 1;
            }
            o => return Err(format!("line {}: unknown record '{}'", ln, o)),
        }
    }
    let _ = Pin::In(0);
    Ok(rep)
}
