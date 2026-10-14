use rndw::driver::Driver;
use rndw::netlist::{export, Netlist};
use rndw::svg::{render, SvgOpts};
use rndw::world::{oriented_layout, Config, Kind, Pin, World};

fn small() -> Config {
    Config { rom_abits: 4, ..Config::default() }
}

fn site(w: &World, p: u32, pin: Pin) -> (i32, i32) {
    w.pin_site(p, pin).unwrap()
}

fn wire(w: &mut World, op: u32, oj: u8, ip: u32, ii: u8) {
    let o = site(w, op, Pin::Out(oj));
    let i = site(w, ip, Pin::In(ii));
    w.connect(o, i).unwrap();
}

fn run_driver(w: &mut World, d: &mut Driver) {
    while !d.idle() {
        d.pre_step(w);
        w.step();
    }
}

#[test]
fn nand_truth_table() {
    let mut w = World::new(small());
    let a = w.place(Kind::Source, 0, 0, 0).unwrap();
    let b = w.place(Kind::Source, 0, 2, 0).unwrap();
    let n = w.place(Kind::Nand, 10, 0, 0).unwrap();
    wire(&mut w, a, 0, n, 0);
    wire(&mut w, b, 0, n, 1);
    for (x, y) in [(0u8, 0u8), (0, 1), (1, 0), (1, 1)] {
        w.set_source(a, x);
        w.set_source(b, y);
        assert!(w.settle());
        assert_eq!(w.out_value(n, 0), 1 - (x & y), "NAND({x},{y})");
    }
}

#[test]
fn unwired_nand_is_tie_high() {
    let mut w = World::new(small());
    let n = w.place(Kind::Nand, 0, 0, 0).unwrap();
    assert!(w.settle());
    assert_eq!(w.out_value(n, 0), 1);
}

#[test]
fn cross_coupled_nands_hold_state() {
    let mut w = World::new(small());
    let sb = w.place(Kind::Source, 0, 0, 0).unwrap();
    let rb = w.place(Kind::Source, 0, 2, 0).unwrap();
    let n1 = w.place(Kind::Nand, 10, 0, 0).unwrap();
    let n2 = w.place(Kind::Nand, 10, 4, 0).unwrap();
    wire(&mut w, sb, 0, n1, 0);
    wire(&mut w, rb, 0, n2, 0);
    wire(&mut w, n1, 0, n2, 1);
    wire(&mut w, n2, 0, n1, 1);
    w.set_source(sb, 0); // set
    w.set_source(rb, 1);
    assert!(w.settle());
    assert_eq!((w.out_value(n1, 0), w.out_value(n2, 0)), (1, 0));
    w.set_source(sb, 1); // release: must hold
    assert!(w.settle());
    assert_eq!((w.out_value(n1, 0), w.out_value(n2, 0)), (1, 0));
    w.set_source(rb, 0); // reset
    assert!(w.settle());
    assert_eq!((w.out_value(n1, 0), w.out_value(n2, 0)), (0, 1));
    w.set_source(rb, 1); // release: must hold
    assert!(w.settle());
    assert_eq!((w.out_value(n1, 0), w.out_value(n2, 0)), (0, 1));
    assert_eq!(w.faults, 0);
}

#[test]
fn dff_chain_delays_one_tick_each() {
    let mut w = World::new(small());
    let s = w.place(Kind::Source, 0, 0, 0).unwrap();
    let d1 = w.place(Kind::Dff, 10, 0, 0).unwrap();
    let d2 = w.place(Kind::Dff, 20, 0, 0).unwrap();
    wire(&mut w, s, 0, d1, 0);
    wire(&mut w, d1, 0, d2, 0);
    w.set_source(s, 1);
    w.step();
    assert_eq!((w.out_value(d1, 0), w.out_value(d2, 0)), (1, 0));
    w.step();
    assert_eq!((w.out_value(d1, 0), w.out_value(d2, 0)), (1, 1));
    w.set_source(s, 0);
    w.step();
    assert_eq!((w.out_value(d1, 0), w.out_value(d2, 0)), (0, 1));
}

