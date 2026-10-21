//! layout -- generic placer + router for RNDP netlists (NAND/DFF 2x2 parts on a pitch grid, ROM/ARM/RAM parts in margins).
//! usage: layout NETLIST.nl OUT.lay [key=value ...]
//! keys: px py cols gap ml mr seed effort via turn rom_rot arm_rot ram_rot iters
use std::collections::{BinaryHeap, HashMap};
use std::cmp::Reverse;
use std::fs;
use std::time::Instant;

struct Rng(u64);
impl Rng {
    fn next(&mut self) -> u64 { let mut x = self.0; x ^= x << 13; x ^= x >> 7; x ^= x << 17; self.0 = x; x }
    fn below(&mut self, n: usize) -> usize { (self.next() % n as u64) as usize }
    fn f(&mut self) -> f64 { (self.next() >> 11) as f64 / (1u64 << 53) as f64 }
}

#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash)]
enum Drv { Node(usize), Rom(usize), Ramo(usize) }
#[derive(Clone, Copy, Debug)]
enum Snk { NodePin(usize, usize), Port(usize) }  // node, pin | index into ports

struct Netlist {
    rom_abits: usize, ram_abits: usize,
    kind: Vec<u8>,                              // b'N' | b'D'
    ins: Vec<Vec<Option<(Drv, u8)>>>,           // per node: source and late level per input pin
    ports: Vec<(String, Option<(Drv, u8)>)>,
}

fn parse_src(t: &str) -> Option<(Drv, u8)> {
    if t == "open" { return None; }
    let (b, late) = match t.split_once('@') { Some((b, l)) => (b, l.parse().unwrap()), None => (t, 0u8) };
    let d = if let Some(r) = b.strip_prefix("ramo") { Drv::Ramo(r.parse().unwrap()) }
        else if let Some(r) = b.strip_prefix("rom") { Drv::Rom(r.parse().unwrap()) }
        else if let Some(r) = b.strip_prefix('n') { Drv::Node(r.parse().unwrap()) } else { panic!("bad src {t}") };
    Some((d, late))
}

fn read_nl(path: &str) -> Netlist {
    let mut nl = Netlist { rom_abits: 0, ram_abits: 0, kind: vec![], ins: vec![], ports: vec![] };
    for line in fs::read_to_string(path).unwrap().lines() {
        let w: Vec<&str> = line.split_whitespace().collect();
        if w.is_empty() { continue; }
        match w[0] {
            "rom" => nl.rom_abits = w[1].parse().unwrap(),
            "ram" => nl.ram_abits = w[1].parse().unwrap(),
            "n" => { let k: usize = w[1].parse().unwrap(); assert_eq!(k, nl.kind.len());
                     nl.kind.push(w[2].as_bytes()[0]); nl.ins.push(w[3..].iter().map(|t| parse_src(t)).collect()); }
            "p" => nl.ports.push((w[1].to_string(), parse_src(w[2]))),
            _ => panic!("bad line {line}"),
        }
    }
    nl
}

// ---------------------------------------------------------------- fixed parts
#[derive(Clone)]
struct FixedPart { name: &'static str, kind: u8, abits: usize, rot: usize, x: i32, y: i32, w: i32, h: i32 }
fn base_dims(kind: u8, abits: usize) -> (i32, i32) {
    match kind { 2 => (2, abits.max(8) as i32), 3 => (2, 9), 4 => (2, abits as i32 + 9), _ => (2, 2) }
}
fn rot_cell(mut c: (i32, i32), mut w: i32, mut h: i32, rot: usize) -> (i32, i32) {
    for _ in 0..rot { c = (h - 1 - c.1, c.0); std::mem::swap(&mut w, &mut h); }
    c
}
fn rot_dims(w: i32, h: i32, rot: usize) -> (i32, i32) { if rot % 2 == 1 { (h, w) } else { (w, h) } }
impl FixedPart {
    fn cell(&self, dx: i32, dy: i32) -> (i32, i32) {
        let (bw, bh) = base_dims(self.kind, self.abits);
        let c = rot_cell((dx, dy), bw, bh, self.rot);
        (self.x + c.0, self.y + c.1)
    }
}

// ---------------------------------------------------------------- config
struct Cfg { px: i32, py: i32, cols: usize, gap: i32, ml: i32, mr: i32, seed: u64, effort: f64, via: i32, turn: i32,
             rom_rot: usize, arm_rot: usize, ram_rot: usize, iters: usize, ram_side: i32, aspect: f64, edge: i32 }

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let mut kv: HashMap<String, String> = HashMap::new();
    for s in &a[3..] { let (k, v) = s.split_once('=').unwrap(); kv.insert(k.into(), v.into()); }
    let g = |k: &str, d: f64| -> f64 { kv.get(k).map(|v| v.parse().unwrap()).unwrap_or(d) };
    let cfg = Cfg { px: g("px", 4.0) as i32, py: g("py", 4.0) as i32, cols: g("cols", 0.0) as usize, gap: g("gap", 6.0) as i32,
        ml: g("ml", 6.0) as i32, mr: g("mr", 6.0) as i32, seed: g("seed", 1.0) as u64, effort: g("effort", 1.0),
        via: g("via", 3.0) as i32, turn: g("turn", 2.0) as i32, rom_rot: g("rom_rot", 1.0) as usize, arm_rot: g("arm_rot", 1.0) as usize,
        ram_rot: g("ram_rot", 1.0) as usize, iters: g("iters", 60.0) as usize, ram_side: g("ram_side", 0.0) as i32, aspect: g("aspect", 1.0), edge: g("edge", 14.0) as i32 };
    let nl = read_nl(&a[1]);
    run(&nl, &cfg, &a[2]);
}

