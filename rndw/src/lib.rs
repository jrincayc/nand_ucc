//! RNDW: Robot + NAND + DFF + Wires (+ ROM) world simulator.  Standard library only.
//!
//! See RNDW_SPEC.md for the world rules.  Module map:
//!   world   - parts, pins, wires, grid, event-driven settle, DFF tick, arm interpreter
//!   netlist - nandgen text netlist import / export
//!   state   - save / load of a whole world (also the seed-world config format)
//!   svg     - SVG snapshots (detail mode, coarse "merged tile" mode, window)
//!   driver  - test/CLI harness that drives one arm through its pins
//!   vectors - differential test runner against the Python reference Sim

pub mod driver;
pub mod netlist;
pub mod state;
pub mod svg;
pub mod vectors;
pub mod world;
