# Answer-Quality Ladder

Complete level sets: 40/40. Repeats: 5 at temperature 0.7. One shared question set per scenario and repeat; the levels differ only in the simulated expert's answers.

Levels: `L3` the frozen full-answer protocol; `L3p` the same information rephrased away from the reference wording; `L2` at most 25 words per answer; `L1` only the first half of the questions answered; `L0` vague answers with no specifics.

| Level | document coverage | field coverage | exact coverage | answer words | unsure answers |
|---|---|---|---|---|---|
| L3 | 0.857 ± 0.075 | 0.744 ± 0.080 | 0.510 ± 0.101 | 251.975 ± 34.477 | 0.000 ± 0.000 |
| L3p | 0.827 ± 0.084 | 0.594 ± 0.098 | 0.240 ± 0.068 | 279.125 ± 36.357 | 0.000 ± 0.000 |
| L2 | 0.783 ± 0.111 | 0.592 ± 0.104 | 0.347 ± 0.095 | 76.450 ± 17.817 | 0.000 ± 0.000 |
| L1 | 0.729 ± 0.108 | 0.544 ± 0.092 | 0.317 ± 0.084 | 148.025 ± 17.204 | 3.000 ± 0.000 |
| L0 | 0.577 ± 0.147 | 0.315 ± 0.122 | 0.103 ± 0.058 | 124.300 ± 13.708 | 0.000 ± 0.000 |

Values are mean ± standard deviation across scenarios and repeats.

## Paired difference from L3, bootstrap 95% CI

| Level | document coverage | field coverage | exact coverage |
|---|---|---|---|
| L3 - L3p | +0.030 [+0.005, +0.057] | +0.150 [+0.114, +0.185] | +0.269 [+0.237, +0.302] |
| L3 - L2 | +0.074 [+0.041, +0.107] | +0.152 [+0.115, +0.189] | +0.163 [+0.139, +0.184] |
| L3 - L1 | +0.128 [+0.090, +0.167] | +0.200 [+0.164, +0.235] | +0.193 [+0.161, +0.223] |
| L3 - L0 | +0.281 [+0.225, +0.333] | +0.428 [+0.374, +0.483] | +0.407 [+0.369, +0.442] |

A positive difference means the full-answer anchor scores higher than that level. The L3 - L3p row isolates how much of the anchor's coverage rests on the simulated expert reusing the reference vocabulary rather than on the information conveyed.

## Provenance of reference items by level

| Level | carried | lost | recovered | dropped | unsupported | missed |
|---|---|---|---|---|---|---|
| L3 | 2.600 ± 1.499 | 0.400 ± 0.672 | 18.250 ± 3.572 | 1.450 ± 1.260 | 1.150 ± 0.921 | 5.025 ± 2.094 |
| L3p | 2.150 ± 1.099 | 0.850 ± 1.051 | 12.500 ± 4.101 | 2.425 ± 1.866 | 2.900 ± 2.110 | 8.050 ± 2.828 |
| L2 | 2.200 ± 1.363 | 0.800 ± 0.883 | 12.250 ± 3.685 | 0.750 ± 1.149 | 3.275 ± 1.617 | 9.600 ± 2.808 |
| L1 | 2.450 ± 1.501 | 0.550 ± 0.677 | 11.250 ± 3.311 | 1.450 ± 1.300 | 2.550 ± 1.679 | 10.625 ± 3.256 |
| L0 | 2.200 ± 1.418 | 0.800 ± 0.791 | 0.375 ± 0.807 | 0.100 ± 0.304 | 6.925 ± 3.174 | 18.475 ± 4.057 |

Counts are per pipeline, under the within-field criterion.

## Limits

The ladder varies a simulated respondent, not real experts; L1 withholds the second half of the questions by position, which is a stand-in for partial knowledge rather than a model of it. Coverage stays lexical under every criterion and does not establish semantic correctness. Repeats estimate generation variance for these scenarios only; they do not add independent scenarios.

