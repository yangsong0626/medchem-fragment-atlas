# Fragment ADMET Case Studies

These case studies are association analyses. ADMET values are measured or curated on parent molecules containing a BRICS fragment, not on the isolated fragment itself.

## Case 1: `[*]N1CCC([*])CC1` and CL

- Direction: favorable association
- Endpoint/task: CL (mL/min/g), `clearance_microsome_az`
- Matched pairs: 155
- Parent median with fragment: 6.00
- Matched-control median: 32.0
- Favorability-adjusted median delta: 17.4
- Bootstrap median CI: 3.74 to 8.00
- Match distance median: 0.96

Interpretation: molecules containing `[*]N1CCC([*])CC1` show a favorable association for CL after nearest-neighbor matching on simple physicochemical descriptors. This should be treated as a triage hypothesis and checked in matched chemical series.

## Case 2: `[*]c1ccc([*])cc1` and CL

- Direction: favorable association
- Endpoint/task: CL (uL/min/10^6 cells), `clearance_hepatocyte_az`
- Matched pairs: 132
- Parent median with fragment: 15.7
- Matched-control median: 27.0
- Favorability-adjusted median delta: 6.43
- Bootstrap median CI: 12.9 to 19.5
- Match distance median: 0.55

Interpretation: molecules containing `[*]c1ccc([*])cc1` show a favorable association for CL after nearest-neighbor matching on simple physicochemical descriptors. This should be treated as a triage hypothesis and checked in matched chemical series.

## Case 3: `[*]N1CCN([*])C(=O)C1` and hERG

- Direction: favorable association
- Endpoint/task: hERG (safety class), `herg_karim`
- Matched pairs: 131
- Parent median with fragment: 1.00
- Matched-control median: 0.00
- Favorability-adjusted median delta: 1.00
- Bootstrap median CI: 1.00 to 1.00
- Match distance median: 0.50

Interpretation: molecules containing `[*]N1CCN([*])C(=O)C1` show a favorable association for hERG after nearest-neighbor matching on simple physicochemical descriptors. This should be treated as a triage hypothesis and checked in matched chemical series.

## Case 4: `[*]N(C)C` and Half-life

- Direction: favorable association
- Endpoint/task: Half-life (hr), `half_life_obach`
- Matched pairs: 53
- Parent median with fragment: 9.30
- Matched-control median: 7.00
- Favorability-adjusted median delta: 1.00
- Bootstrap median CI: 5.00 to 14.0
- Match distance median: 0.44

Interpretation: molecules containing `[*]N(C)C` show a favorable association for Half-life after nearest-neighbor matching on simple physicochemical descriptors. This should be treated as a triage hypothesis and checked in matched chemical series.

## Case 5: `[*]C(F)(F)F` and LD50

- Direction: favorable association
- Endpoint/task: LD50 (log(1/mol/kg)), `ld50_zhu`
- Matched pairs: 229
- Parent median with fragment: 3.66
- Matched-control median: 2.49
- Favorability-adjusted median delta: 0.91
- Bootstrap median CI: 3.52 to 3.86
- Match distance median: 0.41

Interpretation: molecules containing `[*]C(F)(F)F` show a favorable association for LD50 after nearest-neighbor matching on simple physicochemical descriptors. This should be treated as a triage hypothesis and checked in matched chemical series.

## Case 6: `[*]C(=O)C[*]` and CL

- Direction: unfavorable association
- Endpoint/task: CL (uL/min/10^6 cells), `clearance_hepatocyte_az`
- Matched pairs: 48
- Parent median with fragment: 70.6
- Matched-control median: 18.0
- Favorability-adjusted median delta: -40.9
- Bootstrap median CI: 57.6 to 95.5
- Match distance median: 0.56

Interpretation: molecules containing `[*]C(=O)C[*]` show an unfavorable association for CL after nearest-neighbor matching on simple physicochemical descriptors. This should be treated as a triage hypothesis and checked in matched chemical series.

## Case 7: `[*]N1CCN([*])CC1` and CL

- Direction: unfavorable association
- Endpoint/task: CL (mL/min/g), `clearance_microsome_az`
- Matched pairs: 41
- Parent median with fragment: 50.5
- Matched-control median: 11.2
- Favorability-adjusted median delta: -14.8
- Bootstrap median CI: 17.7 to 82.0
- Match distance median: 0.76

Interpretation: molecules containing `[*]N1CCN([*])CC1` show an unfavorable association for CL after nearest-neighbor matching on simple physicochemical descriptors. This should be treated as a triage hypothesis and checked in matched chemical series.

## Case 8: `[*]C1CC1` and Solubility

- Direction: unfavorable association
- Endpoint/task: Solubility (log mol/L), `solubility_aqsoldb`
- Matched pairs: 41
- Parent median with fragment: -4.05
- Matched-control median: -3.13
- Favorability-adjusted median delta: -1.01
- Bootstrap median CI: -4.59 to -3.52
- Match distance median: 0.20

Interpretation: molecules containing `[*]C1CC1` show an unfavorable association for Solubility after nearest-neighbor matching on simple physicochemical descriptors. This should be treated as a triage hypothesis and checked in matched chemical series.

## Case 9: `[*]c1c[nH]c([*])n1` and hERG

- Direction: unfavorable association
- Endpoint/task: hERG (safety class), `herg_karim`
- Matched pairs: 132
- Parent median with fragment: 0.00
- Matched-control median: 1.00
- Favorability-adjusted median delta: -1.00
- Bootstrap median CI: 0.00 to 0.00
- Match distance median: 0.69

Interpretation: molecules containing `[*]c1c[nH]c([*])n1` show an unfavorable association for hERG after nearest-neighbor matching on simple physicochemical descriptors. This should be treated as a triage hypothesis and checked in matched chemical series.

## Case 10: `[*]c1ccc([N+](=O)[O-])cc1` and hERG

- Direction: unfavorable association
- Endpoint/task: hERG (safety class), `herg_karim`
- Matched pairs: 47
- Parent median with fragment: 0.00
- Matched-control median: 1.00
- Favorability-adjusted median delta: -1.00
- Bootstrap median CI: 0.00 to 0.00
- Match distance median: 0.82

Interpretation: molecules containing `[*]c1ccc([N+](=O)[O-])cc1` show an unfavorable association for hERG after nearest-neighbor matching on simple physicochemical descriptors. This should be treated as a triage hypothesis and checked in matched chemical series.