// ---------------------------------------------------------------- geometry of the whole board
struct Board {
    w: i32, h: i32, gx0: i32, gy0: i32, cols: usize, rows: usize,
    rom: FixedPart, arm: FixedPart, ram: Option<FixedPart>,
}

fn pin_of_node(kind: u8, x: i32, y: i32, pin: usize) -> (i32, i32) { let _ = kind; (x, y + pin as i32) }
fn out_of_node(x: i32, y: i32) -> (i32, i32) { (x + 1, y) }

fn driver_cell(b: &Board, pos: &[(i32, i32)], d: Drv) -> (i32, i32) {
    match d {
        Drv::Node(k) => out_of_node(pos[k].0, pos[k].1),
        Drv::Rom(j) => b.rom.cell(1, j as i32),
        Drv::Ramo(c) => b.ram.as_ref().unwrap().cell(1, c as i32),
    }
}
fn port_cell(b: &Board, name: &str, nl: &Netlist) -> (i32, i32) {
    let num = |p: &str| -> i32 { name[p.len()..].parse().unwrap() };
    if name.starts_with("rom_addr") { b.rom.cell(0, num("rom_addr")) }
    else if name.starts_with("arm_addr") { b.arm.cell(0, num("arm_addr")) }
    else if name.starts_with("wdata") { b.arm.cell(1, num("wdata")) }
    else if name == "arm_en" { b.arm.cell(0, 4) }
    else if name.starts_with("ram_addr") { b.ram.as_ref().unwrap().cell(0, num("ram_addr")) }
    else if name == "ram_we" { b.ram.as_ref().unwrap().cell(0, nl.ram_abits as i32) }
    else if name.starts_with("ram_din") { b.ram.as_ref().unwrap().cell(0, nl.ram_abits as i32 + 1 + num("ram_din")) }
    else { panic!("port {name}") }
}

fn make_board(nl: &Netlist, cfg: &Cfg) -> Board {
    let n = nl.kind.len();
    let cols = if cfg.cols > 0 { cfg.cols } else {
        // aspect: grid width/height in cells = aspect
        let c = ((n as f64 * cfg.py as f64 / cfg.px as f64) * cfg.aspect).sqrt().ceil() as usize; c.max(2) };
    let rows = (n + cols - 1) / cols;
    let mut rom = FixedPart { name: "rom", kind: 2, abits: nl.rom_abits, rot: cfg.rom_rot, x: 0, y: 0, w: 0, h: 0 };
    let mut arm = FixedPart { name: "arm", kind: 3, abits: 0, rot: cfg.arm_rot, x: 0, y: 0, w: 0, h: 0 };
    let (bw, bh) = base_dims(2, rom.abits); let (rw, rh) = rot_dims(bw, bh, rom.rot); rom.w = rw; rom.h = rh;
    let (bw, bh) = base_dims(3, 0); let (aw, ah) = rot_dims(bw, bh, arm.rot); arm.w = aw; arm.h = ah;
    let gridw = cols as i32 * cfg.px; let gridh = rows as i32 * cfg.py;
    let mut ram = if nl.ram_abits > 0 {
        let mut r = FixedPart { name: "ram", kind: 4, abits: nl.ram_abits, rot: cfg.ram_rot, x: 0, y: 0, w: 0, h: 0 };
        let (bw, bh) = base_dims(4, r.abits); let (w, h) = rot_dims(bw, bh, r.rot); r.w = w; r.h = h; Some(r) } else { None };
    let top_h = rom.h.max(arm.h) + cfg.gap + cfg.edge;
    let bot_h = ram.as_ref().map(|r| r.h + cfg.gap + cfg.edge).unwrap_or(cfg.gap);
    let w = (cfg.ml + gridw + cfg.mr).max(cfg.ml + rom.w + 2 + arm.w + cfg.mr).max(ram.as_ref().map(|r| r.w + cfg.ml + cfg.mr).unwrap_or(0));
    let h = top_h + gridh + bot_h;
    rom.x = cfg.ml; rom.y = cfg.edge;
    arm.x = cfg.ml + rom.w + 2; arm.y = cfg.edge;
    if let Some(r) = ram.as_mut() { r.x = cfg.ml; r.y = h - r.h - cfg.edge; }
    Board { w, h, gx0: cfg.ml, gy0: top_h, cols, rows, rom, arm, ram }
}

