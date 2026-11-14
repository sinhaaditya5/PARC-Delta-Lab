// PARC-Delta / PDX-1 investor technical report (.docx) — built with docx-js.
// Run: NODE_PATH=<lab>/tools/node/node_modules node make_docx.js
const fs = require("fs");
const path = require("path");
const sharp = require("sharp");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, AlignmentType, HeadingLevel,
  WidthType, ShadingType, BorderStyle, PageBreak, Header, Footer, PageNumber, LevelFormat, TableOfContents,
  VerticalAlign, TabStopType, TabStopPosition,
} = require("docx");

const PROTO = path.resolve(__dirname, "..");
const R = JSON.parse(fs.readFileSync(path.join(PROTO, "report/out/results_summary.json"), "utf8"));
const OUT = path.join(PROTO, "docs/out");
fs.mkdirSync(OUT, { recursive: true });

const NAVY = "0D1628", BLUE = "2456C7", ORANGE = "E8833A", MUTED = "6B7385", INK = "1D2433", LIGHT = "EEF2FA", LINE = "D5DAE3";
const STATUS = { pass: ["PASS", "2E8B57"], open: ["OPEN", "B23A48"], finding: ["FINDING", "E8833A"], "design change": ["DESIGN CHANGE", "2456C7"] };
const CONTENT_W = 9360; // DXA, US Letter with 1" margins
const IMG_W = 624;      // px at 96 dpi = 6.5"

const img = (rel) => path.join(PROTO, rel);
const t = (text, o = {}) => new TextRun({ text, font: "Calibri", size: 22, color: INK, ...o });
const P = (children, o = {}) => new Paragraph({ children: Array.isArray(children) ? children : [t(children)], spacing: { after: 140, line: 288 }, ...o });
const H1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text, font: "Calibri", size: 36, bold: true, color: NAVY })], spacing: { before: 360, after: 180 } });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text, font: "Calibri", size: 28, bold: true, color: BLUE })], spacing: { before: 280, after: 120 } });
const bullet = (runs, level = 0) => new Paragraph({ numbering: { reference: "bullets", level }, children: Array.isArray(runs) ? runs : [t(runs)], spacing: { after: 80, line: 276 } });
const caption = (text) => new Paragraph({ children: [new TextRun({ text, font: "Calibri", size: 18, italics: true, color: MUTED })], spacing: { before: 60, after: 240 } });
const pb = () => new Paragraph({ children: [new PageBreak()] });

async function figure(rel, cap, widthPx = IMG_W) {
  const file = img(rel);
  const meta = await sharp(file).metadata();
  const h = Math.round(widthPx * meta.height / meta.width);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 0 },
      children: [new ImageRun({ type: file.endsWith(".jpg") ? "jpg" : "png", data: fs.readFileSync(file), transformation: { width: widthPx, height: h },
        altText: { title: cap, description: cap, name: path.basename(file) } })] }),
    caption(cap),
  ];
}

const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
const borders = { top: border, bottom: border, left: border, right: border };
function cell(content, width, o = {}) {
  const runs = typeof content === "string" ? [new TextRun({ text: content, font: "Calibri", size: o.size || 18, bold: o.bold, color: o.color || INK })] : content;
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
    shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 70, bottom: 70, left: 100, right: 100 },
    children: [new Paragraph({ children: runs, alignment: o.align || AlignmentType.LEFT })],
  });
}
function table(header, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, widths[i], { bold: true, color: "FFFFFF", fill: NAVY })) }),
      ...rows.map((r, ri) => new TableRow({ children: r.map((c, i) => (c instanceof TableCell ? c : cell(c, widths[i], { fill: ri % 2 ? "F7F9FC" : undefined, ...(opts.cellOpts || {}) }))) })),
    ],
  });
}
function statCards(stats) {
  const w = Math.floor(CONTENT_W / stats.length);
  return new Table({
    width: { size: w * stats.length, type: WidthType.DXA }, columnWidths: stats.map(() => w),
    rows: [new TableRow({ children: stats.map(([big, small]) => new TableCell({
      borders: { top: { style: BorderStyle.SINGLE, size: 8, color: "FFFFFF" }, bottom: { style: BorderStyle.SINGLE, size: 8, color: "FFFFFF" },
                 left: { style: BorderStyle.SINGLE, size: 8, color: "FFFFFF" }, right: { style: BorderStyle.SINGLE, size: 8, color: "FFFFFF" } },
      width: { size: w, type: WidthType.DXA }, shading: { fill: LIGHT, type: ShadingType.CLEAR, color: "auto" },
      margins: { top: 160, bottom: 160, left: 120, right: 120 },
      children: [
        new Paragraph({ alignment: AlignmentType.LEFT, children: [new TextRun({ text: big, font: "Calibri", size: 40, bold: true, color: BLUE })] }),
        new Paragraph({ alignment: AlignmentType.LEFT, children: [new TextRun({ text: small, font: "Calibri", size: 17, color: MUTED })] }),
      ] })) })],
  });
}

