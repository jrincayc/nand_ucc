//! rvemu -- RV32EC emulator for the RNDP Replicator CPU (dependency free).  Semantics = tools/rvemu.py (normative).
//! usage: rvemu ROM.bin [--rom-bits N] [--ab N] [--ram-bytes N] [--max N] [--armlog FILE] [--trace FILE] [--dump-ram FILE] [--load-ram FILE] [--pc N]
//! Arm log: text, one "reg value" per line (decimal), in order issued.  Exit 0 on halt (jal x0,0), 2 on illegal, 3 on max reached.
use std::io::{Write, BufWriter};

fn sx(v: u32, bits: u32) -> i32 { let sh = 32 - bits; ((v << sh) as i32) >> sh }
fn bits(v: u32, hi: u32, lo: u32) -> u32 { (v >> lo) & ((1u32 << (hi - lo + 1)) - 1) }

fn expand(h: u32) -> Result<u32, String> {
    let op = h & 3; let f3 = bits(h, 15, 13);
    let rdp = |lo: u32| 8 + bits(h, lo + 2, lo);
    let i_ = |imm: u32, rs1: u32, f3: u32, rd: u32, opc: u32| ((imm & 0xFFF) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | opc;
    let r_ = |f7: u32, rs2: u32, rs1: u32, f3: u32, rd: u32, opc: u32| (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | opc;
    let s_ = |imm: u32, rs2: u32, rs1: u32, f3: u32, opc: u32| (bits(imm, 11, 5) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (bits(imm, 4, 0) << 7) | opc;
    let b_ = |imm: u32, rs2: u32, rs1: u32, f3: u32| (bits(imm, 12, 12) << 31) | (bits(imm, 10, 5) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (bits(imm, 4, 1) << 8) | (bits(imm, 11, 11) << 7) | 0x63;
    let j_ = |imm: u32, rd: u32| (bits(imm, 20, 20) << 31) | (bits(imm, 10, 1) << 21) | (bits(imm, 11, 11) << 20) | (bits(imm, 19, 12) << 12) | (rd << 7) | 0x6F;
    let u_ = |imm: u32, rd: u32| ((imm & 0xFFFFF) << 12) | (rd << 7) | 0x37;
    let ill = |s: &str| Err(s.to_string());
    if op == 0 {
        if f3 == 0 {
            let imm = (bits(h,10,7) << 6) | (bits(h,12,11) << 4) | (bits(h,5,5) << 3) | (bits(h,6,6) << 2);
            if imm == 0 { return ill("c.addi4spn imm 0"); }
            return Ok(i_(imm, 2, 0, rdp(2), 0x13));
        }
        let imm = (bits(h,5,5) << 6) | (bits(h,12,10) << 3) | (bits(h,6,6) << 2);
        if f3 == 2 { return Ok(i_(imm, rdp(7), 2, rdp(2), 0x03)); }
        if f3 == 6 { return Ok(s_(imm, rdp(2), rdp(7), 2, 0x23)); }
        return ill("quadrant 0 funct3");
    }
    if op == 1 {
        let rd = bits(h, 11, 7); let imm6 = sx((bits(h,12,12) << 5) | bits(h,6,2), 6) as u32;
        let jimm = || sx((bits(h,12,12) << 11) | (bits(h,8,8) << 10) | (bits(h,10,9) << 8) | (bits(h,6,6) << 7) | (bits(h,7,7) << 6) | (bits(h,2,2) << 5) | (bits(h,11,11) << 4) | (bits(h,5,3) << 1), 12) as u32;
        match f3 {
            0 => return Ok(i_(imm6, rd, 0, rd, 0x13)),
            1 => return Ok(j_(jimm(), 1)),
            2 => return Ok(i_(imm6, 0, 0, rd, 0x13)),
            3 => {
                if rd == 2 {
                    let imm = sx((bits(h,12,12) << 9) | (bits(h,4,3) << 7) | (bits(h,5,5) << 6) | (bits(h,2,2) << 5) | (bits(h,6,6) << 4), 10) as u32;
                    if imm == 0 { return ill("c.addi16sp 0"); }
                    return Ok(i_(imm, 2, 0, 2, 0x13));
                }
                if imm6 == 0 { return ill("c.lui 0"); }
                return Ok(u_(imm6, rd));
            }
            4 => {
                let r = rdp(7); let sh = (bits(h,12,12) << 5) | bits(h,6,2); let k = bits(h,11,10);
                if k == 0 || k == 1 {
                    if sh >> 5 != 0 { return ill("shift >= 32"); }
                    return Ok(i_(sh | if k == 1 { 0x400 } else { 0 }, r, 5, r, 0x13));
                }
                if k == 2 { return Ok(i_(imm6, r, 7, r, 0x13)); }
                if bits(h,12,12) != 0 { return ill("c.subw/addw"); }
                let s = bits(h,6,5);
                return Ok(r_(if s == 0 { 0x20 } else { 0 }, rdp(2), r, [0,4,6,7][s as usize], r, 0x33));
            }
            5 => return Ok(j_(jimm(), 0)),
            _ => {
                let imm = sx((bits(h,12,12) << 8) | (bits(h,6,5) << 6) | (bits(h,2,2) << 5) | (bits(h,11,10) << 3) | (bits(h,4,3) << 1), 9) as u32;
                return Ok(b_(imm, 0, rdp(7), if f3 == 6 { 0 } else { 1 }));
            }
        }
    }
    let rd = bits(h, 11, 7); let rs2 = bits(h, 6, 2);
    match f3 {
        0 => { if bits(h,12,12) != 0 { return ill("shift >= 32"); } Ok(i_(rs2, rd, 1, rd, 0x13)) }
        2 => { if rd == 0 { return ill("c.lwsp x0"); } Ok(i_((bits(h,3,2) << 6) | (bits(h,12,12) << 5) | (bits(h,6,4) << 2), 2, 2, rd, 0x03)) }
        4 => {
            if bits(h,12,12) == 0 {
                if rs2 == 0 { if rd == 0 { return ill("c.jr x0"); } return Ok(i_(0, rd, 0, 0, 0x67)); }
                return Ok(r_(0, rs2, 0, 0, rd, 0x33));
            }
            if rs2 == 0 { if rd == 0 { return ill("c.ebreak"); } return Ok(i_(0, rd, 0, 1, 0x67)); }
            Ok(r_(0, rs2, rd, 0, rd, 0x33))
        }
        6 => Ok(s_((bits(h,8,7) << 6) | (bits(h,12,9) << 2), rs2, 2, 2, 0x23)),
        _ => ill("quadrant 2 funct3"),
    }
}

struct M { rom: Vec<u8>, ram: Vec<u8>, rom_bits: u32, ab: u32, pc: u32, icount: u64, halted: bool, armlog: Vec<(u8, u8)>, armcount: u64 }

impl M {
    fn rom_base(&self) -> u32 { 1 << self.ab }
    fn pcm(&self) -> u32 { (1u32 << self.rom_bits) - 1 }
    fn amask(&self) -> u32 { (2u32 << self.ab) - 1 }
    fn rb(&self, a: u32) -> u8 {
        let a = a & self.amask();
        if a & self.rom_base() != 0 { let o = ((a - self.rom_base()) & self.pcm()) as usize; return if o < self.rom.len() { self.rom[o] } else { 0 }; }
        if (a >> 4) == ((self.rom_base() - 16) >> 4) { return 0; }
        if (a as usize) < self.ram.len() { self.ram[a as usize] } else { 0 }
    }
    fn wb(&mut self, a: u32, v: u8) {
        let a = a & self.amask();
        if a & self.rom_base() != 0 { return; }
        if (a >> 4) == ((self.rom_base() - 16) >> 4) { self.armcount += 1; self.armlog.push(((a & 15) as u8, v)); return; }
        if (a as usize) < self.ram.len() { self.ram[a as usize] = v; }
    }
    fn rd(&self, a: u32, n: u32) -> u32 { let mut v = 0u32; for i in 0..n { v |= (self.rb(a.wrapping_add(i)) as u32) << (8 * i); } v }
    fn wr(&mut self, a: u32, n: u32, v: u32) { for i in 0..n { self.wb(a.wrapping_add(i), (v >> (8 * i)) as u8); } }
    fn reg(&self, i: u32) -> u32 { if i == 0 { 0 } else { self.rd(4 * i, 4) } }
    fn setreg(&mut self, i: u32, v: u32) { if i != 0 { self.wr(4 * i, 4, v); } }
    fn step(&mut self) -> Result<(u32, u32, bool), String> {
        let pcmask = self.pcm(); let rb_ = self.rom_base();
        let f = |m: &M, i: u32| m.rb(rb_ | (m.pc.wrapping_add(i) & pcmask)) as u32;
        let lo = f(self, 0) | f(self, 1) << 8;
        let (mut ins, ln, comp) = if lo & 3 == 3 { (lo | f(self, 2) << 16 | f(self, 3) << 24, 4, false) } else { (lo, 2, true) };
        let raw = ins;
        if comp { ins = expand(ins)?; }
        let pc = self.pc; let mut npc = (pc + ln) & pcmask; let pcv = rb_ | pc; let npcv = rb_ | npc;
        let opc = ins & 0x7F; let rd = bits(ins,11,7); let f3 = bits(ins,14,12); let rs1 = bits(ins,19,15); let rs2 = bits(ins,24,20); let f7 = bits(ins,31,25);
        let chk: &[u32] = match opc { 0x33 => &[rd, rs1, rs2], 0x13 | 0x03 | 0x67 => &[rd, rs1], 0x23 | 0x63 => &[rs1, rs2], 0x37 | 0x17 | 0x6F => &[rd], _ => &[] };
        for &r in chk { if r > 15 { return Err(format!("register x{} at pc {:#x}", r, pc)); } }
        let a = self.reg(rs1); let b = self.reg(rs2);
        match opc {
            0x37 => self.setreg(rd, ins & 0xFFFFF000),
            0x17 => self.setreg(rd, pcv.wrapping_add(ins & 0xFFFFF000)),
            0x6F => {
                let imm = sx((bits(ins,31,31) << 20) | (bits(ins,19,12) << 12) | (bits(ins,20,20) << 11) | (bits(ins,30,21) << 1), 21);
                if imm == 0 && rd == 0 { self.halted = true; }
                self.setreg(rd, npcv); npc = (pc as i32).wrapping_add(imm) as u32 & pcmask;
            }
            0x67 => {
                if f3 != 0 { return Err("jalr funct3".into()); }
                let t = a.wrapping_add(sx(ins >> 20, 12) as u32) & pcmask & !1; self.setreg(rd, npcv); npc = t;
            }
            0x63 => {
                let imm = sx((bits(ins,31,31) << 12) | (bits(ins,7,7) << 11) | (bits(ins,30,25) << 5) | (bits(ins,11,8) << 1), 13);
                let (sa, sb) = (a as i32, b as i32);
                let t = match f3 { 0 => a == b, 1 => a != b, 4 => sa < sb, 5 => sa >= sb, 6 => a < b, 7 => a >= b, _ => return Err("branch funct3".into()) };
                if t { npc = (pc as i32).wrapping_add(imm) as u32 & pcmask; }
            }
            0x03 => {
                let ad = a.wrapping_add(sx(ins >> 20, 12) as u32);
                let v = match f3 { 0 => sx(self.rd(ad,1), 8) as u32, 1 => sx(self.rd(ad,2), 16) as u32, 2 => self.rd(ad,4), 4 => self.rd(ad,1), 5 => self.rd(ad,2), _ => return Err("load funct3".into()) };
                self.setreg(rd, v);
            }
            0x23 => {
                let ad = a.wrapping_add(sx((bits(ins,31,25) << 5) | bits(ins,11,7), 12) as u32);
                if f3 > 2 { return Err("store funct3".into()); }
                self.wr(ad, 1 << f3, b);
            }
            0x13 => {
                let imm = sx(ins >> 20, 12) as u32;
                let r = match f3 {
                    0 => a.wrapping_add(imm), 2 => ((a as i32) < (imm as i32)) as u32, 3 => (a < imm) as u32,
                    4 => a ^ imm, 6 => a | imm, 7 => a & imm,
                    1 => { if f7 != 0 || bits(ins,25,25) != 0 { return Err("slli".into()); } a << rs2 }
                    _ => { if (f7 != 0 && f7 != 0x20) || bits(ins,25,25) != 0 { return Err("srli/srai".into()); } if f7 != 0 { ((a as i32) >> rs2) as u32 } else { a >> rs2 } }
                };
                self.setreg(rd, r);
            }
            0x33 => {
                if (f7 != 0 && f7 != 0x20) || (f7 != 0 && f3 != 0 && f3 != 5) { return Err("op funct7".into()); }
                let sh = b & 31;
                let r = match f3 {
                    0 => if f7 != 0 { a.wrapping_sub(b) } else { a.wrapping_add(b) },
                    1 => a << sh, 2 => ((a as i32) < (b as i32)) as u32, 3 => (a < b) as u32, 4 => a ^ b,
                    5 => if f7 != 0 { ((a as i32) >> sh) as u32 } else { a >> sh },
                    6 => a | b, _ => a & b,
                };
                self.setreg(rd, r);
            }
            0x0F => {}
            _ => return Err(format!("opcode {:#x} ({:#010x}) at pc {:#x}", opc, ins, pc)),
        }
        self.pc = npc; self.icount += 1;
        Ok((pc, raw, comp))
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 { eprintln!("usage: rvemu ROM.bin [--rom-bits N] [--ram-bytes N] [--max N] [--armlog F] [--trace F] [--dump-ram F] [--load-ram F] [--pc N]"); std::process::exit(1); }
    let rom = std::fs::read(&args[1]).expect("rom");
    let (mut rom_bits, mut ab, mut ram_bytes, mut maxn, mut pc0) = (14u32, 0u32, 256usize, u64::MAX, 0u32);
    let (mut armlog, mut trace, mut dump, mut load) = (None, None, None, None);
    let mut i = 2;
    while i < args.len() {
        let v = args.get(i + 1).cloned().unwrap_or_default();
        match args[i].as_str() {
            "--rom-bits" => rom_bits = v.parse().unwrap(), "--ab" => ab = v.parse().unwrap(), "--ram-bytes" => ram_bytes = v.parse().unwrap(),
            "--max" => maxn = v.parse().unwrap(), "--pc" => pc0 = v.parse().unwrap(),
            "--armlog" => armlog = Some(v), "--trace" => trace = Some(v), "--dump-ram" => dump = Some(v), "--load-ram" => load = Some(v),
            o => { eprintln!("unknown option {o}"); std::process::exit(1); }
        }
        i += 2;
    }
    if ab == 0 { ab = rom_bits; }
    let mut m = M { rom, ram: vec![0; ram_bytes], rom_bits, ab, pc: pc0, icount: 0, halted: false, armlog: vec![], armcount: 0 };
    if let Some(f) = load { let d = std::fs::read(f).expect("load-ram"); let n = d.len().min(ram_bytes); m.ram[..n].copy_from_slice(&d[..n]); }
    let mut tr = trace.map(|f| BufWriter::new(std::fs::File::create(f).unwrap()));
    let mut code = 0;
    while !m.halted {
        if m.icount >= maxn { code = 3; break; }
        match m.step() {
            Ok((pc, raw, comp)) => { if let Some(t) = tr.as_mut() { writeln!(t, "{:x} {:0w$x}", pc, raw, w = if comp { 4 } else { 8 }).unwrap(); } }
            Err(e) => { eprintln!("illegal: {e} (after {} instructions)", m.icount); code = 2; break; }
        }
    }
    if let Some(f) = armlog { let mut w = BufWriter::new(std::fs::File::create(f).unwrap()); for (r, v) in &m.armlog { writeln!(w, "{} {}", r, v).unwrap(); } }
    if let Some(f) = dump { std::fs::write(f, &m.ram).unwrap(); }
    eprintln!("instructions {} arm_writes {} pc {:#x} halted {}", m.icount, m.armcount, m.pc, m.halted);
    std::process::exit(code);
}
