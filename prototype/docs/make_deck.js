// PARC-Delta / PDX-1 investor deck (.pptx) — structured pptxgenjs deck with native charts.
const fs = require("fs");
const path = require("path");
const sharp = require("sharp");
const pptxgen = require("pptxgenjs");
const SKILL = process.env.PPTX_SKILL;
const { applyTheme } = require(path.join(SKILL, "scripts/apply_theme.js"));

const PROTO = path.resolve(__dirname, "..");
const R = JSON.parse(fs.readFileSync(path.join(PROTO, "report/out/results_summary.json"), "utf8"));
const OUT = path.join(PROTO, "docs/out");
const IMG = (rel) => path.join(PROTO, rel);

const THEME = {
  name: "PARC-Delta Plasma", headFontFace: "Arial", bodyFontFace: "Calibri",
  colors: { dk1: "0D1628", lt1: "FFFFFF", dk2: "1D2433", lt2: "EEF2FA", accent1: "E8833A", accent2: "2456C7",
            accent3: "7A4FB5", accent4: "2E8B57", accent5: "B23A48", accent6: "7F93B8", hlink: "2456C7", folHlink: "7A4FB5" },
};
const HX = THEME.colors;
const MUTED_HEX = "6B7385";

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.title = "PARC-Delta — PDX-1 prototype: CAD, simulation and test results";
  pres.author = "PARC-Delta";
  const C = pres.SchemeColor;

  // ------------------------------------------------------------------ layouts
  const footer = (dark) => [
    { text: { text: "PARC-Delta · PDX-1 concept study · not a reactor design", options: { x: 0.6, y: 7.02, w: 8, h: 0.3, fontSize: 10, color: dark ? C.accent6 : C.text2, margin: 0 } } },
  ];
  pres.defineSlideMaster({
    title: "TITLE_DARK", background: { color: C.text1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 2.1, w: 7.6, h: 1.5, fontSize: 54, bold: true, color: C.background1, valign: "bottom", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.7, y: 3.75, w: 7.2, h: 1.6, fontSize: 22, color: C.background2, valign: "top", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "CONTENT", background: { color: C.background1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.85, fontSize: 32, bold: true, color: C.text1, valign: "middle", margin: 0 }, text: "" } },
      ...footer(false),
    ],
    slideNumber: { x: 12.2, y: 7.02, w: 0.5, h: 0.3, fontSize: 10, color: C.text2, align: "right" },
  });
  pres.defineSlideMaster({
    title: "CONTENT_DARK", background: { color: C.text1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.85, fontSize: 32, bold: true, color: C.background1, valign: "middle", margin: 0 }, text: "" } },
      ...footer(true),
    ],
    slideNumber: { x: 12.2, y: 7.02, w: 0.5, h: 0.3, fontSize: 10, color: C.accent6, align: "right" },
  });

  // ------------------------------------------------------------------ helpers
  async function fit(slide, rel, x, y, w, h, name, align = "center") {
    const m = await sharp(IMG(rel)).metadata();
    const s = Math.min(w / m.width, h / m.height);
    const iw = m.width * s, ih = m.height * s;
    const ix = align === "left" ? x : x + (w - iw) / 2;
    slide.addImage({ path: IMG(rel), x: ix, y: y + (h - ih) / 2, w: iw, h: ih, objectName: name, altText: name });
    return { x: ix, y: y + (h - ih) / 2, w: iw, h: ih };
  }
  function stat(slide, x, y, w, big, small, opts = {}) {
    slide.addText(big, { x, y, w, h: 0.75, fontSize: opts.size || 36, bold: true, color: opts.color || C.accent2, margin: 0, isTextBox: true, objectName: `stat ${big}`, fontFace: THEME.headFontFace });
    slide.addText(small, { x, y: y + 0.75, w, h: 0.62, fontSize: 13, color: opts.small || C.text2, margin: 0, valign: "top", isTextBox: true, objectName: `stat label ${big}` });
  }
  function card(slide, x, y, w, h, head, body, tone = "lt", name = "card") {
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: tone === "lt" ? C.background2 : C.text2 }, line: { color: tone === "lt" ? C.background2 : C.text2 }, objectName: name });
    slide.addText([{ text: head, options: { bold: true, fontSize: 15, color: tone === "lt" ? C.text1 : C.background1, breakLine: true } },
                   { text: body, options: { fontSize: 13, color: tone === "lt" ? C.text2 : C.background2 } }],
      { x: x + 0.18, y: y + 0.12, w: w - 0.36, h: h - 0.24, valign: "top", margin: 0, isTextBox: true, paraSpaceAfter: 4, objectName: name + " text" });
  }
  function numbered(slide, x, y, n, color) {
    slide.addShape(pres.shapes.OVAL, { x, y, w: 0.46, h: 0.46, fill: { color }, line: { color }, objectName: `badge ${n}` });
    slide.addText(String(n), { x, y, w: 0.46, h: 0.46, fontSize: 15, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: `badge text ${n}` });
  }
  const chartText = { catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", titleFontFace: "+mn-lt", legendFontFace: "+mn-lt",
    catAxisLabelColor: MUTED_HEX, valAxisLabelColor: MUTED_HEX, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, dataLabelFontSize: 11, legendFontSize: 12, titleFontSize: 14, titleColor: HX.dk2 };

  const orb = R.orbits, mag = R.magnet, bench = R.bench, s3 = orb.scan["3.0T"];
  const pct = (x, d = 1) => (x * 100).toFixed(d) + "%";

  // ================================================================== 1 title
  pres.addSection({ title: "Opening" });
  let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Opening" });
  s.addImage({ path: IMG("docs/img/pdx1_hero.jpg"), x: 4.2, y: 0, w: 13.333 - 4.2 + 2.3, h: 7.5, transparency: 10, objectName: "hero render" });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 8.6, h: 7.5, fill: { color: C.text1, transparency: 12 }, line: { color: C.text1, transparency: 100 }, objectName: "title scrim" });
  s.addText("PARC-Delta", { placeholder: "title" });
  s.addText("PDX-1 prototype — CAD design, simulation and test results", { placeholder: "body" });
  s.addText("Steering fusion-alpha energy into fuel ions · concept study · 1 November 2026", { x: 0.7, y: 6.3, w: 7.5, h: 0.4, fontSize: 14, color: C.accent1, margin: 0, isTextBox: true, objectName: "tagline" });
  s.addNotes("PARC-Delta is a research model for alpha channeling in proton-boron fusion. This deck shows the PDX-1 prototype concept we designed, simulated and rendered, how we tested it, what the tests showed and what is still open.");

  // ================================================================== 2 problem
  pres.addSection({ title: "Problem and approach" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem and approach" });
  s.addText("Most fusion-alpha energy heats electrons, not fuel", { placeholder: "title" });
  const sd = bench.slowing_down["3.12MeV"];
  s.addChart(pres.charts.BAR, [
    { name: "Electrons", labels: ["Reactor-like plasma (10 keV)", "PDX-1 bench plasma (10 eV)"], values: [73.0, +(sd.electron_share_of_deposited_energy * 100).toFixed(2)] },
    { name: "Protons", labels: ["Reactor-like plasma (10 keV)", "PDX-1 bench plasma (10 eV)"], values: [26.5, +(sd.proton_share_of_deposited_energy * 100).toFixed(2)] },
    { name: "Thermal alphas", labels: ["Reactor-like plasma (10 keV)", "PDX-1 bench plasma (10 eV)"], values: [0.6, 0] },
  ], { x: 0.6, y: 1.5, w: 7.6, h: 4.9, barDir: "bar", barGrouping: "percentStacked", chartColors: [HX.accent6, HX.accent2, HX.accent1],
       showValue: true, dataLabelPosition: "ctr", dataLabelColor: "FFFFFF", dataLabelFormatCode: "0.#", showLegend: true, legendPos: "b",
       showTitle: true, title: "Share of alpha energy deposited (%) — PARC-Delta v1.6 Rosenbluth solver", valGridLine: { color: "E3E6EC", size: 0.5 },
       catGridLine: { style: "none" }, valAxisHidden: true, ...chartText, objectName: "energy partition chart" });
  stat(s, 8.8, 1.6, 4, "73%", "of alpha energy goes to electrons in a reactor-like 10 keV plasma (simulated)");
  stat(s, 8.8, 3.15, 4, "26–27%", "reaches the protons that sustain fusion", { color: C.accent1 });
  stat(s, 8.8, 4.7, 4, "8.7 MeV", "released per p–¹¹B reaction, carried by three alpha particles", { color: C.text1 });
  s.addNotes("The classical collisional path sends most alpha energy into electrons, where it is radiated away. This is the baseline any alpha-channeling scheme must beat. At bench temperatures it is almost all electrons.");

  // ================================================================== 3 approach
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem and approach" });
  s.addText("Our bet: a closed-loop scheduler for alpha channeling", { placeholder: "title" });
  await fit(s, "diagrams/out/d2_control_loop.png", 0.5, 1.35, 8.3, 5.45, "control loop diagram");
  card(s, 9.05, 1.45, 3.7, 2.55, "Prior art we build on", "Fisch 1995 (IBW channeling) · Fisch & Herrmann 1995 (two waves) · Qin & Fisch 2026 (pole resonance) · Liu et al. 2026 (beam-driven IBW cascade)", "lt", "prior art card");
  card(s, 9.05, 4.2, 3.7, 2.55, "What would prove us wrong", "Gain vanishes with collisions or saturation · proton energy stays coherent · a fixed multi-wave spectrum does as well", "dk", "falsifier card");
  s.addNotes("Alpha channeling itself is prior art. Our narrow hypothesis is that a distribution-aware closed-loop scheduler of multiple IBW modes beats no-channeling and single-mode baselines at equal RF power. We list the conditions that would falsify it.");

  // ================================================================== 4 PDX-1
  pres.addSection({ title: "What we built" });
  s = pres.addSlide({ masterName: "CONTENT_DARK", sectionTitle: "What we built" });
  s.addText("PDX-1: a 6.9 m test stand designed around the model", { placeholder: "title" });
  await fit(s, "docs/img/pdx1_hero_callouts.jpg", 0.6, 1.4, 9.7, 5.45, "PDX-1 annotated render", "left");
  stat(s, 10.6, 1.45, 2.4, `${mag.B0_on_axis_T.toFixed(1)} T`, "HTS mirror, ratio " + mag.mirror_ratio.toFixed(2), { color: C.accent1, small: C.background2, size: 32 });
  stat(s, 10.6, 2.85, 2.4, "0.675 MeV", "protons on a 1 µm ¹¹B foil", { color: C.accent1, small: C.background2, size: 32 });
  stat(s, 10.6, 4.25, 2.4, "4 channels", "IBW antennas, 57–127 MHz", { color: C.accent1, small: C.background2, size: 32 });
  stat(s, 10.6, 5.65, 2.4, `${R.cad.part_count} parts`, "labelled STEP assembly", { color: C.accent1, small: C.background2, size: 32 });
  s.addNotes("PDX-1 is a linear magnetic mirror: accelerator, helicon plasma source, boron-11 foil target at the centre of a 3 tesla HTS mirror, four IBW antennas, and diagnostics. Rendered in Blender from the build123d CAD model.");

  // ================================================================== 5 cutaway
  s = pres.addSlide({ masterName: "CONTENT_DARK", sectionTitle: "What we built" });
  s.addText("Inside: simulated alphas in the simulated field", { placeholder: "title" });
  await fit(s, "docs/img/pdx1_cutaway_callouts.jpg", 0.6, 1.4, 12.1, 5.45, "central cell cutaway");
  s.addNotes("The orange orbits are not artwork: they are full-orbit trajectories of alphas sampled from the PARC-Delta birth-source model and pushed through the magnet simulation's field. The purple column follows the simulated flux tube.");

  // ================================================================== 6 how we tested
  pres.addSection({ title: "How we tested" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "How we tested" });
  s.addText("How we tested: traceable, reproducible, cross-checked", { placeholder: "title" });
  const method = [
    ["Single source of truth", "One parameter file drives the CAD, the drawing and every simulation"],
    ["Independent re-execution", "Full v1.6 campaign re-run on a clean toolchain, compared value by value"],
    ["Analytic cross-checks first", "New solvers must reproduce a known answer (e.g. the magnetic loss cone)"],
    ["Use the programme's own physics", "Alphas from the PARC-Delta birth source, slowed with its Rosenbluth coefficients"],
    ["Stated caveats", "Every output lists assumptions; assumed constants are flagged and stress-tested"],
  ];
  method.forEach(([h, b], i) => {
    const y = 1.5 + i * 1.04;
    numbered(s, 0.6, y + 0.08, i + 1, C.accent2);
    s.addText([{ text: h, options: { bold: true, fontSize: 17, color: C.text1, breakLine: true } }, { text: b, options: { fontSize: 14, color: C.text2 } }],
      { x: 1.25, y, w: 6.6, h: 0.95, margin: 0, valign: "top", isTextBox: true, objectName: `method ${i + 1}` });
  });
  card(s, 8.4, 1.5, 4.3, 5.1, "Toolchain (all free / open source)",
    "PARC-Delta v1.6 · Python 3.12 · NumPy · SciPy · pytest\nmagpylib — magnetostatics\nBoris full-orbit pusher\nbuild123d / OpenCascade — 3D CAD, STEP\nCADCraft — A0 engineering drawing\nBlender 5.0 Cycles — renders\nFFmpeg — video", "lt", "toolchain card");
  s.addNotes("Our rule: a result only counts if it is traceable, reproducible and checked against something independent.");

  // ================================================================== 7 test matrix
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "How we tested" });
  s.addText("Eleven tests, four kinds of outcome", { placeholder: "title" });
  const short = {
    T1: "76 / 76 pass", T2: `max deviation ${R.reproducibility.max_rel_diff.toExponential(1)}`, T3: "TA/Nanbu capture 92.9 / 93.9%",
    T4: `${mag.B0_on_axis_T.toFixed(2)} T, ratio ${mag.mirror_ratio.toFixed(2)}, ~10 T winding → HTS`,
    T5: `${pct(s3.fractions.all["end loss"], 2)} vs ${pct(orb.fraction_in_loss_cone_at_birth, 2)} theory`,
    T6: `wall loss 76% at 1 T → ${pct(s3.fractions.all["limiter/wall"])} at 3 T`,
    T7: `${pct(s3.fractions.all["target hit"], 0)} re-hit target within 4 µs`,
    T8: `${sd.time_to_50keV_ms.toFixed(1)} ms; ${pct(sd.electron_share_of_deposited_energy, 1)} to electrons`,
    T9: `~10^${Math.round(Math.log10(bench.alpha_budget.shortfall_factor_best_case))}× short of IBW drive`,
    T10: "4 channels, 57.6–126.6 MHz", T11: `${R.cad.part_count} parts, one parameter file`,
  };
  const ST = { pass: ["PASS", HX.accent4], open: ["OPEN", HX.accent5], finding: ["FINDING", HX.accent1], "design change": ["DESIGN CHANGE", HX.accent2] };
  const rows = [[
    { text: "ID", options: { bold: true, color: "FFFFFF", fill: { color: HX.dk1 } } },
    { text: "What we tested", options: { bold: true, color: "FFFFFF", fill: { color: HX.dk1 } } },
    { text: "Result", options: { bold: true, color: "FFFFFF", fill: { color: HX.dk1 } } },
    { text: "Outcome", options: { bold: true, color: "FFFFFF", fill: { color: HX.dk1 } } },
  ]];
  R.tests.forEach((x, i) => {
    const fill = { color: i % 2 ? "F7F9FC" : "FFFFFF" };
    rows.push([
      { text: x.id, options: { bold: true, fill } }, { text: x.what, options: { fill } }, { text: short[x.id], options: { fill } },
      { text: ST[x.status][0], options: { bold: true, color: ST[x.status][1], fill } },
    ]);
  });
  s.addTable(rows, { x: 0.6, y: 1.35, w: 12.1, colW: [0.7, 5.6, 4.05, 1.75], fontSize: 12, fontFace: THEME.bodyFontFace, color: HX.dk2,
    border: { type: "solid", pt: 0.5, color: "D5DAE3" }, rowH: 0.42, valign: "middle", margin: [0.04, 0.08, 0.04, 0.08], objectName: "test matrix" });
  s.addNotes("Full methodology and every caveat are in the Word report. Pass means agreement with a reference; finding means the result changed the plan; open means a documented unresolved discrepancy.");

  // ================================================================== 8 software validation
  pres.addSection({ title: "Results" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("The model reproduces to better than one part in a billion", { placeholder: "title" });
  stat(s, 0.6, 1.55, 3.6, "76 / 76", "unit and regression tests pass (13 s)");
  stat(s, 0.6, 3.05, 3.6, R.reproducibility.values_compared.toLocaleString("en-US"), `values re-computed across ${R.reproducibility.file_count} v1.6 result files`);
  stat(s, 0.6, 4.55, 3.6, R.reproducibility.max_rel_diff.toExponential(1), "worst relative deviation from the shipped release", { color: C.accent4 });
  s.addChart(pres.charts.LINE, [
    { name: "Takizuka–Abe", labels: ["K=1", "K=4", "K=8", "K=16", "K=32"], values: [52.85, 71.95, 79.33, 85.86, 92.89] },
    { name: "Nanbu", labels: ["K=1", "K=4", "K=8", "K=16", "K=32"], values: [60.46, 78.91, 85.24, 90.47, 93.88] },
    { name: "Rosenbluth reference", labels: ["K=1", "K=4", "K=8", "K=16", "K=32"], values: [100, 100, 100, 100, 100] },
  ], { x: 4.6, y: 1.45, w: 8.1, h: 5.2, chartColors: [HX.accent1, HX.accent3, HX.accent6], lineSize: 2.5, lineDataSymbol: "circle", lineDataSymbolSize: 7,
       showTitle: true, title: "Still open: % of reference alpha energy loss captured vs substeps K", valAxisMinVal: 40, valAxisMaxVal: 105,
       showValue: false, showLegend: true, legendPos: "b", valGridLine: { color: "E3E6EC", size: 0.5 }, catGridLine: { style: "none" }, ...chartText, objectName: "TA Nanbu chart" });
  s.addNotes("Everything reproduces. The one inherited open item is the full-mixture collision cross-check: even at 32 substeps the Monte Carlo samplers miss 6 to 7 percent of the reference energy loss. We report it rather than hide it.");

  // ================================================================== 9 magnet
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("Magnet simulation forced a switch to HTS", { placeholder: "title" });
  await fit(s, "sim/out/fig_magnet_axis.png", 0.5, 1.4, 8.6, 3.7, "on-axis field chart");
  await fit(s, "sim/out/fig_magnet_map.png", 0.5, 5.05, 8.6, 1.9, "field map");
  stat(s, 9.5, 1.5, 3.2, `${mag.B0_on_axis_T.toFixed(2)} T`, "centre field; mirror ratio " + mag.mirror_ratio.toFixed(2));
  stat(s, 9.5, 2.95, 3.2, `${mag.stored_magnetic_energy_MJ.toFixed(1)} MJ`, "stored magnetic energy");
  stat(s, 9.5, 4.4, 3.2, `~${mag.peak_field_at_conductor_T.toFixed(0)} T`, "on mirror windings → NbTi rejected, REBCO at 20 K adopted", { color: C.accent1 });
  s.addNotes("The coil currents were solved for 3 tesla and a 1.6 mirror ratio. The winding field of about 10 tesla is beyond practical niobium-titanium margins, so the baseline moved to REBCO high-temperature superconductor, conduction-cooled at 20 kelvin.");

  // ================================================================== 10 orbit validation
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("The orbit solver matches loss-cone theory", { placeholder: "title" });
  await fit(s, "sim/out/fig_alpha_phase_space.png", 0.5, 1.35, 8.2, 5.55, "phase space chart");
  stat(s, 9.1, 1.6, 3.6, pct(s3.fractions.all["end loss"], 2), "simulated end loss (4,200 alphas, 4 µs)");
  stat(s, 9.1, 3.1, 3.6, pct(orb.fraction_in_loss_cone_at_birth, 2), "analytic loss cone at birth", { color: C.accent4 });
  s.addText("Alphas are sampled from the PARC-Delta α0/α1 birth source and pushed with a 0.4 ns Boris integrator through the simulated field.",
    { x: 9.1, y: 4.65, w: 3.6, h: 1.4, fontSize: 14, color: C.text2, margin: 0, valign: "top", isTextBox: true, objectName: "orbit note" });
  s.addNotes("Before trusting the orbit code for design, we checked it against the textbook loss cone. The agreement is within 0.02 percentage points.");

  // ================================================================== 11 field choice
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("3 T keeps 99.9% of alphas off the wall", { placeholder: "title" });
  const Bs = ["1.0T", "2.0T", "3.0T", "4.0T"];
  const fate = (k) => Bs.map((b) => +(orb.scan[b].fractions.all[k] * 100).toFixed(1));
  s.addChart(pres.charts.BAR, [
    { name: "Confined", labels: ["1 T", "2 T", "3 T", "4 T"], values: fate("confined") },
    { name: "End loss", labels: ["1 T", "2 T", "3 T", "4 T"], values: fate("end loss") },
    { name: "Wall / limiter", labels: ["1 T", "2 T", "3 T", "4 T"], values: fate("limiter/wall") },
    { name: "Target hit", labels: ["1 T", "2 T", "3 T", "4 T"], values: fate("target hit") },
  ], { x: 0.6, y: 1.4, w: 7.9, h: 5.3, barDir: "col", barGrouping: "stacked", chartColors: [HX.accent4, HX.accent6, HX.accent1, HX.accent5],
       showValue: true, dataLabelPosition: "ctr", dataLabelColor: "FFFFFF", dataLabelFormatCode: "0", valAxisMaxVal: 100,
       showTitle: true, title: "Alpha fate after 4 µs (% of alphas) vs central field", showLegend: true, legendPos: "b",
       valGridLine: { color: "E3E6EC", size: 0.5 }, catGridLine: { style: "none" }, ...chartText, objectName: "fate vs field chart" });
  card(s, 8.9, 1.5, 3.8, 2.4, "Design point: B0 = 3 T", `Wall loss falls from ${fate("limiter/wall")[0]}% at 1 T to ${fate("limiter/wall")[2]}% at 3 T. Beyond 3 T more alphas stay near the axis and re-hit the target.`, "lt", "design point card");
  card(s, 8.9, 4.15, 3.8, 2.55, "Finding: the target is in the way", `Every orbit re-visits the axis, so ${fate("target hit")[2]}% hit the foil frame or arm within 4 µs. Moving the target off-axis trades target hits for wall hits.`, "dk", "target finding card");
  s.addNotes("The field scan fixed the design field. It also revealed a structural issue with an on-axis target, which changes how we plan the experiments.");

  // ================================================================== 12 alpha budget
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("Hard truth: beam-foil alphas are ~10⁹× too sparse", { placeholder: "title" });
  const ab = bench.alpha_budget;
  s.addChart(pres.charts.BAR, [{ name: "Fast-alpha density (m⁻³)", labels: ["Target-limited (on-axis foil)", "Slowing-limited (ideal)", "Needed for IBW drive"],
    values: [ab.alpha_density_target_limited_m3, ab.alpha_density_slowing_limited_m3, ab.alpha_density_required_at_bench_density_m3] }],
    { x: 0.6, y: 1.4, w: 7.4, h: 5.3, barDir: "col", chartColors: [HX.accent5, HX.accent1, HX.accent4], valAxisLogScaleBase: 10, valAxisMinVal: 100,
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0E+00", showLegend: false, showTitle: true, title: "Fast-alpha density, m⁻³ (log scale)",
      valGridLine: { color: "E3E6EC", size: 0.5 }, catGridLine: { style: "none" }, ...chartText, objectName: "alpha budget chart" });
  stat(s, 8.4, 1.5, 4.3, `~10^${Math.round(Math.log10(ab.shortfall_factor_best_case))}×`, "shortfall even with no target losses (10 µA, 1 µm foil, σ ≈ 1.2 b assumed)", { color: C.accent5 });
  card(s, 8.4, 3.15, 4.3, 3.5, "What we changed", "Phase 1 measures the alpha birth spectrum (validates the source model).\nPhase 2 adds a surrogate energetic-ion ring for wave-drive tests.\nTrapped-alpha work needs a pulsed, retractable or gas/pellet boron target.", "lt", "changes card");
  s.addNotes("This is the most important finding. A microamp beam on a foil makes roughly a billion times too few alphas to excite ion-Bernstein waves on their own. Finding it in simulation, before buying hardware, reshaped the plan.");

  // ================================================================== 13 RF
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("Retuning a channel moves its resonance layer", { placeholder: "title" });
  await fit(s, "sim/out/fig_resonance_map.png", 0.5, 1.35, 8.7, 5.5, "resonance map");
  const rm = bench.resonance_map;
  stat(s, 9.55, 1.5, 3.2, `${rm.f_c_alpha_MHz.toFixed(1)} MHz`, "alpha cyclotron frequency at 3 T");
  stat(s, 9.55, 2.95, 3.2, "2Ωα ≈ Ωp", "alpha and proton harmonics overlap: the basis of α→p channeling", { color: C.accent1, size: 30 });
  s.addText("A1 57.6 · A2 80.6 · A3 103.6 · A4 126.6 MHz. Because B varies along the axis, frequency is a position actuator for the scheduler.",
    { x: 9.55, y: 4.55, w: 3.2, h: 1.8, fontSize: 14, color: C.text2, margin: 0, valign: "top", isTextBox: true, objectName: "channel note" });
  s.addNotes("The channel plan sits between alpha harmonics. Retuning a channel shifts where it resonates along the machine, which is the knob the scheduler turns.");

  // ================================================================== 14 decisions
  pres.addSection({ title: "Decisions and risks" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Decisions and risks" });
  s.addText("Five decisions the tests forced", { placeholder: "title" });
  const dec = [
    ["~10 T on mirror windings", "NbTi → REBCO HTS at 20 K, conduction-cooled"],
    ["76% wall loss at 1 T, 0.1% at 3 T", "Design field fixed at 3 T, limiter at 250 mm"],
    ["38% target re-hit within 4 µs", "Pulsed / retractable / gas boron target for trapped-alpha work"],
    ["~10⁹× alpha-density shortfall", "Phase 1 = source validation; Phase 2 = surrogate ion ring"],
    ["99.9% bench energy to electrons", "RF on/off modulation for small proton-heating signals"],
  ];
  dec.forEach(([f, d], i) => {
    const y = 1.45 + i * 1.07;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 5.3, h: 0.86, rectRadius: 0.08, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: `finding ${i + 1}` });
    s.addText([{ text: "Test showed  ", options: { fontSize: 12, color: C.accent1, bold: true } }, { text: f, options: { fontSize: 15, color: C.text1, bold: true } }],
      { x: 0.8, y, w: 5.0, h: 0.86, valign: "middle", margin: 0, isTextBox: true, objectName: `finding text ${i + 1}` });
    s.addShape(pres.shapes.RIGHT_ARROW, { x: 6.1, y: y + 0.24, w: 0.6, h: 0.38, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: `arrow ${i + 1}` });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.9, y, w: 5.8, h: 0.86, rectRadius: 0.08, fill: { color: C.text1 }, line: { color: C.text1 }, objectName: `decision ${i + 1}` });
    s.addText([{ text: "So we  ", options: { fontSize: 12, color: C.accent1, bold: true } }, { text: d, options: { fontSize: 15, color: C.background1 } }],
      { x: 7.1, y, w: 5.5, h: 0.86, valign: "middle", margin: 0, isTextBox: true, objectName: `decision text ${i + 1}` });
  });
  s.addNotes("Each of these is a concrete change caused by a specific test. That is the value of doing the simulation before the hardware.");

  // ================================================================== 15 open questions
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Decisions and risks" });
  s.addText("What we still have to answer", { placeholder: "title" });
  const oq = [
    ["Collision closure", "Close the 6–7% TA/Nanbu energy-transfer gap (importance sampling of near-comoving electrons)"],
    ["Alpha drive source", "Which surrogate energetic-ion source reaches n_fast/n_p ≈ 1% at bench scale?"],
    ["Coherent vs irreversible", "Separate coherent proton response from real heating (Gate 4)"],
    ["Nonlinear physics", "Does the multi-mode gain survive saturation? PIC benchmark first (Gate 3)"],
    ["Magnet engineering", "~10 T REBCO windings, ~170 MPa screen: quench protection and FEA"],
    ["Radiation safety", "¹¹B(α,n)¹⁴N neutrons from alphas on boron need a dose assessment"],
  ];
  oq.forEach(([h, b], i) => {
    const x = 0.6 + (i % 3) * 4.1, y = 1.5 + Math.floor(i / 3) * 2.65;
    card(s, x, y, 3.85, 2.4, h, b, i === 1 ? "dk" : "lt", `question ${i + 1}`);
  });
  s.addText("Full list of 10 open questions, with how each will be tested, in the accompanying report.", { x: 0.6, y: 6.62, w: 12, h: 0.32, fontSize: 12, color: C.text2, italic: true, margin: 0, isTextBox: true, objectName: "questions note" });
  s.addNotes("These are where the technical risk sits. The highlighted one, a surrogate fast-ion source, is the critical path for testing the scheduler in hardware.");

  // ================================================================== 16 drawing
  pres.addSection({ title: "Engineering and plan" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Engineering and plan" });
  s.addText("CAD that engineers can review", { placeholder: "title" });
  await fit(s, "docs/img/PDX1-GA-001_paper_hi.jpg", 0.5, 1.35, 8.6, 5.55, "general arrangement drawing");
  card(s, 9.4, 1.45, 3.3, 5.3, "Deliverables", `STEP assembly, ${R.cad.part_count} labelled parts\nA0 GA drawing PDX1-GA-001 (DXF + PDF) from CADCraft\nBlender scene + photoreal renders\nTurntable + explainer video\nAll generated from one parameter file`, "lt", "deliverables card");
  s.addNotes("The general-arrangement drawing was produced headlessly in CADCraft from the same parameter file as the 3D model and simulations.");

  // ================================================================== 17 roadmap
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Engineering and plan" });
  s.addText("Each phase ends with a falsifiable exit test", { placeholder: "title" });
  const ph = [
    ["Phase 0 · now", "Model + concept", "v1.6, PDX-1 CAD and simulations", "Close TA/Nanbu gap", C.accent4],
    ["Phase 1", "Magnet + beam-target", "HTS mirror, 0.7 MV beam, Si spectrometer", "α birth spectrum within ±10%", C.accent2],
    ["Phase 2", "Fast-ion ring + IBW", "Surrogate ions, 4-channel array, scheduler", "B2 beats B0 and B1 at equal RF", C.accent1],
    ["Phase 3", "Nonlinear + scale", "PIC benchmark, irreversible heating", "Go / no-go on scale-up", C.accent3],
  ];
  ph.forEach(([p, t, scope, exit, col], i) => {
    const x = 0.6 + i * 3.1;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.6, w: 2.8, h: 4.6, rectRadius: 0.1, fill: { color: C.background2 }, line: { color: col, width: 1.5 }, objectName: `phase ${i}` });
    s.addText([{ text: p, options: { fontSize: 13, bold: true, color: col, breakLine: true } }, { text: t, options: { fontSize: 18, bold: true, color: C.text1, breakLine: true } },
               { text: " ", options: { fontSize: 8, breakLine: true } }, { text: scope, options: { fontSize: 14, color: C.text2 } }],
      { x: x + 0.2, y: 1.75, w: 2.4, h: 2.6, valign: "top", margin: 0, isTextBox: true, objectName: `phase text ${i}` });
    s.addText([{ text: "EXIT TEST", options: { fontSize: 11, bold: true, color: col, breakLine: true } }, { text: exit, options: { fontSize: 14, bold: true, color: C.text1 } }],
      { x: x + 0.2, y: 4.55, w: 2.4, h: 1.45, valign: "top", margin: 0, isTextBox: true, objectName: `exit text ${i}` });
    if (i < 3) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + 2.84, y: 3.7, w: 0.22, h: 0.36, fill: { color: C.text2 }, line: { color: C.text2 }, objectName: `phase arrow ${i}` });
  });
  s.addText("Budgets and schedules require vendor quotes and are not estimated here.", { x: 0.6, y: 6.45, w: 12, h: 0.32, fontSize: 12, italic: true, color: C.text2, margin: 0, isTextBox: true, objectName: "roadmap note" });
  s.addNotes("Every phase has an exit test that could stop us. That keeps the programme honest and capital-efficient.");

  // ================================================================== 18 closing
  pres.addSection({ title: "Close" });
  s = pres.addSlide({ masterName: "CONTENT_DARK", sectionTitle: "Close" });
  s.addText("What we claim — and what we don't", { placeholder: "title" });
  card(s, 0.6, 1.5, 5.9, 5.1, "We have shown", "A reproducible alpha-channeling research model (76/76 tests, rerun to 7.5e-10)\nA concept test stand whose geometry and physics come from one source\nA validated orbit solver and simulation-driven design decisions\nAn honest map of the hard problems, found before buying hardware", "dk", "claims card");
  card(s, 6.85, 1.5, 5.9, 5.1, "We do not claim", "Fusion gain, net electricity or low-cost power\nThat PDX-1 is a reactor or ready to fabricate\nThat the scheduler works — it is the hypothesis under test\nNovelty over the prior art on alpha channeling itself", "dk", "non-claims card");
  s.addNotes("Close on credibility: what is shown, what is not, and the next exit test.");

  const file = path.join(OUT, "PARC-Delta_PDX-1_Investor_Deck.pptx");
  await pres.writeFile({ fileName: file });
  await applyTheme(file, THEME);
  console.log("wrote", file);
}
main().catch((e) => { console.error(e); process.exit(1); });