async function build() {
  const mag = R.magnet, orb = R.orbits, bench = R.bench, s3 = orb.scan["3.0T"];
  const pct = (x, d = 1) => (x * 100).toFixed(d) + "%";
  const children = [];

  // ---------------------------------------------------------------- cover
  children.push(new Paragraph({ spacing: { before: 600, after: 120 }, children: [new TextRun({ text: "PARC-Delta", font: "Calibri", size: 30, bold: true, color: ORANGE })] }));
  children.push(new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: "PDX-1 Prototype: CAD, Simulation and Test Report", font: "Calibri", size: 56, bold: true, color: NAVY })] }));
  children.push(new Paragraph({ spacing: { after: 360 }, children: [new TextRun({ text: "What we built, how we tested it, what the tests showed — and what is still open", font: "Calibri", size: 28, color: MUTED })] }));
  children.push(...await figure("docs/img/pdx1_hero.jpg", "PDX-1 linear test stand — photoreal render of the concept CAD model (Blender 5.0, Cycles)."));
  children.push(table(["Document", "Detail"], [
    ["Prepared for", "Investor technical due diligence (YC application supplement)"],
    ["Programme", "PARC-Delta — p–¹¹B fusion alpha-channeling research model, release v1.6.0-research"],
    ["Device", "PDX-1 linear mirror test stand — concept design (not for fabrication)"],
    ["Date", R.date],
    ["Status", "Research and concept stage. Not a reactor design; no claim of fusion gain, net electricity or low-cost power."],
  ], [2300, 7060]));
  children.push(pb());

  // ---------------------------------------------------------------- contents
  children.push(H1("Contents"));
  children.push(new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }));
  children.push(P([t("Right-click the table and choose Update Field if page numbers are not shown.", { size: 18, color: MUTED, italics: true })]));
  children.push(pb());

  // ---------------------------------------------------------------- 1 executive summary
  children.push(H1("1. Executive summary"));
  children.push(P("PARC-Delta is a research software programme that asks one narrow, falsifiable question: can a closed-loop, distribution-aware scheduler of ion-Bernstein waves (IBWs) move more fusion-alpha energy into fuel protons than the classical collisional path, without spending more RF power than it saves? The v1.6 model already reproduces the published linear IBW benchmark and computes the collisional baseline that any channeling scheme must beat."));
  children.push(P("For this report we designed, simulated and rendered PDX-1, a bench-scale linear mirror device that would test the programme’s physics in hardware, and we re-ran and extended the full software validation. All CAD, drawings and simulations are generated from a single parameter file, so every number in this report can be traced and reproduced."));
  children.push(statCards([["76/76", "automated tests pass"], ["7.5e-10", "max deviation, v1.6 rerun"], [`${mag.B0_on_axis_T.toFixed(1)} T`, `HTS mirror, ratio ${mag.mirror_ratio.toFixed(2)}`], [pct(s3.fractions.all["limiter/wall"]), "alpha wall loss at 3 T"]]));
  children.push(P(""));
  children.push(H2("Key results"));
  [
    [t("Software is reproducible. ", { bold: true }), t(`All 76 tests pass, and the full v1.6 numerical campaign re-ran on an independent toolchain with ${R.reproducibility.values_compared} values matching to a worst-case relative deviation of ${R.reproducibility.max_rel_diff.toExponential(1)}.`)],
    [t("The orbit solver agrees with theory. ", { bold: true }), t(`Simulated end losses of ${pct(s3.fractions.all["end loss"], 2)} match the analytic magnetic loss cone (${pct(orb.fraction_in_loss_cone_at_birth, 2)}) for alphas drawn from the PARC-Delta birth source.`)],
    [t("Simulation drove real design changes. ", { bold: true }), t(`A ~${mag.peak_field_at_conductor_T.toFixed(0)} T winding field moved the magnet from NbTi to REBCO HTS; a field scan fixed B0 = 3 T (wall loss ${pct(orb.scan["1.0T"].fractions.all["limiter/wall"], 0)} at 1 T vs ${pct(s3.fractions.all["limiter/wall"])} at 3 T).`)],
    [t("We found the hard problem early. ", { bold: true }), t(`A microamp beam-on-foil source yields ~10^${Math.round(Math.log10(bench.alpha_budget.shortfall_factor_best_case))} times too few alphas to self-excite IBWs, and an on-axis foil re-intersects ${pct(s3.fractions.all["target hit"], 0)} of trapped alphas within 4 µs. Phase 1 therefore validates the alpha source; Phase 2 adds a surrogate energetic-ion ring.`)],
  ].forEach((r) => children.push(bullet(r)));
  children.push(H2("What we are not claiming"));
  children.push(P("PDX-1 is a concept for a research instrument. It is not a reactor, does not produce net energy and has not been engineered for fabrication. The multi-mode scheduler is a hypothesis; three of the programme’s seven acceptance gates (nonlinear benchmark, irreversible heating, fair baselines) are not yet implemented, and the full-mixture collision cross-check has a documented 6–7% open discrepancy."));
  children.push(pb());

  // ---------------------------------------------------------------- 2 problem & approach
  children.push(H1("2. The problem and our approach"));
  children.push(P("In proton–boron-11 fusion each reaction releases about 8.7 MeV as three alpha particles. Left alone, those alphas slow down on the plasma: our v1.6 simulation of a 10 keV, 10²⁰ m⁻³ background sends about 73% of their energy to electrons and only 26–27% to protons. Energy in electrons is largely radiated away, which is a central obstacle for aneutronic fusion."));
  children.push(...await figure("diagrams/out/d3_energy_flow.png", "Figure 1 — Classical alpha energy partition simulated with PARC-Delta v1.6 (reactor-like background) and in the PDX-1 bench plasma. This is the baseline any channeling scheme must beat."));
  children.push(P("Alpha channeling — using plasma waves to take energy from alphas and give it to fuel ions — is established prior art (Fisch 1995; Fisch & Herrmann 1995; Qin & Fisch 2026; Liu et al. 2026). PARC-Delta does not claim the idea. Our narrow hypothesis is that a closed-loop scheduler, which continuously re-tunes a coupled set of IBW modes using measured alpha phase-space gradients, beats both a no-channeling baseline and a single fixed mode under identical conditions. The hypothesis is falsified if the advantage disappears with collisions and saturation, if proton energy stays coherent rather than becoming heat, or if a fixed multi-wave spectrum does just as well."));
  children.push(...await figure("diagrams/out/d2_control_loop.png", "Figure 2 — The closed-loop resonance scheduler: the hypothesis PDX-1 is designed to test."));
  children.push(pb());

  // ---------------------------------------------------------------- 3 what we built
  children.push(H1("3. What we built"));
  children.push(H2("3.1 PDX-1 concept device"));
  children.push(P("PDX-1 is a 6.9 m linear magnetic mirror. A 0.7 MV electrostatic accelerator sends 0.675 MeV protons — the p–¹¹B resonance energy used throughout PARC-Delta — through a helicon plasma source onto a 1 µm enriched ¹¹B foil at the centre of a 3 T superconducting mirror. Four Faraday-shielded IBW antennas, an FPGA scheduler and a diagnostic set for alphas, waves and proton heating complete the loop."));
  children.push(...await figure("docs/img/pdx1_hero_annotated.jpg", "Figure 3 — PDX-1 major subsystems (annotated render)."));
  children.push(table(["Parameter", "Value", "Source"], [
    ["Central field B0 / mirror field", `${mag.B0_on_axis_T.toFixed(2)} T / ${mag.B_max_on_axis_T.toFixed(2)} T (ratio ${mag.mirror_ratio.toFixed(2)})`, "magnet simulation"],
    ["Coils", "2 mirror + 6 main REBCO HTS, 20 K, conduction-cooled", "design decision (T4)"],
    ["Amp-turns per coil", `${(mag.amp_turns_per_main_coil / 1e6).toFixed(2)} MA-t main · ${(mag.amp_turns_per_mirror_coil / 1e6).toFixed(2)} MA-t mirror`, "magnet simulation"],
    ["Stored magnetic energy", `${mag.stored_magnetic_energy_MJ.toFixed(1)} MJ`, "inductance matrix"],
    ["Vacuum vessel", "316L, ID 600 mm × 2400 mm; limiter r = 250 mm", "CAD"],
    ["Beam / target", "0.675 MeV protons, 10 µA; 1 µm enriched ¹¹B foil", "design input"],
    ["Bench plasma", "helicon, ne ≈ 1e19 m⁻³, Te ≈ 10 eV, Tp ≈ 2 eV", "design input"],
    ["IBW channels A1–A4", "57.6 / 80.6 / 103.6 / 126.6 MHz (illustrative)", "resonance map"],
    ["Envelope / parts", `${(R.cad.overall_mm[0] / 1000).toFixed(1)} × ${(R.cad.overall_mm[1] / 1000).toFixed(1)} × ${(R.cad.overall_mm[2] / 1000).toFixed(1)} m · ${R.cad.part_count} labelled parts`, "CAD"],
  ], [2900, 4160, 2300]));
  children.push(caption("Table 1 — PDX-1 key parameters. Values marked as simulation outputs are reproduced by the scripts listed in the appendix."));
  children.push(...await figure("diagrams/out/d1_architecture.png", "Figure 4 — System architecture: beam path and the control/support systems."));
  children.push(...await figure("docs/img/pdx1_cutaway_annotated.jpg", "Figure 5 — Central-cell cutaway. The orange orbits are simulated alpha trajectories from the PARC-Delta birth source in the simulated field, not artwork."));
  children.push(H2("3.2 Engineering drawing and CAD deliverables"));
  children.push(P("A general-arrangement drawing (PDX1-GA-001, A0 at 1:10) was generated headlessly in CADCraft from the same parameter file as the 3D model and the simulations. The 3D model is a labelled STEP assembly built with build123d on the OpenCascade kernel."));
  children.push(...await figure("docs/img/PDX1-GA-001_paper_hi.jpg", "Figure 6 — General arrangement PDX1-GA-001: longitudinal section B-B, target-plane section A-A, parts list and notes."));
  children.push(pb());

  // ---------------------------------------------------------------- 4 how we tested
  children.push(H1("4. How we tested"));
  children.push(P("Our test philosophy is that a result only counts if it is traceable, reproducible and checked against something independent. Concretely:"));
  [
    [t("Single source of truth. ", { bold: true }), t("One parameter file drives the CAD model, the drawing and every simulation, so geometry and physics cannot drift apart.")],
    [t("Independent re-execution. ", { bold: true }), t("The v1.6 release was copied to a clean toolchain and its full numerical campaign was re-run and compared value by value.")],
    [t("Analytic cross-checks. ", { bold: true }), t("New solvers must reproduce a known answer first (the magnetic loss cone for the orbit pusher; the published LAPD case for the linear IBW model).")],
    [t("Use the programme’s own physics. ", { bold: true }), t("Device studies draw alphas from the PARC-Delta birth-source sampler and slow them with the PARC-Delta Rosenbluth coefficients, rather than re-implementing physics.")],
    [t("Stated caveats. ", { bold: true }), t("Every output file lists its assumptions; any assumed constant (for example the 1.2 b cross-section) is flagged and the conclusion checked for robustness.")],
  ].forEach((r) => children.push(bullet(r)));
  children.push(H2("4.1 Toolchain"));
  children.push(table(["Purpose", "Tool (all free / open source)"], [
    ["Physics model + tests", "PARC-Delta v1.6 (Python 3.12, NumPy, SciPy), pytest"],
    ["Magnetostatics", "magpylib (analytic current loops) + Maxwell mutual-inductance matrix"],
    ["Particle orbits", "Boris full-orbit integrator (NumPy), field map from magpylib"],
    ["3D CAD", "build123d on OpenCascade (STEP, STL)"],
    ["2D drawing", "CADCraft 0.15.1 CLI (Rust), DXF + A0 PDF"],
    ["Rendering + video", "Blender 5.0 (Cycles, Metal GPU), FFmpeg, macOS speech synthesis"],
  ], [3000, 6360]));
  children.push(H2("4.2 Test matrix"));
  const sw = [700, 1500, 2700, 3200, 1260];
  children.push(table(["ID", "Area", "What was tested · how", "Result", "Status"],
    R.tests.map((x) => {
      const [label, col] = STATUS[x.status];
      return [x.id, x.area,
        cell([new TextRun({ text: x.what + ". ", font: "Calibri", size: 17, bold: true, color: INK }), new TextRun({ text: x.how, font: "Calibri", size: 17, color: MUTED })], sw[2]),
        cell(x.result, sw[3], { size: 17 }),
        cell([new TextRun({ text: label, font: "Calibri", size: 16, bold: true, color: col })], sw[4])];
    }), sw));
  children.push(caption("Table 2 — Test matrix. PASS = agrees with its reference; FINDING = a result that changes the plan; DESIGN CHANGE = a test that altered the design; OPEN = documented unresolved discrepancy."));
  children.push(...await figure("diagrams/out/d4_validation.png", "Figure 7 — Validation ladder: programme acceptance gates and the tests performed in this work."));
  children.push(pb());

  // ---------------------------------------------------------------- 5 results
  children.push(H1("5. Results"));
  children.push(H2("5.1 Software validation and reproducibility (T1–T3)"));
  children.push(P(`The 76-test suite passed in 13 s. Re-running scripts_run_v16.py in an isolated copy regenerated all ${R.reproducibility.file_count} v1.6 result files; across ${R.reproducibility.values_compared} numerical values the worst relative deviation from the shipped release was ${R.reproducibility.max_rel_diff.toExponential(1)}, which is floating-point noise. The release’s own cross-checks remain as reported: a single-proton bath agrees with the Rosenbluth reference to better than 0.003%, while the full electron–proton–alpha mixture still captures only 92.9% (TA) and 93.9% (Nanbu) of the predicted alpha energy loss at 32 substeps — an open item we track as T3.`));
  children.push(table(["v1.6 result file", "Values", "Max relative deviation"], R.reproducibility.files.map((f) => [f.file, String(f.values), f.max_rel_diff === 0 ? "0 (bit-identical)" : f.max_rel_diff.toExponential(1)]), [5560, 1200, 2600]));
  children.push(caption("Table 3 — Value-by-value reproduction of the v1.6 numerical campaign."));
  children.push(H2("5.2 Magnet (T4)"));
  children.push(P(`Solving the main and mirror coil currents for B0 = 3.0 T and a target mirror ratio of 1.6 gives ${(mag.amp_turns_per_main_coil / 1e6).toFixed(2)} MA-turns per main coil and ${(mag.amp_turns_per_mirror_coil / 1e6).toFixed(2)} MA-turns per mirror coil, a ${mag.mirror_ratio.toFixed(2)} mirror ratio and ${mag.stored_magnetic_energy_MJ.toFixed(1)} MJ stored. The test that mattered: the mirror windings see about ${mag.peak_field_at_conductor_T.toFixed(1)} T, beyond practical NbTi margins at 4.2 K, so the baseline moved to REBCO HTS at 20 K. A J×B×R screen gives ~${Math.round(mag.hoop_stress_estimate_MPa["MR-R"])} MPa in the mirror coil — acceptable for reinforced REBCO but requiring finite-element confirmation.`));
  children.push(...await figure("sim/out/fig_magnet_axis.png", "Figure 8 — Simulated on-axis field and coil layout."));
  children.push(...await figure("sim/out/fig_magnet_map.png", "Figure 9 — |B| map and flux surfaces in the central cell with the vessel wall and limiter."));
  children.push(H2("5.3 Alpha orbits and confinement (T5–T7)"));
  children.push(P(`${2 * orb.alphas_per_branch} alphas (α0 and α1 branches, unweighted) were sampled from the PARC-Delta sequential-kinematic source for 0.675 MeV protons and pushed for 4 µs with a 0.4 ns Boris integrator. The simulated end loss of ${pct(s3.fractions.all["end loss"], 2)} matches the analytic loss cone of ${pct(orb.fraction_in_loss_cone_at_birth, 2)}, validating the solver. Wall loss falls from ${pct(orb.scan["1.0T"].fractions.all["limiter/wall"], 0)} at 1 T to ${pct(orb.scan["2.0T"].fractions.all["limiter/wall"], 0)} at 2 T and ${pct(s3.fractions.all["limiter/wall"])} at 3 T, which fixes the design field.`));
  children.push(...await figure("sim/out/fig_alpha_phase_space.png", "Figure 10 — Birth energy vs pitch with each alpha’s fate at 3 T. The dashed lines are the analytic loss-cone boundaries."));
  children.push(...await figure("sim/out/fig_alpha_fate_vs_B.png", "Figure 11 — Alpha fate after 4 µs versus central field."));
  children.push(P(`The same run exposed a structural issue: every gyro-orbit of an alpha born on the axis passes back through the axis at the mid-plane, so ${pct(s3.fractions.all["target hit"], 0)} of alphas strike the foil frame or arm within 4 µs (median first foil re-crossing ${s3.median_time_to_first_foil_recrossing_us.toFixed(1)} µs). Moving the target off-axis only trades target hits for wall hits; the confined fraction stays at 16–22%.`));
  children.push(...await figure("sim/out/fig_alpha_orbits.png", "Figure 12 — Simulated orbits: side view (bounce between mirrors) and end view (orbits re-visit the axis)."));
  children.push(...await figure("sim/out/fig_alpha_target_offset.png", "Figure 13 — Design trade: target radial offset versus alpha fate at 3 T."));
  children.push(H2("5.4 Bench collisions and the alpha inventory (T8–T9)"));
  const sd = bench.slowing_down["3.12MeV"], ab = bench.alpha_budget;
  children.push(P(`Using the PARC-Delta Rosenbluth coefficients for the bench plasma, a 3.1 MeV alpha slows to 50 keV in ${sd.time_to_50keV_ms.toFixed(1)} ms and deposits ${pct(sd.electron_share_of_deposited_energy, 2)} of its energy in electrons. The budget then follows: a 10 µA beam on a 1 µm foil gives ${ab.alphas_per_s.toExponential(1)} alphas per second (assuming σ ≈ 1.2 b). Even with no target losses this sustains only ${ab.alpha_density_slowing_limited_m3.toExponential(1)} m⁻³, against ${ab.alpha_density_required_at_bench_density_m3.toExponential(0)} m⁻³ needed to match the 2% alpha fraction of the PARC-Delta reference IBW case. The conclusion is insensitive to the cross-section: it holds for any value within a factor of ten.`));
  children.push(...await figure("sim/out/fig_bench_slowing_down.png", "Figure 14 — Mean alpha energy versus time in the bench plasma."));
  children.push(...await figure("sim/out/fig_alpha_budget.png", "Figure 15 — Achievable fast-alpha density versus the density needed to drive IBWs."));
  children.push(H2("5.5 RF channel plan (T10)"));
  const rm = bench.resonance_map;
  children.push(P(`At B0 = 3 T the alpha and proton cyclotron frequencies are ${rm.f_c_alpha_MHz.toFixed(1)} MHz and ${rm.f_c_proton_MHz.toFixed(1)} MHz, and the lower-hybrid frequency is ${rm.f_lower_hybrid_MHz.toFixed(0)} MHz. Because the alpha charge-to-mass ratio is 0.503 of the proton’s, even alpha harmonics nearly coincide with proton harmonics — the physical basis of alpha-to-proton channeling. The four channels sit between alpha harmonics, and because B varies along the axis each channel’s resonance layers sit at definite positions that move when the frequency is retuned. That motion is the scheduler’s actuator.`));
  children.push(...await figure("sim/out/fig_resonance_map.png", "Figure 16 — Cyclotron harmonics along the axis, channel frequencies and resonance layers."));
  children.push(H2("5.6 CAD integrity (T11)"));
  children.push(P(`The build123d model contains ${R.cad.part_count} labelled parts in 14 material groups and exports to STEP; the CADCraft drawing, the Blender renders and all simulations read the same parameters. The close-up below shows the in-vessel hardware: Faraday-shielded IBW straps and the target insertion arm.`));
  children.push(...await figure("docs/img/pdx1_detail_annotated.jpg", "Figure 17 — In-vessel detail: IBW straps with Faraday screens, target arm and simulated alpha orbits."));
  children.push(pb());

  // ---------------------------------------------------------------- 6 decisions
  children.push(H1("6. Decisions the tests forced"));
  children.push(table(["Test finding", "Decision"], [
    ["~10 T on mirror windings (T4)", "Baseline magnet changed from NbTi at 4.2 K to REBCO HTS at 20 K, conduction-cooled (no liquid helium)."],
    ["76% wall loss at 1 T, 0.1% at 3 T (T6)", "Design field fixed at B0 = 3 T with a 250 mm limiter radius."],
    ["38% target re-intersection within 4 µs (T7)", "On-axis foil kept for Phase 1 source measurements; trapped-alpha studies need a pulsed, retractable or gas/pellet boron target."],
    ["~10⁹× alpha-density shortfall (T9)", "Phase 1 validates the alpha birth spectrum; Phase 2 adds a surrogate energetic-ion ring; blanked port D4 reserved for it."],
    ["99.9% of bench alpha energy to electrons (T8)", "Proton-heating diagnostics must resolve small signals against an electron-dominated baseline; RF on/off modulation planned."],
  ], [3600, 5760]));
  children.push(caption("Table 4 — Each row is a design change or plan change caused by a specific test."));

  // ---------------------------------------------------------------- 7 open questions
  children.push(H1("7. Open questions from testing"));
  children.push(P("These are the questions the tests raised and that we have not yet answered. We list them because they are where the next work — and most of the technical risk — sits."));
  children.push(table(["#", "Topic", "Question"], R.open_questions.map((q, i) => [String(i + 1), q.topic, q.question]), [500, 2200, 6660]));
  children.push(caption("Table 5 — Open questions and risks."));
  children.push(pb());

  // ---------------------------------------------------------------- 8 roadmap
  children.push(H1("8. Roadmap"));
  children.push(...await figure("diagrams/out/d5_roadmap.png", "Figure 18 — Staged plan; each phase ends with a falsifiable exit test."));
  children.push(table(["Phase", "Scope", "Exit test"], [
    ["0 · now", "PARC-Delta v1.6; PDX-1 CAD and device simulations; this report", "Close the TA/Nanbu 6–7% energy-transfer gap; multi-seed uncertainty"],
    ["1", "HTS mirror, 0.7 MV beam line, foil target, Si α-spectrometer", "Measured α birth spectrum matches the source model within ±10%"],
    ["2", "Surrogate energetic-ion ring; 4-channel IBW array; FPGA scheduler", "Multi-mode scheduler (B2) beats no-channeling (B0) and single-mode (B1) beyond uncertainty at equal RF power"],
    ["3", "Nonlinear PIC benchmark; irreversible-heating measurement; scale study", "Go / no-go on a scaled device based on Gates 3–5"],
  ], [1300, 4300, 3760]));
  children.push(caption("Table 6 — Phases and exit tests. Budgets and schedules require vendor quotes and are not estimated in this report."));

  // ---------------------------------------------------------------- 9 claims boundary
  children.push(H1("9. Claims boundary"));
  [
    "PDX-1 is a concept research instrument. It is not a reactor design and is not engineered for fabrication; structural, thermal, vacuum, quench-protection and radiation-safety analyses are outstanding.",
    "No result here establishes fusion gain, net electricity, low-cost power or a new energy-generation mechanism.",
    "Alpha channeling with IBWs, two-wave channeling and pole-resonance channeling are prior art. PARC-Delta’s novelty, if any, lies only in the specific closed-loop scheduler, and must be confirmed by a claim-chart review.",
    "Device simulations are collisionless orbit, magnetostatic and expected-drag calculations with the caveats stated in each output file.",
  ].forEach((x) => children.push(bullet(x)));

  // ---------------------------------------------------------------- appendix
  children.push(H1("Appendix A. Reproducing this report"));
  children.push(P("All files live on the project SSD under /Volumes/Aditya ssd/PARC-Delta-Lab. After sourcing tools/env.sh:"));
  [
    "pytest -q  (in PARC-Delta-v1.6)  →  76 tests",
    "python scripts_run_v16.py  (in runs/v16_rerun)  →  v1.6 results",
    "python prototype/sim/magnet_field.py, alpha_orbits.py, bench_physics.py  →  device simulations",
    "python prototype/cad/pdx1_model.py  →  STEP + STL;  python prototype/drawings/make_ga_drawing.py  →  CADCraft drawing",
    "$BLENDER -b --factory-startup -P prototype/renders/blender_scene.py -- hero  →  renders",
    "python prototype/report/collect_results.py  →  results_summary.json used by this document",
  ].forEach((x) => children.push(bullet([t(x, { font: "Courier New", size: 18 })])));
  children.push(H1("Appendix B. References"));
  [
    "N. J. Fisch, “Alpha power channeling using ion-Bernstein waves,” Physics of Plasmas 2, 2375 (1995). doi:10.1063/1.871454",
    "N. J. Fisch and M. C. Herrmann, “Alpha power channelling with two waves,” Nuclear Fusion 35, 1753 (1995). doi:10.1088/0029-5515/35/12/I40",
    "H. Qin and N. J. Fisch, “Thresholdless IBW emission and alpha-to-thermal-ion energy channeling via pole resonance of fusion-product ions,” arXiv:2609.07732 (2026).",
    "Y. Liu et al., “Energization of proton via beam-driven ion Bernstein waves in p11B plasmas,” arXiv:2603.02728 (2026).",
    "PARC-Delta v1.6 release report and acceptance gates (docs/ACCEPTANCE_GATES.md).",
  ].forEach((x) => children.push(bullet(x)));

  const doc = new Document({
    creator: "PARC-Delta", title: "PDX-1 Prototype: CAD, Simulation and Test Report", description: "Investor technical report",
    styles: {
      default: { document: { run: { font: "Calibri", size: 22 } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 36, bold: true, color: NAVY, font: "Calibri" }, paragraph: { spacing: { before: 360, after: 180 }, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, color: BLUE, font: "Calibri" }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
      ],
    },
    numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
    sections: [{
      properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, right: 1440, bottom: 1300, left: 1440 } } },
      headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "PARC-Delta · PDX-1 CAD, Simulation and Test Report", font: "Calibri", size: 16, color: MUTED })] })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }], children: [
        new TextRun({ text: "Concept study · not a reactor design · " + R.date, font: "Calibri", size: 16, color: MUTED }),
        new TextRun({ children: ["\tPage ", PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES], font: "Calibri", size: 16, color: MUTED })] })] }) },
      children,
    }],
  });
  const buf = await Packer.toBuffer(doc);
  const out = path.join(OUT, "PARC-Delta_PDX-1_Test_Report.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", out, (buf.length / 1e6).toFixed(1), "MB");
}

build().catch((e) => { console.error(e); process.exit(1); });