#[test]
fn dff_swap_is_simultaneous() {
    // Two DFFs feeding each other swap values on a tick (no race).
    let mut w = World::new(small());
    let a = w.place(Kind::Dff, 0, 0, 0).unwrap();
    let b = w.place(Kind::Dff, 10, 0, 0).unwrap();
    wire(&mut w, a, 0, b, 0);
    wire(&mut w, b, 0, a, 0);
    w.set_dff(a, 1);
    w.settle();
    w.step();
    assert_eq!((w.out_value(a, 0), w.out_value(b, 0)), (0, 1));
    w.step();
    assert_eq!((w.out_value(a, 0), w.out_value(b, 0)), (1, 0));
}

#[test]
fn rom_reads_programmed_cells_and_locks_on_wire() {
    let mut w = World::new(small());
    let rom = w.place(Kind::Rom, 10, 10, 0).unwrap();
    let addr: Vec<u32> = (0..4).map(|i| w.place(Kind::Source, 0, i * 2, 0).unwrap()).collect();
    let o = w.parts[rom as usize].x; // origin lookups use the placed coordinates
    assert_eq!(o, 10);
    for a in 0..16usize {
        w.program_rom(10, 10, a, (a * 7 + 3) as u8).unwrap();
    }
    for (i, &s) in addr.iter().enumerate() {
        wire(&mut w, s, 0, rom, i as u8);
    }
    // Now wired: further programming must fail.
    assert!(w.program_rom(10, 10, 0, 99).is_err());
    for a in 0..16u8 {
        for (i, &s) in addr.iter().enumerate() {
            w.set_source(s, (a >> i) & 1);
        }
        assert!(w.settle());
        let mut v = 0u8;
        for j in 0..8 {
            v |= w.out_value(rom, j) << j;
        }
        assert_eq!(v, (a as usize * 7 + 3) as u8, "ROM[{a}]");
    }
}

#[test]
fn every_kind_and_rotation_has_consistent_pin_sites() {
    for kind in [Kind::Nand, Kind::Dff, Kind::Rom, Kind::Arm, Kind::Source] {
        for rot in 0..4u8 {
            let mut w = World::new(small());
            let p = w.place(kind, 7, 9, rot).unwrap();
            let (nw, nh, pins) = oriented_layout(kind, rot, 4);
            let part = w.parts[p as usize].clone();
            assert_eq!((part.w, part.h), (nw, nh));
            let mut seen = std::collections::HashSet::new();
            for (dx, dy, pin) in pins {
                assert!(dx >= 0 && dx < nw && dy >= 0 && dy < nh, "{kind:?} rot {rot}");
                assert!(seen.insert((dx, dy)), "pins share a cell: {kind:?} rot {rot}");
                let (x, y) = site(&w, p, pin);
                assert_eq!(w.site_pin(x, y), Some((p, pin)));
            }
        }
    }
}

fn counter_text(bits: usize) -> String {
    // Input w0 = enable; DFFs w1..=bits; per bit: t, a, b, x, cn = 5 gates.
    let base = 1 + bits;
    let mut s = format!("in 1\ndff {}\n", bits);
    for i in 0..bits {
        s.push_str(&format!("q{} <= w{}\n", i, base + 5 * i + 3));
    }
    for i in 0..bits {
        let q = 1 + i;
        let c = if i == 0 { 0 } else { base + 5 * (i - 1) + 4 };
        let g = base + 5 * i;
        s.push_str(&format!("w{} = NAND w{} w{}\n", g, q, c));
        s.push_str(&format!("w{} = NAND w{} w{}\n", g + 1, q, g));
        s.push_str(&format!("w{} = NAND w{} w{}\n", g + 2, c, g));
        s.push_str(&format!("w{} = NAND w{} w{}\n", g + 3, g + 1, g + 2));
        s.push_str(&format!("w{} = NAND w{} w{}\n", g + 4, g, g));
    }
    s
}

