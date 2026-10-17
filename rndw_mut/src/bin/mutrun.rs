//! Mutant experiments on the X quine.
//!   mutrun validate A.txt B.txt           run A to B's tick, compare save_state() with B byte for byte
//!   mutrun child CMDS ROM [opts]          build the child a mutant parent would build (from its command stream),
//!                                         run the child, compare what it builds with the stream that built it
//!   mutrun full STATE ROM TICKS           gate-level parent: poke ROM into gen-1, run, summarise the child
//! Command file lines:  P kind x y rot | W ax ay bx by (absolute coords) | X code kind angle ax ay bx by val (expected, relative)
use rndw::world::*;
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs;

fn i16le(r: &[u8; ARM_REGS], lo: usize) -> i32 {
    (r[lo] as u16 | ((r[lo + 1] as u16) << 8)) as i16 as i32
}

fn hash(items: &mut Vec<Vec<i64>>) -> u64 {
    items.sort();
    let mut h: u64 = 1469598103934665603;
    for it in items.iter() {
        for v in it {
            h ^= *v as u64;
            h = h.wrapping_mul(1099511628211);
        }
        h ^= 0xFF;
        h = h.wrapping_mul(1099511628211);
    }
    h
}

/// Normalised summary of parts with id >= first (positions are kept: callers shift if needed).
fn summary(w: &World, first: usize, dy: i32) -> String {
    let mut parts: Vec<Vec<i64>> = Vec::new();
    for p in &w.parts[first..] {
        parts.push(vec![p.kind.code() as i64, p.x as i64, (p.y + dy) as i64, p.rot as i64]);
    }
    let lo = |x: i32, y: i32| w.part_at(x, y).map(|p| p as usize).unwrap_or(usize::MAX);
    let mut wires: Vec<Vec<i64>> = Vec::new();
    for &(a, b, c, d) in &w.wires {
        if lo(a, b) != usize::MAX && lo(a, b) >= first {
            wires.push(vec![a as i64, (b + dy) as i64, c as i64, (d + dy) as i64]);
        }
    }
    let nrom = w.parts[first..].iter().filter(|p| p.kind == Kind::Rom).count();
    let mut romh = 0u64;
    for p in &w.parts[first..] {
        if p.kind == Kind::Rom {
            let mut v: Vec<Vec<i64>> = w.roms[p.aux as usize].iter().enumerate().filter(|(_, b)| **b != 0).map(|(a, b)| vec![a as i64, *b as i64]).collect();
            romh ^= hash(&mut v);
        }
    }
    format!("parts={} wires={} parts_hash={:016x} wires_hash={:016x} roms={} rom_hash={:016x}", parts.len(), wires.len(), hash(&mut parts), hash(&mut wires), nrom, romh)
}

