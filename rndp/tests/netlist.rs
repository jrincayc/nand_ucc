use rndp::netlist::*;
use rndp::world::*;

fn world() -> World {
    World::new(Config { width: 4000, height: 4000, ..Config::default() })
}

// 3 inputs a b c; toggle flip-flop t <= NOT t (w? numbering: in 0..2, dff 3, gates 4..)
const NL: &str = "in 3\ndff 1\nq0 <= w5\nw4 = NAND w0 w1\nw5 = NAND w3 w3\nw6 = NAND w4 w2\n";

#[test]
fn parse_and_roundtrip_layout_has_no_faults() {
    let nl = Netlist::parse(NL).unwrap();
    assert_eq!((nl.n_in, nl.n_dff, nl.gates.len()), (3, 1, 3));
    let mut w = world();
    let map = nl.build(&mut w).unwrap();
    assert_eq!(w.faults, 0);
    // truth table of w4 = NAND(a,b) and w6 = NAND(w4,c) through real copper
    for bits in 0..8u8 {
        for k in 0..3 {
            w.set_source(map.sources[k], (bits >> k) & 1);
        }
        w.settle();
        let (a, b, c) = (bits & 1, (bits >> 1) & 1, (bits >> 2) & 1);
        let w4 = 1 - (a & b);
        assert_eq!(w.out_value(map.nands[0], 0), w4);
        assert_eq!(w.out_value(map.nands[2], 0), 1 - (w4 & c));
    }
    // toggle flop: q flips each tick
    let q0 = w.out_value(map.dffs[0], 0);
    w.step();
    assert_eq!(w.out_value(map.dffs[0], 0), 1 - q0);
    w.step();
    assert_eq!(w.out_value(map.dffs[0], 0), q0);
}

#[test]
fn vectors_catch_a_wrong_wire() {
    let nl = Netlist::parse(NL).unwrap();
    let mut w = world();
    let map = nl.build(&mut w).unwrap();
    // expected values for watch w4: NAND(a,b); inputs 3 bits; first tick a=1 b=1 -> 0
    let good = "rndw-vectors 1\nn_in 3\nwatch 4\nt 110 0\nt 100 1\n";
    let r = run_vectors(&mut w, &nl, &map, good).unwrap();
    assert_eq!((r.ticks, r.compared, r.mismatches), (2, 2, 0));
    let bad = "rndw-vectors 1\nn_in 3\nwatch 4\nt 110 1\n";
    let r = run_vectors(&mut w, &nl, &map, bad).unwrap();
    assert_eq!(r.mismatches, 1);
}

#[test]
fn parse_errors() {
    assert!(Netlist::parse("in 1\ndff 0\nw1 = NAND w0 w9\n").is_err());
    assert!(Netlist::parse("in 1\ndff 0\nw5 = NAND w0 w0\n").is_err());
    assert!(Netlist::parse("dff 0\n").is_err());
}

#[test]
fn needs_two_layers() {
    let nl = Netlist::parse(NL).unwrap();
    let mut w = World::new(Config { layers: 1, ..Config::default() });
    assert!(nl.build(&mut w).is_err());
}