#[test]
fn netlist_counter_counts_and_round_trips() {
    let bits = 6;
    let text = counter_text(bits);
    let nl = Netlist::parse(&text).unwrap();
    assert_eq!(nl.to_text(), text);
    let mut w = World::new(small());
    let map = nl.build(&mut w).unwrap();
    w.set_source(map.sources[0], 1);
    assert!(w.settle());
    for t in 1..=200usize {
        w.step();
        let mut v = 0usize;
        for (i, &d) in map.dffs.iter().enumerate() {
            v |= (w.out_value(d, 0) as usize) << i;
        }
        assert_eq!(v, t % (1 << bits), "tick {t}");
    }
    assert_eq!(w.faults, 0);
    assert_eq!(export(&w).unwrap().to_text(), text);
}

#[test]
fn arm_builds_circuit_through_its_pins() {
    let mut w = World::new(small());
    let mut d = Driver::install(&mut w, 0, 0).unwrap();
    d.place(0, 300, 260, 0); // 16-bit coordinates
    d.place(0, 310, 260, 0);
    d.wire(301, 260, 310, 260); // Y of the first -> A of the second
    d.place(1, 320, 260, 0);
    d.wire(311, 260, 320, 260); // second NAND -> DFF
    let writes = d.pending() as u64;
    run_driver(&mut w, &mut d);
    assert_eq!(w.faults, 0, "{:?}", w.fault_log);
    assert_eq!(w.tick, writes);
    let st = w.stats();
    assert_eq!((st.nand, st.dff, st.arm, st.wires), (2, 1, 1, 13 + 2));
    let n1 = w.part_at(300, 260).unwrap();
    assert_eq!((w.parts[n1 as usize].x, w.parts[n1 as usize].y), (300, 260));
}

#[test]
fn arm_programs_rom_before_wiring_but_not_after() {
    let mut w = World::new(small());
    let mut d = Driver::install(&mut w, 0, 0).unwrap();
    d.place(2, 100, 100, 0);
    d.program_rom(100, 100, 5, 0xAB);
    d.program_rom(100, 100, 6, 0xCD);
    d.place(1, 120, 100, 0); // a DFF whose D input we wire to ROM DATA[0]
    d.wire(101, 100, 120, 100);
    run_driver(&mut w, &mut d);
    assert_eq!(w.faults, 0, "{:?}", w.fault_log);
    let rom = w.part_at(100, 100).unwrap();
    assert_eq!(w.roms[w.parts[rom as usize].aux as usize][5], 0xAB);
    d.program_rom(100, 100, 7, 0xEE); // ROM is wired now
    run_driver(&mut w, &mut d);
    assert_eq!(w.faults, 1);
    assert_eq!(w.roms[w.parts[rom as usize].aux as usize][7], 0);
}

#[test]
fn faults_are_counted_not_fatal() {
    let mut w = World::new(small());
    let mut d = Driver::install(&mut w, 0, 0).unwrap();
    d.place(0, 100, 100, 0);
    d.place(0, 100, 100, 0); // overlap
    d.place(7, 200, 200, 0); // bad kind
    d.place(0, 200, 200, 5); // bad angle
    d.place(0, 65535, 65535, 0); // out of bounds
    d.wire(0, 0, 100, 100); // arm pin site to NAND input: both inputs
    d.wire(101, 100, 150, 150); // second site is not a part
    d.place(0, 120, 100, 0);
    d.wire(101, 100, 120, 100);
    d.wire(101, 100, 120, 100); // input already driven
    d.reg(15, 9); // unknown command
    d.reg(12, 1); // reserved register
    run_driver(&mut w, &mut d);
    assert_eq!(w.faults, 9, "{:#?}", w.fault_log);
    assert_eq!(w.stats().nand, 2);
}

#[test]
fn en_wire_event_fires_once() {
    let mut w = World::new(small());
    let arm = w.place(Kind::Arm, 0, 0, 0).unwrap();
    let s = w.place(Kind::Source, 10, 0, 0).unwrap();
    assert!(!w.take_en_wire_event());
    wire(&mut w, s, 0, arm, 0); // ADDR pin: no event
    assert!(!w.take_en_wire_event());
    wire(&mut w, s, 0, arm, 4); // EN pin
    assert!(w.take_en_wire_event());
    assert!(!w.take_en_wire_event());
}

