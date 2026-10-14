//! Differential testing against the Python reference (`gen_vectors.py` + `nandgen.Sim`).
//!
//! Vector file ("rndw-vectors 1"):
//!   rndw-vectors 1
//!   n_in <N>
//!   watch <wire id> ...            wires compared every tick
//!   t <N input bits> <watch bits>  one line per tick, bit i = wire i / watch i
//!
//! Per tick: drive the Sources from the input bits, settle, compare the watched wires with the
//! expected bits, then clock the world one tick.

use crate::netlist::{NetMap, Netlist};
use crate::world::World;

pub struct VecReport {
    pub ticks: usize,
    pub compared: usize,
    pub mismatches: usize,
    pub first: Vec<String>,
}

fn bits(s: &str, ln: usize, what: &str) -> Result<Vec<u8>, String> {
    s.bytes()
        .map(|b| match b {
            b'0' => Ok(0u8),
            b'1' => Ok(1u8),
            _ => Err(format!("line {}: bad {} bit '{}'", ln, what, b as char)),
        })
        .collect()
}

pub fn run_vectors(w: &mut World, nl: &Netlist, map: &NetMap, text: &str) -> Result<VecReport, String> {
    let mut watch: Vec<usize> = Vec::new();
    let mut seen_header = false;
    let mut n_in_hdr = None;
    let mut rep = VecReport { ticks: 0, compared: 0, mismatches: 0, first: Vec::new() };
    let total = nl.n_in + nl.n_dff + nl.gates.len();
    let part_of = |id: usize| -> u32 {
        if id < nl.n_in {
            map.sources[id]
        } else if id < nl.n_in + nl.n_dff {
            map.dffs[id - nl.n_in]
        } else {
            map.nands[id - nl.n_in - nl.n_dff]
        }
    };
    for (i, line) in text.lines().enumerate() {
        let ln = i + 1;
        let t: Vec<&str> = line.split_whitespace().collect();
        if t.is_empty() {
            continue;
        }
        match t[0] {
            "rndw-vectors" => seen_header = true,
            "n_in" => {
                let n: usize = t.get(1).and_then(|s| s.parse().ok()).ok_or_else(|| format!("line {}: bad n_in", ln))?;
                if n != nl.n_in {
                    return Err(format!("vector file has {} inputs, netlist has {}", n, nl.n_in));
                }
                n_in_hdr = Some(n);
            }
            "watch" => {
                watch = t[1..]
                    .iter()
                    .map(|s| s.parse::<usize>().map_err(|_| format!("line {}: bad wire id", ln)))
                    .collect::<Result<_, _>>()?;
                if let Some(&bad) = watch.iter().find(|&&x| x >= total) {
                    return Err(format!("watch wire {} out of range", bad));
                }
            }
            "t" => {
                if !seen_header || n_in_hdr.is_none() {
                    return Err(format!("line {}: tick before header", ln));
                }
                if t.len() != 3 {
                    return Err(format!("line {}: expected 't <inputs> <expected>'", ln));
                }
                let ins = bits(t[1], ln, "input")?;
                let exp = bits(t[2], ln, "expected")?;
                if ins.len() != nl.n_in || exp.len() != watch.len() {
                    return Err(format!("line {}: wrong number of bits", ln));
                }
                for (k, &b) in ins.iter().enumerate() {
                    w.set_source(map.sources[k], b);
                }
                w.settle();
                for (k, &id) in watch.iter().enumerate() {
                    rep.compared += 1;
                    let got = w.out_value(part_of(id), 0);
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
            other => return Err(format!("line {}: unknown record '{}'", ln, other)),
        }
    }
    Ok(rep)
}