// ---------------------------------------------------------------- placement (simulated annealing on a site grid)
struct Term { node: i32, dx: i32, dy: i32 }
fn anneal(nl: &Netlist, b: &Board, cfg: &Cfg, rng: &mut Rng) -> Vec<usize> {
    let n = nl.kind.len(); let sites = b.cols * b.rows;
    // nets: one per driver
    let mut net_of: HashMap<Drv, usize> = HashMap::new();
    let mut nets: Vec<Vec<Term>> = vec![];
    let mut fixed_bb: Vec<(i32, i32, i32, i32)> = vec![];       // bbox of fixed terminals (xmin,ymin,xmax,ymax); empty = (MAX..)
    let mut get = |d: Drv, nets: &mut Vec<Vec<Term>>, fb: &mut Vec<(i32, i32, i32, i32)>, b: &Board| -> usize {
        *net_of.entry(d).or_insert_with(|| {
            nets.push(vec![]); fb.push((i32::MAX, i32::MAX, i32::MIN, i32::MIN));
            let id = nets.len() - 1;
            match d { Drv::Node(k) => nets[id].push(Term { node: k as i32, dx: 1, dy: 0 }),
                      _ => { let c = driver_cell(b, &[], d); let f = &mut fb[id]; *f = (f.0.min(c.0), f.1.min(c.1), f.2.max(c.0), f.3.max(c.1)); } }
            id })
    };
    for k in 0..n { for (p, s) in nl.ins[k].iter().enumerate() { if let Some((d, _)) = s {
        let id = get(*d, &mut nets, &mut fixed_bb, b); nets[id].push(Term { node: k as i32, dx: 0, dy: p as i32 }); } } }
    for (name, s) in &nl.ports { if let Some((d, _)) = s {
        let id = get(*d, &mut nets, &mut fixed_bb, b); let c = port_cell(b, name, nl);
        let f = &mut fixed_bb[id]; *f = (f.0.min(c.0), f.1.min(c.1), f.2.max(c.0), f.3.max(c.1)); } }
    let mut node_nets: Vec<Vec<usize>> = vec![vec![]; n];
    for (i, t) in nets.iter().enumerate() { for x in t { if x.node >= 0 { if node_nets[x.node as usize].last() != Some(&i) { node_nets[x.node as usize].push(i); } } } }
    let mut site_of: Vec<usize> = (0..n).collect();
    // random initial
    for i in (1..n).rev() { let j = rng.below(i + 1); site_of.swap(i, j); }
    let mut node_at: Vec<usize> = vec![usize::MAX; sites];
    for k in 0..n { node_at[site_of[k]] = k; }
    let pos = |s: usize| -> (i32, i32) { (b.gx0 + (s % b.cols) as i32 * cfg.px, b.gy0 + (s / b.cols) as i32 * cfg.py) };
    let net_cost = |i: usize, site_of: &Vec<usize>| -> f64 {
        let mut bb = fixed_bb[i];
        for t in &nets[i] { let p = pos(site_of[t.node as usize]); let (x, y) = (p.0 + t.dx, p.1 + t.dy);
            bb.0 = bb.0.min(x); bb.1 = bb.1.min(y); bb.2 = bb.2.max(x); bb.3 = bb.3.max(y); }
        ((bb.2 - bb.0) + (bb.3 - bb.1)) as f64 };
    let mut costs: Vec<f64> = (0..nets.len()).map(|i| net_cost(i, &site_of)).collect();
    let mut total: f64 = costs.iter().sum();
    let mut try_move = |rng: &mut Rng, site_of: &mut Vec<usize>, node_at: &mut Vec<usize>, costs: &mut Vec<f64>, total: &mut f64, t: f64, rlim: i32, dry: bool| -> (bool, f64) {
        let a = rng.below(n); let sa = site_of[a];
        let (ax, ay) = ((sa % b.cols) as i32, (sa / b.cols) as i32);
        let nx = (ax + rng.below((2 * rlim + 1) as usize) as i32 - rlim).clamp(0, b.cols as i32 - 1);
        let ny = (ay + rng.below((2 * rlim + 1) as usize) as i32 - rlim).clamp(0, b.rows as i32 - 1);
        let sb = ny as usize * b.cols + nx as usize; if sb == sa { return (false, 0.0); }
        let o = node_at[sb];
        site_of[a] = sb; if o != usize::MAX { site_of[o] = sa; }
        let mut touched: Vec<usize> = node_nets[a].clone(); if o != usize::MAX { for &x in &node_nets[o] { if !touched.contains(&x) { touched.push(x); } } }
        let newc: Vec<f64> = touched.iter().map(|&i| net_cost(i, site_of)).collect();
        let delta: f64 = touched.iter().zip(&newc).map(|(&i, &c)| c - costs[i]).sum();
        let acc = dry || delta <= 0.0 || (t > 0.0 && rng.f() < (-delta / t).exp());
        if acc && !dry { for (&i, &c) in touched.iter().zip(&newc) { costs[i] = c; } *total += delta; node_at[sb] = a; node_at[sa] = o; (true, delta) }
        else { site_of[a] = sa; if o != usize::MAX { site_of[o] = sb; } (acc, delta) }
    };
    // initial temperature from random-move deltas
    let mut ds = vec![]; for _ in 0..2000 { let (_, d) = try_move(rng, &mut site_of, &mut node_at, &mut costs, &mut total, 0.0, b.cols.max(b.rows) as i32, true); ds.push(d); }
    let mean = ds.iter().sum::<f64>() / ds.len() as f64; let sd = (ds.iter().map(|d| (d - mean) * (d - mean)).sum::<f64>() / ds.len() as f64).sqrt();
    let mut t = 12.0 * sd; let mut rlim = b.cols.max(b.rows) as f64;
    let inner = ((n as f64).powf(1.33) * 2.0 * cfg.effort) as usize + 1000;
    let start = Instant::now();
    eprintln!("anneal: {n} nodes {} nets, grid {}x{}, T0 {:.1}, {} moves/temp, cost {:.0}", nets.len(), b.cols, b.rows, t, inner, total);
    loop {
        let mut acc = 0usize;
        for _ in 0..inner { let (ok, _) = try_move(rng, &mut site_of, &mut node_at, &mut costs, &mut total, t, rlim.round() as i32, false); if ok { acc += 1; } }
        let ar = acc as f64 / inner as f64;
        rlim = (rlim * (1.0 - 0.44 + ar)).clamp(1.0, b.cols.max(b.rows) as f64);
        let alpha = if ar > 0.96 { 0.5 } else if ar > 0.8 { 0.9 } else if ar > 0.15 { 0.95 } else { 0.8 };
        t *= alpha;
        if t < 0.005 * total / nets.len() as f64 { break; }
    }
    // greedy quench
    for _ in 0..inner { try_move(rng, &mut site_of, &mut node_at, &mut costs, &mut total, 0.0, 2, false); }
    eprintln!("anneal done: cost {:.0} in {:.1}s", total, start.elapsed().as_secs_f64());
    site_of
}

