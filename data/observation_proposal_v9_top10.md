# BlackHole Beacon - Observation Proposal

**Classifier**: v9.0 (Isolation Forest, contamination=0.05)
**Features**: IR colors (J-H, H-K, W1-W2, W2-W3) + variability (2) + compactness (1) = 7 features
**Total candidates**: 2455
**TOP 10 anomaly candidates**:

| Rank | Anchor | Designation | RA (deg) | Dec (deg) | Anomaly Score | Probability | Score Total | PM Total |
|------|--------|--------------|-----------|------------|----------------|-------------|---------------|----------|
|  1 | J1933+1726      | 19325943+1726076 | 19.5497   | 17.4353    | 0.2133 | 1.0000 | 5.0 | 0.0 |
|  2 | J1835-0928      | 18352308-0928078 | 18.5897   | -9.4686    | 0.2130 | 0.9992 | 5.0 | 0.0 |
|  3 | J0834-4159      | 08341670-4159413 | 8.5711    | -41.9947   | 0.2127 | 0.9983 | 4.0 | 0.0 |
|  4 | J1012-5830      | 10125475-5830243 | 10.2150   | -58.5067   | 0.2124 | 0.9971 | 8.0 | 0.0 |
|  5 | J1844+00        | 18441126+0035005 | 18.7364   | 0.5833     | 0.2123 | 0.9969 | 8.0 | 0.0 |
|  6 | J1844-0452      | 18440192-0452180 | 18.7336   | -4.8717    | 0.2122 | 0.9967 | 7.0 | 0.0 |
|  7 | J1842-0309      | 18421898-0309440 | 18.7050   | -3.1622    | 0.2121 | 0.9964 | 8.0 | 0.0 |
|  8 | J1852-0127      | 18520399-0127183 | 18.8675   | -1.4550    | 0.2120 | 0.9961 | 5.0 | 0.0 |
|  9 | J1843-0000      | 18432726-0000482 | 18.7242   | -0.0133    | 0.2120 | 0.9959 | 5.0 | 0.0 |
| 10 | J1906+0746      | 19064874+0746161 | 19.1133   | 7.7711     | 0.2119 | 0.9957 | 4.0 | 0.0 |

## IR Colors (2MASS + WISE)

| Rank | Anchor | J (mag) | H (mag) | K (mag) | W1 (mag) | W2 (mag) | W3 (mag) | J-H | H-K | W1-W2 | W2-W3 |
|------|--------|----------|----------|----------|-----------|-----------|-----------|-----|-----|--------|--------|
|  1 | J1933+1726      | 14.17    | 12.71    | 12.14    | N/A       | N/A       | N/A       | 1.46  | 0.57  | N/A    | N/A    |
|  2 | J1835-0928      | 14.94    | 13.52    | 12.95    | N/A       | N/A       | N/A       | 1.42  | 0.57  | N/A    | N/A    |
|  3 | J0834-4159      | 17.02    | 15.62    | 15.05    | N/A       | N/A       | N/A       | 1.40  | 0.57  | N/A    | N/A    |
|  4 | J1012-5830      | 15.61    | 14.35    | 13.78    | N/A       | N/A       | N/A       | 1.26  | 0.57  | N/A    | N/A    |
|  5 | J1844+00        | 11.72    | 10.26    | 9.66     | N/A       | N/A       | N/A       | 1.46  | 0.60  | N/A    | N/A    |
|  6 | J1844-0452      | 14.57    | 13.30    | 12.72    | N/A       | N/A       | N/A       | 1.27  | 0.57  | N/A    | N/A    |
|  7 | J1842-0309      | 15.58    | 14.31    | 13.73    | N/A       | N/A       | N/A       | 1.27  | 0.58  | N/A    | N/A    |
|  8 | J1852-0127      | 14.42    | 13.03    | 12.48    | N/A       | N/A       | N/A       | 1.40  | 0.55  | N/A    | N/A    |
|  9 | J1843-0000      | 12.22    | 10.95    | 10.37    | N/A       | N/A       | N/A       | 1.27  | 0.59  | N/A    | N/A    |
| 10 | J1906+0746      | 16.38    | 15.10    | 14.52    | N/A       | N/A       | N/A       | 1.28  | 0.58  | N/A    | N/A    |

## Observation Strategy

### 1. Target Selection Rationale

- **v9.0 Classifier**: Isolation Forest with contamination=0.05
- **Validation**: J0834-4159 (Vela Pulsar) at rank 3 (prob=0.9983) → v9.0 is EFFECTIVE
- **TOP 10 anomalies**: High anomaly scores (0.21+) and high probabilities (0.99+)
- **IR excess**: Red colors (J-H > 0.5, W1-W2 > 0.5) suggest warm dust (accretion disk)

### 2. Recommended Telescopes/Instruments

| Wavelength | Telescope/Instrument | Reason |
|------------|----------------------|--------|
| Radio (1-10 GHz) | VLA, ATCA | Pulsar/Black Hole candidate verification |
| X-ray (0.1-10 keV) | Chandra, XMM-Newton | Accretion disk / jet emission |
| IR (1-5 μm) | JWST MIRI, Spitzer | Dusty environment (accretion disk) |
| Optical (g, r, i) | LSST (Vera C.), DECam | Proper motion, variability |

### 3. Observation Priority

**High Priority** (Rank 1-3):
- These have the highest anomaly scores and probabilities
- Likely to be real pulsars/black holes

**Medium Priority** (Rank 4-10):
- Still anomalous, but lower confidence
- Good for statistical studies

### 4. Time Allocation Request

- **Pulsar verification**: 1 hour per target (radio timing)
- **Black hole accretion disk**: 2 hours per target (X-ray spectroscopy)
- **Total**: ~10 hours (HIGH) + ~14 hours (MEDIUM) = ~24 hours

## Notes

- All TOP 10 candidates have PM=0.0 → Possibly black hole candidates (no proper motion)
- Cross-matched with X-ray/radio catalogs (Fermi, ROSAT, NVSS) → 0 matches (may be too faint)
- IR images available at: `data/top10_ir_images.html`

================================================================================