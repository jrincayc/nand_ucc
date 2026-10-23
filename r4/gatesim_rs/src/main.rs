//! gatesim -- dependency-free gate-level simulator of the nandgen CPU netlist (.nl) against a ROM image.
//! Semantics = tools/netsim.py = one RNDP tick: settle combinational logic (ROM/RAM reads combinational), then RAM write / arm write are
//! sampled, then every DFF latches its D.  Open inputs read 0.  `@n` (late) suffixes are layout hints and ignored.
//! usage: gatesim NL ROM.bin [--ticks N] [--stop-arm N] [--armlog F] [--dump-ram F] [--checkpoint F --every N] [--resume F] [--trace F]
//! Output on stderr: 'ticks T arm_writes N'.  Arm log lines are 'reg value' (decimal), the same format as rvemu --armlog.
use std::io::Write;

const NONE: u32 = u32::MAX;

struct Net {
    n: usize,
    a: Vec<u32>,           // input slot of each node (a for NAND, d for DFF)
    b: Vec<u32>,
    is_dff: Vec<bool>,
    val: Vec<u8>,          // [0..n) nodes, n..n+8 rom byte bits, n+8..n+16 ram data bits, n+16 constant 0
    pass1: Vec<u32>,       // NAND nodes in the address cones, topological
    pass2: Vec<u32>,       // all other NANDs, topological
    dffs: Vec<u32>,
    rom_addr: Vec<u32>, ram_addr: Vec<u32>, ram_din: Vec<u32>, arm_addr: Vec<u32>, ram_we: u32, arm_en: u32,
}

fn slot(tok: &str, n: usize) -> u32 {
    let t = tok.split('@').next().unwrap();
    if t == "open" { return (n + 16) as u32; }
    if let Some(r) = t.strip_prefix("ramo") { return (n + 8 + r.parse::<usize>().unwrap()) as u32; }
    if let Some(r) = t.strip_prefix("rom") { return (n + r.parse::<usize>().unwrap()) as u32; }
    if let Some(r) = t.strip_prefix('n') { return r.parse::<u32>().unwrap(); }
    panic!("bad token {}", tok);
}

fn load(path: &str) -> (Net, usize, usize) {
    let text = std::fs::read_to_string(path).expect("nl");
    let (mut rb, mut mb) = (0usize, 0usize);
    let mut nodes: Vec<(bool, String, String)> = vec![]; let mut ports: Vec<(String, String)> = vec![];
    for l in text.lines() {
        let w: Vec<&str> = l.split_whitespace().collect();
        if w.is_empty() { continue; }
        match w[0] {
            "rom" => rb = w[1].parse().unwrap(), "ram" => mb = w[1].parse().unwrap(),
            "n" => nodes.push((w[2] == "D", w[3].to_string(), if w.len() > 4 { w[4].to_string() } else { String::new() })),
            "p" => ports.push((w[1].to_string(), w[2].to_string())),
            _ => {}
        }
    }
    let n = nodes.len();
    let mut a = vec![0u32; n]; let mut b = vec![0u32; n]; let mut is_dff = vec![false; n];
    for (i, (d, x, y)) in nodes.iter().enumerate() {
        is_dff[i] = *d; a[i] = slot(x, n); b[i] = if *d { NONE } else { slot(y, n) };
    }
    let port = |name: &str| -> u32 { slot(&ports.iter().find(|p| p.0 == name).unwrap_or_else(|| panic!("port {}", name)).1, n) };
    let rom_addr: Vec<u32> = (0..rb).map(|i| port(&format!("rom_addr{}", i))).collect();
    let ram_addr: Vec<u32> = (0..mb).map(|i| port(&format!("ram_addr{}", i))).collect();
    let ram_din: Vec<u32> = (0..8).map(|i| port(&format!("ram_din{}", i))).collect();
    let arm_addr: Vec<u32> = (0..4).map(|i| port(&format!("arm_addr{}", i))).collect();
    let (ram_we, arm_en) = (port("ram_we"), port("arm_en"));
    // topological order of NANDs (iterative DFS); DFFs and inputs are sources
    let mut state = vec![0u8; n]; let mut order: Vec<u32> = vec![];
    for r in 0..n {
        if is_dff[r] || state[r] != 0 { continue; }
        let mut st: Vec<(usize, u8)> = vec![(r, 0)];
        while let Some((x, ph)) = st.pop() {
            if ph == 0 {
                if state[x] != 0 { continue; }
                state[x] = 1; st.push((x, 1));
                for s in [a[x], b[x]] { let s = s as usize; if s < n && !is_dff[s] && state[s] == 0 { st.push((s, 0)); } }
            } else { state[x] = 2; order.push(x as u32); }
        }
    }
    // cone of the address ports
    let mut cone = vec![false; n]; let mut stack: Vec<usize> = vec![];
    for &p in rom_addr.iter().chain(ram_addr.iter()) { if (p as usize) < n { stack.push(p as usize); } }
    while let Some(x) = stack.pop() {
        if cone[x] || is_dff[x] { continue; }
        cone[x] = true;
        for s in [a[x], b[x]] { if (s as usize) < n { stack.push(s as usize); } else { panic!("address depends on an input slot"); } }
    }
    let pass1 = order.iter().cloned().filter(|&x| cone[x as usize]).collect();
    let pass2 = order.iter().cloned().filter(|&x| !cone[x as usize]).collect();
    let dffs = (0..n as u32).filter(|&i| is_dff[i as usize]).collect();
    (Net { n, a, b, is_dff, val: vec![0; n + 17], pass1, pass2, dffs, rom_addr, ram_addr, ram_din, arm_addr, ram_we, arm_en }, rb, mb)
}

