// eng2sim: cycle-level model of engine2 (port of engine2_model.py). usage: eng2sim ROWS.txt M OUT.bin   (writes pairs reg,val as bytes)
use std::io::{Write, BufWriter};
fn main() {
    let a: Vec<String> = std::env::args().collect();
    let words: Vec<u32> = std::fs::read_to_string(&a[1]).unwrap().split_whitespace().map(|s| s.parse().unwrap()).collect();
    let m: i64 = a[2].parse().unwrap();
    let w = words.len() as i64; let e0 = m - w + 1; let mask14: i64 = (1 << 14) - 1;
    let mut out = BufWriter::new(std::fs::File::create(&a[3]).unwrap());
    let (mut tok, mut started, mut t, mut rr, mut wreg): (i64, bool, i64, i64, u32) = (-1, false, 0, 0, 0);
    let (mut ma, mut mcap, mut me, mut mc, mut p2) = (false, false, false, false, false);
    let (mut ax, mut ay): (u32, u32) = (0, 0);
    let mut cyc: u64 = 0; let mut nw: u64 = 0;
    loop {
        let word = if tok >= 0 { words[tok as usize] } else { 0 };
        let d = word & 255; let reg = (word >> 8) & 15; let src = (word >> 12) & 7; let dfl = (word >> 15) & 1; let cpol = (word >> 16) & 1; let ccol = ((word >> 17) & 31) as usize; let ph = (word >> 22) & 3;
        let start = !started;
        let wrap = t == m; let last = rr == m;
        let wb = |i: u32| (wreg >> i) & 1;
        let cm = if ccol < 24 { (wreg >> ccol) & 1 } else { 1 };
        let cond_eq = cm == cpol;
        let isdata = wb(22) == 0 && wb(23) == 0;
        let ok_d = dfl == 0 || isdata;
        let pg = (dfl == 1) != p2;
        let cond_ok = cond_eq && ok_d && pg;
        let en = (ma && ph == 1) || (me && ph == 2 && cond_ok) || (mc && ph == 3);
        let mut data: u32 = 0; let mut sm9: u32 = 0;
        match src {
            0 => data = d,
            1 | 3 => { let v = rr + if src == 3 { 1 } else { 0 }; data = (((v & 63) as u32) << 2) | (d & 3); }
            2 | 4 => { let v = rr + if src == 4 { 1 } else { 0 }; data = (((((v >> 13) & 1) ^ 1) as u32) << 7) | (((v >> 6) & 127) as u32); }
            5 => { let op1 = if d & 1 == 1 { ay } else { ax }; let sel = (d >> 1) & 7;
                   let add = match sel { 0 => wreg & 511, 1 => (wreg >> 16) & 3, 2 => (wreg >> 9) & 63, _ => 0 };
                   sm9 = (op1 + add) & 511; data = sm9 & 255; }
            7 => { let op1 = if (reg >> 1) & 1 == 1 { ay } else { ax }; let add = if d & 1 == 1 { (wreg >> 9) & 63 } else { 0 };
                   sm9 = (op1 + add) & 511; data = (d & 0xFE) | (sm9 >> 8); }
            6 => { let sel = d & 3; data = if sel == 0 { (wb(18) | (wb(19) << 2)) as u32 } else if sel == 1 { (wb(9) | (wb(10) << 1)) as u32 } else if sel == 2 { wb(11) as u32 } else { 0 }; }
            _ => {}
        }
        if en { out.write_all(&[reg as u8, data as u8]).unwrap(); nw += 1; }
        let (mut nax, mut nay) = (ax, ay);
        if en && src == 5 && (d >> 4) & 1 == 1 { if d & 1 == 1 { nay = sm9 } else { nax = sm9 } }
        let capture = mcap && t == rr;
        let nwreg = if capture { word } else { wreg };
        let mut ntok = if tok >= 0 && tok < w - 1 { tok + 1 } else { -1 };
        if tok == w - 1 || start { ntok = 0 }
        let nt = if start || wrap { e0 } else { t + 1 };
        let p2start = me && wrap && last && !p2;
        let adv = me && wrap && !last;
        let ldrr = start || p2start;
        let nrr = if ldrr { e0 } else if adv { rr + 1 } else { rr };
        let na = if start { true } else { ma && !wrap };
        let ncap = (ma && wrap) || adv || p2start || (mcap && !wrap);
        let ne = (mcap && wrap) || (me && !wrap);
        let nc = (me && wrap && last && p2) || (mc && !wrap);
        let done = started && !(ma || mcap || me || mc) && cyc > 0;
        if done && !start { break; }
        started = true; t = nt & mask14; rr = nrr & mask14; wreg = nwreg; tok = ntok;
        ma = na; mcap = ncap; me = ne; mc = nc;
        p2 = p2 || p2start; ax = nax; ay = nay;
        cyc += 1;
    }
    out.flush().unwrap();
    println!("cycles {} writes {}", cyc, nw);
}