fn main() {
    let a: Vec<String> = env::args().collect();
    if a.len() < 2 {
        eprintln!("usage: mutrun validate|child|full ...");
        std::process::exit(2);
    }
    match a[1].as_str() {
        "validate" => {
            let mut w = World::load_state(&fs::read_to_string(&a[2]).unwrap()).unwrap();
            let want = fs::read_to_string(&a[3]).unwrap();
            let target: u64 = want.lines().find(|l| l.starts_with("tick ")).unwrap()[5..].trim().parse().unwrap();
            while w.tick < target {
                w.step();
            }
            let got = w.save_state();
            println!("ran to tick {} faults {}  save_state equal to file: {}", w.tick, w.faults, got == want);
            if got != want {
                for (i, (g, e)) in got.lines().zip(want.lines()).enumerate() {
                    if g != e {
                        println!("first differing line {}: got '{}' want '{}'", i + 1, g, e);
                        break;
                    }
                }
            }
        }
        "watch" => {
            let mut w = World::load_state(&fs::read_to_string(&a[2]).unwrap()).unwrap();
            let ticks: u64 = a[3].parse().unwrap();
            let pids: Vec<u32> = a[4..].iter().map(|s| s.parse().unwrap()).collect();
            let np = pids.len() / 2;
            let mut diff = vec![0u64; np];
            let mut first = vec![0u64; np];
            let mut hi = vec![0u64; np];
            for t in 0..ticks {
                w.step();
                for k in 0..np {
                    let (x, y) = (w.out_value(pids[2 * k], 0), w.out_value(pids[2 * k + 1], 0));
                    if x != y {
                        if diff[k] == 0 { first[k] = t; }
                        diff[k] += 1;
                    }
                    if x == 1 { hi[k] += 1; }
                }
            }
            for k in 0..np {
                println!("pair {} ({},{}): differ on {} of {} ticks (first at +{}); old signal high on {} ticks", k, pids[2 * k], pids[2 * k + 1], diff[k], ticks, first[k], hi[k]);
            }
        }
        "watch3" => {
            // triples (other_pid, newsrc_pid, dest_pid): how often would NAND(other, newsrc) differ from the dest's real output?
            let mut w = World::load_state(&fs::read_to_string(&a[2]).unwrap()).unwrap();
            let ticks: u64 = a[3].parse().unwrap();
            let pids: Vec<u32> = a[4..].iter().map(|s| s.parse().unwrap()).collect();
            let n = pids.len() / 3;
            let mut diff = vec![0u64; n];
            let mut first = vec![0u64; n];
            for t in 0..ticks {
                w.step();
                for k in 0..n {
                    let (o, ns, d) = (w.out_value(pids[3 * k], 0), w.out_value(pids[3 * k + 1], 0), w.out_value(pids[3 * k + 2], 0));
                    if 1 - (o & ns) != d {
                        if diff[k] == 0 { first[k] = t; }
                        diff[k] += 1;
                    }
                }
            }
            for k in 0..n {
                println!("gate {}: mutated gate output would differ from the original on {} of {} ticks (first at +{})", k, diff[k], ticks, first[k]);
            }
        }
        "full" => {
            let mut w = World::load_state(&fs::read_to_string(&a[2]).unwrap()).unwrap();
            let rom = fs::read(&a[3]).unwrap();
            let ticks: u64 = a[4].parse().unwrap();
            // the parent's ROM is the ROM part with the highest id below its arm: locate gen-1 ROM (kind 2 followed by arm)
            let n0 = w.parts.len();
            let rom_part = (0..n0).filter(|&i| w.parts[i].kind == Kind::Rom).last().unwrap() as u32;
            let first_child = n0; // child parts get ids >= n0
            for (ad, v) in rom.iter().enumerate() {
                w.rom_poke(rom_part, ad, *v).unwrap();
            }
            w.settle();
            let t0 = w.tick;
            while w.tick - t0 < ticks {
                w.step();
            }
            println!("full: ran {} ticks, faults {}, parts {} (+{})", ticks, w.faults, w.parts.len(), w.parts.len() - n0);
            for m in w.fault_log.iter().take(5) {
                println!("  fault: {}", m);
            }
            let oy = w.parts[rom_part as usize + 1].y;
            // shift child coordinates so they compare with a replay world whose parent arm is at the same place
            println!("child {}", summary(&w, first_child, 0));
            let _ = oy;
        }
        "child" => {
            let mut max_ticks: u64 = 9_000_000;
            let mut stall: u64 = 400_000;
            let mut per_cmd: u64 = 8;
            let mut k = 4;
            while k + 1 < a.len() {
                match a[k].as_str() {
                    "--max-ticks" => max_ticks = a[k + 1].parse().unwrap(),
                    "--stall" => stall = a[k + 1].parse().unwrap(),
                    "--per-cmd" => per_cmd = a[k + 1].parse().unwrap(),
                    _ => {}
                }
                k += 2;
            }
            let text = fs::read_to_string(&a[2]).unwrap();
            let rom = fs::read(&a[3]).unwrap();
            let mut stream: Vec<(char, Vec<i32>)> = Vec::new();
            let mut expected: Vec<Vec<i32>> = Vec::new();
            for l in text.lines() {
                let t: Vec<&str> = l.split_whitespace().collect();
                if t.is_empty() {
                    continue;
                }
                let v: Vec<i32> = t[1..].iter().map(|s| s.parse().unwrap()).collect();
                match t[0] {
                    "P" | "W" => stream.push((t[0].chars().next().unwrap(), v)),
                    "X" => expected.push(v),
                    _ => {}
                }
            }
            let cfg = Config { width: 65536, height: 4096, rom_abits: 12, event_limit: 5_000_000 };
            let mut w = World::new(cfg);
            w.log_cmds = true;
            let mut rom_origin: Option<(i32, i32)> = None;
            let mut rom_done = false;
            let program = |w: &mut World, org: Option<(i32, i32)>| {
                match org {
                    None => w.fault("child ROM never placed; cannot program it".into()),
                    Some((ox, oy)) => {
                        for (ad, v) in rom.iter().enumerate() {
                            if *v != 0 {
                                if let Err(e) = w.program_rom(ox, oy, ad, *v) {
                                    w.fault(e);
                                    break;
                                }
                            }
                        }
                    }
                }
            };
            let n = stream.len();
            let t_build0 = w.tick;
            for (i, (c, v)) in stream.iter().enumerate() {
                match c {
                    'P' => match Kind::from_code(v[0] as u8) {
                        None => w.fault(format!("PLACE with bad KIND {}", v[0])),
                        Some(kd) => match w.place(kd, v[1], v[2], v[3] as u8) {
                            Ok(_) => {
                                if kd == Kind::Rom && rom_origin.is_none() {
                                    rom_origin = Some((v[1], v[2]));
                                }
                            }
                            Err(e) => w.fault(e),
                        },
                    },
                    _ => {
                        if !rom_done {
                            program(&mut w, rom_origin);
                            rom_done = true;
                            for _ in 0..300 {
                                w.step();
                            }
                        }
                        if let Err(e) = w.connect((v[0], v[1]), (v[2], v[3])) {
                            w.fault(e);
                        }
                    }
                }
                let steps = if i + 1 == n { 0 } else if n - i <= 4 { 300 } else { per_cmd };
                for _ in 0..steps {
                    w.step();
                }
            }
            if !rom_done {
                program(&mut w, rom_origin);
            }
            let s1_faults = w.faults;
            let mut cnt = [0usize; 5];
            for p in &w.parts {
                cnt[p.kind.code() as usize] += 1;
            }
            print!("stage1: faults={} nand={} dff={} rom={} arm={} wires={}", s1_faults, cnt[0], cnt[1], cnt[2], cnt[3], w.wires.len());
            if s1_faults > 0 {
                print!(" first_fault='{}'", w.fault_log.first().cloned().unwrap_or_default());
            }
            println!();
            println!("child_summary: {}", summary(&w, 0, 0));
            // ---- stage 2
            let arm_part = (0..w.parts.len()).filter(|&i| w.parts[i].kind == Kind::Arm).last();
            let ap = match arm_part {
                None => {
                    println!("result: NO_ARM");
                    return;
                }
                Some(p) => p,
            };
            let en_wired = w.in_src[(w.parts[ap].in_base + 4) as usize] != NONE;
            if !en_wired {
                println!("result: ARM_EN_UNWIRED (child can never issue a command)");
                return;
            }
            let _ = t_build0;
            let f0 = w.faults;
            let mut processed = 0usize;
            let mut cmp_idx = 0usize;
            let mut roms: BTreeMap<usize, u8> = BTreeMap::new();
            let mut rom_errs = 0usize;
            let t_start = w.tick;
            let mut last_progress = w.tick;
            let mut verdict = String::new();
            'outer: loop {
                for _ in 0..1000 {
                    w.step();
                }
                if w.cmdlog.len() > processed {
                    last_progress = w.tick;
                }
                while processed < w.cmdlog.len() {
                    let (code, r, err) = w.cmdlog[processed].clone();
                    processed += 1;
                    if code == CMD_PROGRAM_ROM {
                        let ad = (r[4] as usize) | ((r[5] as usize) << 8);
                        roms.insert(ad, r[10]);
                        if err.is_some() {
                            rom_errs += 1;
                        }
                        continue;
                    }
                    let got: Vec<i32> = vec![code as i32, r[8] as i32, r[9] as i32, i16le(&r, 0), i16le(&r, 2), i16le(&r, 4), i16le(&r, 6)];
                    if cmp_idx >= expected.len() {
                        break;
                    }
                    let e = &expected[cmp_idx];
                    let same = if e[0] != got[0] {
                        false
                    } else if e[0] == 1 {
                        e[1] == got[1] && e[2] == got[2] && e[3] == got[3] && e[4] == got[4]
                    } else {
                        e[3] == got[3] && e[4] == got[4] && e[5] == got[5] && e[6] == got[6]
                    };
                    if !same || err.is_some() {
                        verdict = format!("DIVERGES at command {}/{}: got {:?} expected {:?} err={:?}", cmp_idx, expected.len(), got, e, err);
                        break 'outer;
                    }
                    cmp_idx += 1;
                }
                if cmp_idx == expected.len() {
                    let want: BTreeMap<usize, u8> = rom.iter().enumerate().filter(|(_, b)| **b != 0).map(|(i, b)| (i, *b)).collect();
                    if roms != want {
                        let missing = want.keys().filter(|k| !roms.contains_key(k)).count();
                        let wrong = roms.iter().filter(|(k, v)| want.get(k) != Some(v)).count();
                        verdict = format!("ROM_COPY_DIFFERS (missing {} bytes, wrong/extra {}; {} rom errs)", missing, wrong, rom_errs);
                    } else {
                        verdict = "REPLICATES (grandchild command stream and ROM identical to the child's own)".into();
                    }
                    break;
                }
                if w.tick - last_progress > stall {
                    // diagnose: watch the ROM address bus for 50k ticks
                    let rp = (0..w.parts.len()).find(|&i| w.parts[i].kind == Kind::Rom);
                    let mut seen: BTreeSet<usize> = BTreeSet::new();
                    let mut last = 0usize;
                    if let Some(rp) = rp {
                        let ib = w.parts[rp].in_base as usize;
                        for _ in 0..50_000 {
                            w.step();
                            let mut ad = 0usize;
                            for b in 0..12 {
                                let sidx = w.in_src[ib + b];
                                let v = if sidx == NONE { 0 } else { w.val[sidx as usize] as usize };
                                ad |= v << b;
                            }
                            seen.insert(ad);
                            last = ad;
                        }
                    }
                    let mx = seen.iter().next_back().cloned().unwrap_or(0);
                    println!("diag: rom_addresses_seen={} max=0x{:x} last=0x{:x} first_cmd_expected_region", seen.len(), mx, last);
                    verdict = format!("STALLED after {} matched commands ({} ticks without a command)", cmp_idx, stall);
                    break;
                }
                if w.tick - t_start > max_ticks {
                    verdict = format!("TIMEOUT after {} matched commands", cmp_idx);
                    break;
                }
            }
            println!("result: {}", verdict);
            println!("stage2: ticks={} matched_cmds={} rom_cmds={} faults_since={}", w.tick - t_start, cmp_idx, roms.len(), w.faults - f0);
            let _ = BTreeSet::<u8>::new();
        }
        _ => {}
    }
}
