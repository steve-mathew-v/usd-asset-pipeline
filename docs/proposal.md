# MSc Project Proposal (Draft)

**Programme:** MSc Computer Animation and Visual Effects — NCCA, Bournemouth University
**Working title:** *A Lightweight USD-Based Asset Management Pipeline for Cross-DCC Collaboration in Small Studios*
**Author:** [your name]
**Date:** [date]

---

## 1. Abstract

Large studios manage shared assets through heavyweight pipeline systems (ShotGrid/Flow, Perforce, proprietary asset managers) that are expensive, complex, and assume dedicated pipeline staff. Small studios, student teams and freelancers typically fall back to manual file-sharing (cloud drives, naming conventions, messaging), which is error-prone and offers no versioning, no "approved" state, and no cross-application consistency.

This project investigates how a lightweight, self-hostable asset pipeline built on OpenUSD can support reliable cross-DCC asset exchange for small teams. A working client–server system will let an artist publish an asset from one DCC (e.g. Maya), have it reviewed and marked as approved, and have another artist load the latest approved version into a different DCC (e.g. Houdini) — with versioning and basic dependency awareness handled by the system rather than by convention. The system will be evaluated through structured user testing with artists and a comparison against the manual workflow it replaces.

## 2. Background and motivation

A precursor to this project (an `.obj`-based upload/download server with a Maya client) demonstrated the core idea but exposed its limits: `.obj` carries no materials, hierarchy, variants or layering, and the system had no versioning, weak authentication, and a single hard-coded DCC client. These limits are precisely the problems OpenUSD was designed to solve, which motivates rebuilding the interchange layer around USD.

OpenUSD has become the de facto interchange and composition standard across the industry (Pixar, NVIDIA Omniverse, and native support in Maya, Houdini, Unreal, Blender). Its layering and composition model (sublayers, references, payloads, variants) makes it well suited to a *publish/subscribe* asset workflow. However, most public discussion of USD pipelines assumes large-studio infrastructure. There is a gap — and a practical, examinable question — around what a *minimal viable* USD pipeline looks like for teams without that infrastructure.

## 3. Research question and objectives

**Research question:**
> Can a lightweight, USD-based asset management system provide reliable, versioned, cross-DCC asset exchange for small studios, and does it measurably improve on a manual file-sharing workflow in terms of usability and error reduction?

**Aims:**
- Design and build a self-hostable asset pipeline using USD as the interchange format.
- Support a genuine publish → review → consume workflow across at least two DCCs.
- Evaluate it against the manual workflow it is intended to replace.

**Objectives (measurable):**
1. Review existing asset-management approaches (large-studio tools, open-source tools such as Kitsu and Prism, and USD-based pipelines) and articulate the gap.
2. Implement a server with authenticated, versioned asset storage and an "approved" state.
3. Implement USD publish/consume clients for **two** DCCs (Maya + Houdini proposed).
4. Implement asset versioning with the ability to consume "latest approved" or a pinned version.
5. Evaluate the system through user testing (task-based study + SUS usability questionnaire) and a comparative analysis against manual file-sharing.

## 4. Why USD (technical reality, not just a buzzword)

Moving from `.obj` to USD is the technical spine of the project. Concretely:

- **Interchange format:** assets stored as `.usd`/`.usdc` (and `.usdz` for self-contained packages) instead of `.obj`. This carries hierarchy, materials (UsdShade/MaterialX), and metadata that `.obj` cannot.
- **Composition for versioning:** rather than overwriting files, each publish writes a new versioned layer. A small, stable "asset stub" USD file *references* or *payloads* the current approved version, so consumers always point at the stub and the pipeline controls which version it resolves to.
- **Asset resolution:** investigate a custom USD Asset Resolver (Ar 2.0) so that a logical asset URI (e.g. `asset:robot/v-latest`) resolves to the correct file on the server — this is the "proper" USD way to do version pinning and is a strong technical contribution if achieved.
- **Per-DCC bridge:** export uses each DCC's native USD support (Maya `mayaUSDExport`, Houdini USD ROP / LOPs); import uses references/payloads rather than flattening. The server stays DCC-agnostic — it speaks HTTP and stores USD, exactly as the prototype's server was Maya-agnostic.

A realistic fallback if the custom resolver proves too large in scope: handle version resolution server-side (the client asks the server for "latest approved" and gets the right file), and document the resolver as future work. This keeps the project deliverable.

## 5. Methodology

- **Approach:** iterative, design-and-build (engineering) project with an empirical evaluation component.
- **Development:** Python; FastAPI server; USD via the `pxr` Python bindings; Maya and Houdini Python clients with Qt (PySide6) UIs; Docker for deployment; CI (GitHub Actions) running an automated test suite.
- **Evaluation:**
  - *Usability study:* 6–10 artists perform a fixed set of publish/consume tasks. Capture task completion time, success/error rates, and a standard **SUS** (System Usability Scale) questionnaire.
  - *Comparative analysis:* same tasks performed via manual file-sharing vs. the tool; compare errors (wrong version used, missing textures, naming mistakes) and time.
  - *Technical evaluation:* performance/scaling as asset count and size grow.

## 6. Scope

**In scope:** USD interchange; versioning with approved state; two DCC clients (Maya, Houdini); authentication; Docker deployment; automated tests; user evaluation.

**Out of scope (named as future work):** Substance/texture round-trip publishing; a full custom Ar 2.0 resolver (attempt as a stretch goal); render-farm or shot/sequence management; real-time multi-user editing; cloud-scale storage.

## 7. Provisional timeline (~14 weeks)

| Weeks | Work |
|-------|------|
| 1–2  | Literature & tools review; finalise research question with supervisor |
| 3–4  | Server: auth, versioned USD storage, approved state, tests + CI |
| 5–7  | Maya client: USD publish/consume, version selection |
| 8–9  | Houdini client: USD publish/consume |
| 10   | Versioning/resolution layer (server-side; resolver as stretch) |
| 11   | Docker deployment; harden; pilot the user study |
| 12–13| Run user study; gather and analyse data |
| 14   | Write-up, finalise thesis, prepare demo/viva |

## 8. Expected contributions

1. A working, self-hostable, open-source USD asset pipeline aimed specifically at small teams.
2. A design analysis of what a *minimal* USD pipeline requires, grounded in a review of existing systems.
3. Empirical evidence on whether such a tool improves usability and reduces errors versus manual workflows.

## 9. Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| USD learning curve / `pxr` build issues | Use prebuilt USD (pip `usd-core`, or Houdini/Maya's bundled USD); start with a USD spike in week 1 |
| Custom resolver too large | Fall back to server-side version resolution; document resolver as future work |
| Recruiting study participants | Recruit from NCCA cohort early; keep tasks short (~20 min) |
| Scope creep across DCCs | Lock to two DCCs; everything else is explicitly future work |

## 10. Initial references (to expand)

- Pixar / AOUSD — OpenUSD documentation and specification.
- NVIDIA — OpenUSD resources and Omniverse pipeline material.
- Autodesk — Maya USD documentation; SideFX — Houdini Solaris/LOPs and USD documentation.
- Kitsu (CGWire) and Prism Pipeline — open-source asset/production management tools (for the comparative review).
- Brooke, J. (1996). *SUS: A 'quick and dirty' usability scale.* (evaluation methodology)
- Pipeline/asset-management literature and post-mortems (to be gathered in the review).