#[test]
fn oscillator_does_not_hang_and_is_a_fault() {
    let mut w = World::new(Config { event_limit: 1000, ..small() });
    let hi = w.place(Kind::Nand, 0, 0, 0).unwrap(); // tie-high
    let osc = w.place(Kind::Nand, 10, 0, 0).unwrap();
    wire(&mut w, hi, 0, osc, 1);
    wire(&mut w, osc, 0, osc, 0); // NOT feeding itself
    assert!(!w.settle());
    assert_eq!(w.faults, 1);
    // The world keeps working afterwards.
    w.step();
}

#[test]
fn svg_detail_coarse_and_window() {
    let mut w = World::new(small());
    let mut d = Driver::install(&mut w, 0, 0).unwrap();
    for i in 0..20 {
        d.place(0, 100 + 3 * i, 100, 0);
    }
    run_driver(&mut w, &mut d);
    let detail = render(&w, &SvgOpts::default());
    assert!(detail.contains("<svg") && detail.contains("mode=detail"));
    assert_eq!(detail.matches("class=\"n\" x=").count(), 20);
    let coarse = render(&w, &SvgOpts { max_elements: 8, ..SvgOpts::default() });
    assert!(coarse.contains("mode=coarse"));
    assert!(coarse.matches("<rect class").count() < 20 + 3);
    let win = render(&w, &SvgOpts { window: Some((98, 98, 110, 104)), ..SvgOpts::default() });
    assert_eq!(win.matches("class=\"n\" x=").count(), 4);
}

#[test]
fn state_round_trips_and_resumes_identically() {
    let mut w = World::new(small());
    let nl = Netlist::parse(&counter_text(5)).unwrap();
    let map = nl.build(&mut w).unwrap();
    w.set_source(map.sources[0], 1);
    w.settle();
    for _ in 0..13 {
        w.step();
    }
    let rom = w.place(Kind::Rom, 200, 200, 1).unwrap();
    w.program_rom(200, 200, 3, 0x5A).unwrap();
    let text = w.save_state();
    let mut w2 = World::load_state(&text).unwrap();
    assert_eq!(w2.save_state(), text);
    assert_eq!(w2.tick, 13);
    let _ = rom;
    for _ in 0..40 {
        w.step();
        w2.step();
    }
    assert_eq!(w.save_state().replace("tick 53", ""), w2.save_state().replace("tick 53", ""));
}

#[test]
fn vector_runner_detects_mismatches() {
    use rndw::vectors::run_vectors;
    let nl = Netlist::parse("in 2\ndff 0\nw2 = NAND w0 w1\n").unwrap();
    let good = "rndw-vectors 1\nn_in 2\nwatch 2\nt 00 1\nt 01 1\nt 10 1\nt 11 0\n";
    let bad = "rndw-vectors 1\nn_in 2\nwatch 2\nt 00 1\nt 11 1\n";
    for (text, want) in [(good, 0usize), (bad, 1usize)] {
        let mut w = World::new(small());
        let map = nl.build(&mut w).unwrap();
        w.settle();
        let rep = run_vectors(&mut w, &nl, &map, text).unwrap();
        assert_eq!(rep.mismatches, want);
    }
}

#[test]
fn arm_coordinates_are_signed_offsets_from_the_arm() {
    let mut w = World::new(small());
    let mut d = Driver::install(&mut w, 400, 400).unwrap();
    d.place(0, 100, 60, 0); // -> absolute (500, 460)
    d.place(0, -150, -40, 0); // -> absolute (250, 360): negative offsets
    d.wire(101, 60, -150, -40); // Y of the first -> A of the second (relative both ends)
    run_driver(&mut w, &mut d);
    assert_eq!(w.faults, 0, "{:?}", w.fault_log);
    assert!(w.part_at(500, 460).is_some());
    assert!(w.part_at(250, 360).is_some());
    assert!(w.part_at(100, 60).is_none());
}
