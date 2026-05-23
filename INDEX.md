# BlackHole Beacon — Project Index
*Generated: 2026-05-21 19:10*

## Current Status

```
Data collection: 1400/2529 anchors processed (55.4%)
399 anchors with 2MASS/WISE matches
Background batch still running (PID ~2500)
```

## Pipeline

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Fetch    │ →  │ Cross-   │ →  │ Feature  │ →  │ Classify │
│ Catalog  │    │ match    │    │ Extract  │    │ + Score  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

## Directory Layout

```
blackhole-beacon/
├── IMPLEMENTATION.md        — Project blueprint (Phase 1-3)
├── catalog/                 — Anchor catalogs
│   ├── psrcat_catalog.csv   — 2,530 pulsars (coordinated)
│   ├── bh_xrb_catalog.csv   — 28 BH X-ray binaries
│   ├── smbh_catalog.csv     — 32 SMBH
│   └── gwtc_bbh_all.csv     — 83 GWTC BBH mergers
├── queries/                 — Analysis pipeline scripts
│   ├── batch_resumable.py   — 🔄 Background batch cross-match
│   ├── multi_archive.py     — IRAS + ZTF + ROSAT engine
│   ├── phase1_analysis.py   — Stats + coverage report
│   ├── phase2_variability.py— Cross-epoch (13yr baseline)
│   ├── phase3_scoring.py    — Candidate ranking
│   ├── spectral_features.py — Multi-band SED extraction
│   ├── spectral_classifier.py— ML classifier + anomaly detection
│   ├── sed_decomposer.py    — Physical component breakdown
│   ├── simbad_comparison.py — New survey cross-compare
│   ├── gaia_comparison.py   — Gaia DR3 query (TAP inaccessible)
│   └── parse_votable_binary.py — Simbad BINARY parser
└── data/
    ├── crossmatch_phase1_v1.json    — 402 anchors, 1,354 sources
    ├── phase2_variability.json      — 262 anchors × 332 pairs
    ├── phase3_candidates.json       — 454 ranked candidates
    ├── spectral_features.json       — 402 SED vectors
    ├── sed_components.json          — BB/PL/dust decomposition
    ├── classifier_model.json        — PCA + RF metadata
    └── _checkpoint.json             — Batch resume checkpoint
```

## Key Findings (50% data)

| Metric | Value |
|--------|-------|
| Anchors with data | 402 |
| 2MASS | 300 anchors, 775 sources |
| WISE | 364 anchors, 579 sources |
| Both bands | 262 anchors |
| Proper motion candidates | 48 (max 227 mas/yr) |
| WISE IR excess | 29 |
| SED outliers (IsolationForest) | 21 |
| PCA variance explained | 76.7% (3 components) |

## What's Still Running

- **batch_resumable.py**: 1400/2529 → continuing (IRSA)
- **multi_archive.py**: Ready, waiting for batch to finish
- **IRAS / ZTF / ROSAT**: Not yet queried
- **BH XRB + SMBH data**: In batch's second half

## Data Size

~2 MB analysis data | ~600 KB checkpoint | 60 KB logs
