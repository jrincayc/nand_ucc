//! engsim -- dependency-free gate-level simulator of the E4 engine netlist (.nl, R4 format) with an abstract token-ring plane.
//! usage: engsim ENGINE.nl ROWS.txt [--cycles N] [--armlog F] [--dump-state F]
//! ROWS.txt: one decimal instruction word (24 bits, column j = bit j) per row.  The plane is modelled as the real ring: token position, Q_0' = D0 (port ram_addr0),
//! qlast = Q_{W-1}; the word under the token is presented on x0..x23.  Arm semantics: cycle k's outputs are executed in tick k+1 (written to the log in order).
use std::io::Write;
fn main() {
    let a: Vec<String> = std::env::args().collect();
    let nl = std::fs::read_to_string(&a[1]).unwrap();
    let rows: Vec<u32> = std::fs::read_to_string(&a[2]).unwrap().split_whitespace().map(|s| s.parse().unwrap()).collect();
    let w = rows.len();
    let mut cycles: u64 = 10_000_000; let mut armlog: Option<String> = None;
    let mut i = 3; while i < a.len() { match a[i].as_str() { "--cycles" => { cycles = a[i + 1].parse().unwrap(); i += 2 } "--armlog" => { armlog = Some(a[i + 1].clone()); i += 2 } _ => panic!("arg") } }
    // tokens: >=0 internal node, -1 open, -(100+k) external x_k
    let mut kind: Vec<u8> = vec![]; let mut fa: Vec<i32> = vec![]; let mut fb: Vec<i32> = vec![];
    let mut ports: Vec<(String, i32)> = vec![];
    let tok = |s: &str| -> i32 { let b = s.split('@').next().unwrap(); if b == "open" { -1 } else if b.starts_with('x') { -(100 + b[1..].parse::<i32>().unwrap()) } else { b[1..].parse().unwrap() } };
    for line in nl.lines() {
        let w: Vec<&str> = line.split_whitespace().collect(); if w.is_empty() { continue }
        if w[0] == "n" { let idx: usize = w[1].parse().unwrap(); assert_eq!(idx, kind.len()); kind.push(if w[2] == "D" { 1 } else { 0 }); fa.push(tok(w[3])); fb.push(if w.len() > 4 { tok(w[4]) } else { -1 }); }
        else if w[0] == "p" { ports.push((w[1].to_string(), tok(w[2]))); }
    }
    let n = kind.len();
    let mut val = vec![0u8; n]; // DFF state at start; NAND values computed
    let order: Vec<usize> = (0..n).filter(|&i| kind[i] == 0).collect();
    let dffs: Vec<usize> = (0..n).filter(|&i| kind[i] == 1).collect();
    let mut tokp: i64 = -1; // token position (-1 none)
    let mut out: Vec<(u32, u32)> = vec![]; let mut multi = 0u64;
    let get = |val: &Vec<u8>, t: i32, ext: &[u8; 25]| -> u8 { if t >= 0 { val[t as usize] } else if t == -1 { 0 } else { ext[(-t - 100) as usize] } };
    for cyc in 0..cycles {
        let word = if tokp >= 0 { rows[tokp as usize] } else { 0 };
        let mut ext = [0u8; 25]; for j in 0..24 { ext[j] = ((word >> j) & 1) as u8 } ext[24] = if tokp == w as i64 - 1 { 1 } else { 0 };
        for &i in &order { let x = get(&val, fa[i], &ext); let y = get(&val, fb[i], &ext); val[i] = 1 - (x & y); }
        // outputs
        let mut en = 0; let mut reg = 0u32; let mut data = 0u32; let mut d0 = 0;
        for (name, t) in &ports { let v = get(&val, *t, &ext) as u32; match name.as_str() {
            "arm_en" => en = v, "ram_addr0" => d0 = v,
            s if s.starts_with("arm_addr") => reg |= v << s[8..].parse::<u32>().unwrap(),
            s if s.starts_with("wdata") => data |= v << s[5..].parse::<u32>().unwrap(), _ => {} } }
        if en == 1 { out.push((reg, data)); }
        // next state
        let nd: Vec<u8> = dffs.iter().map(|&i| get(&val, fa[i], &ext)).collect();
        // the tie-high node n(tie) = NAND(open,open) = 1 is wired late: in simulation the run DFF D reads it as 1 (it is an ordinary node here)
        let mut next_tok: i64 = -1;
        if tokp >= 0 && (tokp as usize) < w - 1 { next_tok = tokp + 1 }
        if d0 == 1 { if next_tok >= 0 { multi += 1 } next_tok = 0 }
        tokp = next_tok;
        for (k, &i) in dffs.iter().enumerate() { val[i] = nd[k]; }
        if cyc % 50_000_000 == 49_999_999 { eprintln!("cycle {}", cyc + 1) }
    }
    eprintln!("cycles {} arm_writes {} double_tokens {}", cycles, out.len(), multi);
    if let Some(p) = armlog { let mut f = std::io::BufWriter::new(std::fs::File::create(p).unwrap()); for (r, d) in &out { writeln!(f, "{} {}", r, d).unwrap(); } }
}