impl Net {
    #[inline] fn eval(&mut self, list_is_1: bool) {
        let Net { a, b, val, pass1, pass2, .. } = self;
        let list = if list_is_1 { &*pass1 } else { &*pass2 };
        for &x in list.iter() { let x = x as usize; val[x] = 1 ^ (val[a[x] as usize] & val[b[x] as usize]); }
    }
    fn bus(&self, s: &[u32]) -> usize { s.iter().enumerate().fold(0, |acc, (i, &p)| acc | (self.val[p as usize] as usize) << i) }
}

fn put_u64(o: &mut Vec<u8>, v: u64) { o.extend_from_slice(&v.to_le_bytes()); }

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 { eprintln!("usage: gatesim NL ROM.bin [--ticks N] [--stop-arm N] [--armlog F] [--dump-ram F] [--checkpoint F --every N] [--resume F] [--trace F]"); std::process::exit(1); }
    let (mut net, rb, mb) = load(&args[1]);
    let mut rom = std::fs::read(&args[2]).expect("rom"); rom.resize(1 << rb, 0);
    let (mut ticks, mut stop_arm) = (u64::MAX, u64::MAX); let (mut armlog, mut dump, mut ck, mut resume) = (None, None, None, None); let mut every = 0u64;
    let mut i = 3;
    while i < args.len() {
        let v = args.get(i + 1).cloned().unwrap_or_default();
        match args[i].as_str() {
            "--ticks" => ticks = v.parse().unwrap(), "--stop-arm" => stop_arm = v.parse().unwrap(), "--armlog" => armlog = Some(v), "--dump-ram" => dump = Some(v),
            "--checkpoint" => ck = Some(v), "--every" => every = v.parse().unwrap(), "--resume" => resume = Some(v), "--trace" => {}
            x => panic!("unknown option {}", x),
        }
        i += 2;
    }
    let mut ram = vec![0u8; 1 << mb];
    let mut arm: Vec<(u8, u8)> = vec![]; let mut t: u64 = 0;
    if let Some(f) = &resume {
        let d = std::fs::read(f).expect("resume"); assert_eq!(&d[0..8], b"GSIMCK01");
        let rd = |o: usize| u64::from_le_bytes(d[o..o + 8].try_into().unwrap());
        t = rd(8); let na = rd(16) as usize; let nd = rd(24) as usize; assert_eq!(nd, net.dffs.len()); assert_eq!(rd(32) as usize, ram.len());
        let mut o = 40;
        for &x in net.dffs.clone().iter() { net.val[x as usize] = d[o]; o += 1; }
        let rl = ram.len(); ram.copy_from_slice(&d[o..o + rl]); o += rl;
        for _ in 0..na { arm.push((d[o], d[o + 1])); o += 2; }
        eprintln!("resumed at tick {} with {} arm writes", t, arm.len());
    }
    let t_start = std::time::Instant::now(); let t0 = t;
    let rmask = (1usize << rb) - 1;
    let inputs = net.n;
    let mut last_ck = t;
    while t < ticks && (arm.len() as u64) < stop_arm {
        // pass 1: addresses (depend on DFFs only); inputs are not read there
        net.eval(true);
        let ra = net.bus(&net.ram_addr);
        let rv = rom[net.bus(&net.rom_addr) & rmask]; let mv = ram[ra];
        for j in 0..8 { net.val[inputs + j] = (rv >> j) & 1; net.val[inputs + 8 + j] = (mv >> j) & 1; }
        net.eval(false);
        let d = net.bus(&net.ram_din) as u8;
        if net.val[net.ram_we as usize] != 0 { ram[ra] = d; }
        if net.val[net.arm_en as usize] != 0 { arm.push((net.bus(&net.arm_addr) as u8, d)); }
        // latch
        let mut tmp = [0u8; 256]; let nd = net.dffs.len(); assert!(nd <= 256);
        for (k, &x) in net.dffs.iter().enumerate() { tmp[k] = net.val[net.a[x as usize] as usize]; }
        for (k, &x) in net.dffs.iter().enumerate() { net.val[x as usize] = tmp[k]; }
        t += 1;
        if every > 0 && t - last_ck >= every {
            if let Some(f) = &ck {
                let mut o: Vec<u8> = b"GSIMCK01".to_vec(); put_u64(&mut o, t); put_u64(&mut o, arm.len() as u64); put_u64(&mut o, nd as u64); put_u64(&mut o, ram.len() as u64);
                for &x in net.dffs.iter() { o.push(net.val[x as usize]); }
                o.extend_from_slice(&ram); for &(a, v) in arm.iter() { o.push(a); o.push(v); }
                std::fs::write(format!("{}.tmp", f), &o).unwrap(); std::fs::rename(format!("{}.tmp", f), f).unwrap();
                eprintln!("checkpoint at tick {} ({} arm writes, {:.0} ticks/s)", t, arm.len(), (t - t0) as f64 / t_start.elapsed().as_secs_f64());
            }
            last_ck = t;
        }
    }
    eprintln!("ticks {} arm_writes {} ({:.2} s, {:.0} ticks/s)", t, arm.len(), t_start.elapsed().as_secs_f64(), (t - t0) as f64 / t_start.elapsed().as_secs_f64());
    if let Some(f) = armlog { let mut w = std::io::BufWriter::new(std::fs::File::create(f).unwrap()); for &(a, v) in &arm { writeln!(w, "{} {}", a, v).unwrap(); } }
    if let Some(f) = dump { std::fs::write(f, &ram).unwrap(); }
}