// ---------------------------------------------------------------- routing
const SC: i32 = 16;
struct Router<'a> { w: usize, h: usize, cost_via: i32, cost_turn: i32,
    owner: Vec<u32>,          // static pad owner per (layer, cell): 0 free, else net+1 (pads and open pins)
    sinkpad: Vec<i32>,        // sink id at pad cell, -1 none
    occ: Vec<u16>, hist: Vec<f32>, pres: f32,
    stamp: u32, seen: Vec<u32>, dist: Vec<i32>, prev: Vec<u32>,
    tree: Vec<u32>, tstamp: u32, _p: std::marker::PhantomData<&'a ()> }

struct NetR { sinks: Vec<usize>, driver_cell: (i32, i32), cells: Vec<u32>, paths: Vec<(usize, Vec<u32>)> }   // paths: (sink, states)

fn run(nl: &Netlist, cfg: &Cfg, out: &str) {
    let mut rng = Rng(cfg.seed.wrapping_mul(0x9E3779B97F4A7C15) | 1);
    let b = make_board(nl, cfg);
    let n = nl.kind.len();
    let site_of = anneal(nl, &b, cfg, &mut rng);
    let pos: Vec<(i32, i32)> = (0..n).map(|k| { let s = site_of[k]; (b.gx0 + (s % b.cols) as i32 * cfg.px, b.gy0 + (s / b.cols) as i32 * cfg.py) }).collect();
    let (w, h) = (b.w as usize, b.h as usize);
    let cell = |l: usize, x: i32, y: i32| -> usize { (l * h + y as usize) * w + x as usize };
    // nets and sinks
    struct Sink { snk: Snk, cell: (i32, i32), late: u8, net: usize }
    let mut sinks: Vec<Sink> = vec![]; let mut netd: HashMap<Drv, usize> = HashMap::new(); let mut nets: Vec<NetR> = vec![]; let mut netdrv: Vec<Drv> = vec![];
    let mut owner = vec![0u32; 2 * w * h]; let mut sinkpad = vec![-1i32; 2 * w * h];
    let mut next_single = 0u32;
    let mut stamp_pad = |owner: &mut Vec<u32>, c: (i32, i32), id: u32| { for l in 0..2 { let i = cell(l, c.0, c.1); assert!(owner[i] == 0, "pad overlap at {:?}", c); owner[i] = id; } };
    // driver nets first so that net ids are stable: id+1 is the owner tag
    let mut order: Vec<Drv> = vec![];
    for k in 0..n { for s in nl.ins[k].iter().flatten() { if !netd.contains_key(&s.0) { netd.insert(s.0, order.len()); order.push(s.0); } } }
    for (_, s) in &nl.ports { if let Some(s) = s { if !netd.contains_key(&s.0) { netd.insert(s.0, order.len()); order.push(s.0); } } }
    for d in &order { nets.push(NetR { sinks: vec![], driver_cell: driver_cell(&b, &pos, *d), cells: vec![], paths: vec![] }); netdrv.push(*d); }
    let nnets = nets.len() as u32;
    for (i, d) in order.iter().enumerate() { stamp_pad(&mut owner, nets[i].driver_cell, i as u32 + 1); let _ = d; }
    // nodes whose output has no sink still own their pad: give it a singleton id
    let mut driven: Vec<bool> = vec![false; n]; for d in &order { if let Drv::Node(k) = d { driven[*k] = true; } }
    next_single = nnets + 1;
    for k in 0..n { if !driven[k] { let c = out_of_node(pos[k].0, pos[k].1); stamp_pad(&mut owner, c, next_single); next_single += 1; } }
    // unused fixed-part pins are pads as well
    let mut used_fixed: std::collections::HashSet<(i32, i32)> = Default::default();
    for k in 0..n { for (p, s) in nl.ins[k].iter().enumerate() {
        let c = pin_of_node(nl.kind[k], pos[k].0, pos[k].1, p);
        match s { Some((d, late)) => { let id = netd[d]; stamp_pad(&mut owner, c, id as u32 + 1);
                    sinks.push(Sink { snk: Snk::NodePin(k, p), cell: c, late: *late, net: id }); }
                  None => { stamp_pad(&mut owner, c, next_single); next_single += 1; } } } }
    for (pi, (name, s)) in nl.ports.iter().enumerate() { let c = port_cell(&b, name, nl);
        if let Some((d, late)) = s { let id = netd[d]; stamp_pad(&mut owner, c, id as u32 + 1);
            sinks.push(Sink { snk: Snk::Port(pi), cell: c, late: *late, net: id }); }
        used_fixed.insert(c); }
    // remaining pins of fixed parts (unused ones) become blocked singleton pads
    let mut fixed_pins: Vec<(i32, i32)> = vec![];
    for j in 0..8 { fixed_pins.push(b.rom.cell(1, j)); }
    for i in 0..nl.rom_abits as i32 { fixed_pins.push(b.rom.cell(0, i)); }
    for i in 0..4 { fixed_pins.push(b.arm.cell(0, i)); } fixed_pins.push(b.arm.cell(0, 4)); for j in 0..8 { fixed_pins.push(b.arm.cell(1, j)); }
    if let Some(r) = &b.ram { let a = nl.ram_abits as i32; for c in 0..8 { fixed_pins.push(r.cell(1, c)); } for k in 0..(a + 9) { fixed_pins.push(r.cell(0, k)); } }
    for c in fixed_pins { if owner[cell(0, c.0, c.1)] == 0 { stamp_pad(&mut owner, c, next_single); next_single += 1; } }
    for (si, s) in sinks.iter().enumerate() { sinkpad[cell(0, s.cell.0, s.cell.1)] = si as i32; sinkpad[cell(1, s.cell.0, s.cell.1)] = si as i32; nets[s.net].sinks.push(si); }
    // sink order within a net: normal by distance to driver, then EN (late 1), then RUN (late 2)
    for net in nets.iter_mut() { let dc = net.driver_cell;
        net.sinks.sort_by_key(|&si| (sinks[si].late, (sinks[si].cell.0 - dc.0).abs() + (sinks[si].cell.1 - dc.1).abs())); }
    eprintln!("route: board {}x{}, {} nets, {} sinks", w, h, nets.len(), sinks.len());
    let t0 = Instant::now();
    let nstates = 2 * w * h * 5;
    let mut r = Router { w, h, cost_via: cfg.via * SC, cost_turn: cfg.turn * SC, owner, sinkpad, occ: vec![0; 2 * w * h], hist: vec![0.0; 2 * w * h], pres: 0.5,
        stamp: 0, seen: vec![0; nstates], dist: vec![0; nstates], prev: vec![u32::MAX; nstates], tree: vec![0; 2 * w * h], tstamp: 0, _p: Default::default() };
    // net order: big nets first
    let mut ord: Vec<usize> = (0..nets.len()).collect();
    ord.sort_by_key(|&i| Reverse(nets[i].sinks.len()));
    let mut ok = false;
    let mut best_over = usize::MAX; let mut stagn = 0usize; let mut hot: Vec<bool> = vec![false; 2 * w * h];
    for it in 0..cfg.iters {
        let mut rerouted = 0;
        let widen = stagn >= 6;
        if widen { for v in hot.iter_mut() { *v = false; }
            for i in 0..r.occ.len() { if r.occ[i] > 1 { let rem = i % (w * h); let (x, y) = ((rem % w) as i32, (rem / w) as i32);
                for dy in -2..=2i32 { for dx in -2..=2i32 { let (nx, ny) = (x + dx, y + dy); if nx >= 0 && ny >= 0 && nx < w as i32 && ny < h as i32 { for l in 0..2 { hot[(l * h + ny as usize) * w + nx as usize] = true; } } } } } } }
        if it > 0 { for i in (1..ord.len()).rev() { let j = rng.below(i + 1); ord.swap(i, j); } }
        for &ni in &ord {
            if it > 0 && !(if widen { nets[ni].cells.iter().any(|&c| hot[c as usize]) } else { net_congested(&r, &nets[ni]) }) { continue; }
            rip(&mut r, &mut nets[ni]); route_net(&mut r, &mut nets[ni], &sinks.iter().map(|s| (s.cell, s.late)).collect::<Vec<_>>(), ni);
            rerouted += 1;
        }
        let over = r.occ.iter().filter(|&&o| o > 1).count();
        eprintln!("  iter {it}: rerouted {rerouted}, overused cells {over}, pres {:.1} ({:.1}s)", r.pres, t0.elapsed().as_secs_f64());
        if over == 0 { ok = true; break; }
        if over < best_over { best_over = over; stagn = 0; } else { stagn += 1; if stagn > 40 { stagn = 6; } }
        for i in 0..r.occ.len() { if r.occ[i] > 1 { r.hist[i] += 2.0; } }
        r.pres = (r.pres * 1.4).min(40.0);
    }
    if !ok { eprintln!("ROUTING FAILED");
        let mut v: Vec<(usize, usize, usize)> = vec![]; for i in 0..r.occ.len() { if r.occ[i] > 1 { let rem = i % (w * h); v.push((i / (w * h), rem % w, rem / w)); } }
        for q in v.iter().take(60) { eprint!("({},{},{}) ", q.0, q.1, q.2); } eprintln!();
        for q in v.iter().take(8) { for ol in 0..2 { let c2 = (ol * h + q.2) * w + q.1; let mut wh = vec![]; for (ni, net) in nets.iter().enumerate() { if net.cells.contains(&(c2 as u32)) { wh.push(format!("{:?}", netdrv[ni])); } } eprintln!("    layer {} at {},{}: {}", ol, q.1, q.2, wh.join(",")); }
            let c = (q.0 * h + q.2) * w + q.1; let mut who = vec![]; for (ni, net) in nets.iter().enumerate() { if net.cells.contains(&(c as u32)) { who.push(format!("{:?}(sinks {}, owner-pad {})", netdrv[ni], net.sinks.len(), r.owner[c])); } } eprintln!("  cell {:?}: {}", q, who.join(" | ")); }
        eprintln!("board {}x{} grid x {}..{} y {}..{}", w, h, b.gx0, b.gx0 + b.cols as i32 * cfg.px, b.gy0, b.gy0 + b.rows as i32 * cfg.py);
        std::process::exit(2); }
    // output
    let mut o = String::new();
    o += &format!("dims {} {} px {} py {} cols {} rows {}\n", w, h, cfg.px, cfg.py, b.cols, b.rows);
    for p in [&b.rom, &b.arm].into_iter().chain(b.ram.iter()) { o += &format!("part {} {} {} {} {}\n", p.name, p.x, p.y, p.rot, p.abits); }
    let mut at: Vec<usize> = vec![usize::MAX; b.cols * b.rows]; for k in 0..n { at[site_of[k]] = k; }
    for s in 0..b.cols * b.rows { let (x, y) = (b.gx0 + (s % b.cols) as i32 * cfg.px, b.gy0 + (s / b.cols) as i32 * cfg.py);
        if at[s] == usize::MAX { o += &format!("site {s} {x} {y} E -1\n"); } else { o += &format!("site {s} {x} {y} {} {}\n", nl.kind[at[s]] as char, at[s]); } }
    let dname = |d: Drv| -> String { match d { Drv::Node(k) => format!("n{}", site_of[k]), Drv::Rom(j) => format!("rom{j}"), Drv::Ramo(c) => format!("ramo{c}") } };
    let mut tracks = 0; let mut vias = 0; let mut cellsum = 0;
    for (ni, net) in nets.iter().enumerate() {
        for (si, st) in &net.paths {
            let s = &sinks[*si];
            let who = match s.snk { Snk::NodePin(k, p) => format!("n{} {}", site_of[k], p), Snk::Port(pi) => format!("{} 0", nl.ports[pi].0) };
            let mut pts: Vec<(i32, i32, usize)> = vec![];
            let dec = |st: u32| -> (usize, i32, i32) { let c = (st / 5) as usize; let l = c / (w * h); let rem = c % (w * h); (l, (rem % w) as i32, (rem / w) as i32) };
            let p: Vec<(usize, i32, i32)> = st.iter().map(|&s| dec(s)).collect();
            cellsum += p.len();
            pts.push((p[0].1, p[0].2, p[0].0));
            for i in 1..p.len() {
                let (l, x, y) = p[i]; let (pl, px_, py_) = p[i - 1];
                if l != pl { vias += 1; pts.push((x, y, pl)); pts.push((x, y, l)); }
                else if i + 1 < p.len() {
                    let (nl_, nx, ny) = p[i + 1];
                    let straight = nl_ == l && ((nx - x) == (x - px_) && (ny - y) == (y - py_));
                    if !straight { pts.push((x, y, l)); }
                }
            }
            let last = p[p.len() - 1]; pts.push((last.1, last.2, last.0));
            pts.dedup();
            for i in 1..pts.len() { if pts[i].2 == pts[i - 1].2 && (pts[i].0 != pts[i - 1].0 || pts[i].1 != pts[i - 1].1) { tracks += 1; } }
            o += &format!("sink {} {} {} {} :", who, s.late, dname(netdrv[ni]), 0);
            for q in &pts { o += &format!(" {},{},{}", q.0, q.1, q.2); }
            o += "\n";
        }
    }
    fs::write(out, o).unwrap();
    // extent of copper
    eprintln!("done: {} tracks {} vias, path cells {}, route time {:.1}s, board {}x{} = {} cells for {} nodes ({:.1}/node)",
        tracks, vias, cellsum, t0.elapsed().as_secs_f64(), w, h, w * h, n, (w * h) as f64 / n as f64);
}

fn net_congested(r: &Router, net: &NetR) -> bool { net.cells.iter().any(|&c| r.occ[c as usize] > 1) }
fn rip(r: &mut Router, net: &mut NetR) { for &c in &net.cells { r.occ[c as usize] -= 1; } net.cells.clear(); net.paths.clear(); }

fn route_net(r: &mut Router, net: &mut NetR, sinks: &[((i32, i32), u8)], ni: usize) {
    let (w, h) = (r.w, r.h);
    let cell = |l: usize, x: i32, y: i32| -> usize { (l * h + y as usize) * w + x as usize };
    r.tstamp += 1; let ts = r.tstamp;
    // tree = driver pad on both layers
    let mut tree_cells: Vec<u32> = vec![];
    let mut bb = (i32::MAX, i32::MAX, i32::MIN, i32::MIN);
    let mut add_tree = |r: &mut Router, c: usize, tree_cells: &mut Vec<u32>, bb: &mut (i32, i32, i32, i32)| {
        if r.tree[c] != ts { r.tree[c] = ts; tree_cells.push(c as u32); r.occ[c] += 1;
            let rem = c % (w * h); let (x, y) = ((rem % w) as i32, (rem / w) as i32);
            bb.0 = bb.0.min(x); bb.1 = bb.1.min(y); bb.2 = bb.2.max(x); bb.3 = bb.3.max(y); } };
    for l in 0..2 { add_tree(r, cell(l, net.driver_cell.0, net.driver_cell.1), &mut tree_cells, &mut bb); }
    let sink_list = net.sinks.clone();
    for si in sink_list {
        let (sc, _) = sinks[si];
        r.stamp += 1; let st = r.stamp;
        let mut heap: BinaryHeap<Reverse<(i32, i32, u32)>> = BinaryHeap::new();   // (f, g, state)
        let heur = |x: i32, y: i32| -> i32 { let dx = (bb.0 - x).max(0).max(x - bb.2); let dy = (bb.1 - y).max(0).max(y - bb.3); (dx + dy - 1).max(0) * SC };
        for l in 0..2 { let s = (cell(l, sc.0, sc.1) * 5 + 4) as u32; r.seen[s as usize] = st; r.dist[s as usize] = 0; r.prev[s as usize] = u32::MAX; heap.push(Reverse((heur(sc.0, sc.1), 0, s))); }
        let mut found: Option<u32> = None;
        while let Some(Reverse((_, g, s))) = heap.pop() {
            if r.dist[s as usize] != g || r.seen[s as usize] != st { continue; }
            let c = (s / 5) as usize; let dir = (s % 5) as usize;
            let l = c / (w * h); let rem = c % (w * h); let (x, y) = ((rem % w) as i32, (rem / w) as i32);
            if r.tree[c] == ts && dir != 4 { found = Some(s); break; }
            // planar moves
            for d in 0..4usize {
                let (dx, dy) = [(1, 0), (-1, 0), (0, 1), (0, -1)][d];
                let (nx, ny) = (x + dx, y + dy);
                if nx < 0 || ny < 0 || nx >= w as i32 || ny >= h as i32 { continue; }
                let nc = cell(l, nx, ny);
                if !passable(r, nc, ni, ts) { continue; }
                let mut cost = SC + (r.hist[nc] * SC as f32) as i32 + congestion(r, nc, ts);
                if dir < 4 && dir / 2 != d / 2 { cost += r.cost_turn; }
                let ns = (nc * 5 + d) as u32; let ng = g + cost;
                if r.seen[ns as usize] != st || r.dist[ns as usize] > ng { r.seen[ns as usize] = st; r.dist[ns as usize] = ng; r.prev[ns as usize] = s; heap.push(Reverse((ng + heur(nx, ny), ng, ns))); }
            }
            // via (not on pads, which already join the layers)
            if r.owner[c] == 0 {
                let ol = 1 - l; let nc = cell(ol, x, y);
                if passable(r, nc, ni, ts) {
                    let cost = r.cost_via + (r.hist[nc] * SC as f32) as i32 + congestion(r, nc, ts);
                    let ns = (nc * 5 + 4) as u32; let ng = g + cost;
                    if r.seen[ns as usize] != st || r.dist[ns as usize] > ng { r.seen[ns as usize] = st; r.dist[ns as usize] = ng; r.prev[ns as usize] = s; heap.push(Reverse((ng + heur(x, y), ng, ns))); }
                }
            }
        }
        let mut s = match found { Some(s) => s, None => { eprintln!("no path for sink {si} of net {ni}"); std::process::exit(3) } };
        let mut path: Vec<u32> = vec![];
        loop { path.push(s); let p = r.prev[s as usize]; if p == u32::MAX { break; } s = p; }
        path.reverse();       // from sink pad to the tree
        for &s in &path { add_tree(r, (s / 5) as usize, &mut tree_cells, &mut bb); }
        net.paths.push((si, path));
    }
    net.cells = tree_cells;
}

#[inline] fn passable(r: &Router, c: usize, ni: usize, ts: u32) -> bool {
    let o = r.owner[c];
    if o != 0 && o != ni as u32 + 1 { return false; }
    if o != 0 && r.sinkpad[c] >= 0 && r.tree[c] != ts { return false; }     // an unrouted sink pad of this net: not a through route
    // driver pads have owner = ni+1 and are in the tree; fine
    true }
#[inline] fn congestion(r: &Router, c: usize, ts: u32) -> i32 {
    let own = if r.tree[c] == ts { 1 } else { 0 };
    let others = r.occ[c] as i32 - own;
    if others > 0 { (r.pres * others as f32 * SC as f32 * 2.0) as i32 } else { 0 } }
