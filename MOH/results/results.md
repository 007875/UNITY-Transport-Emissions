# UNITY v2 - generated results

Monte-Carlo samples: 3000, seed: 42. All inputs are placeholder assumptions (src/unity/params.py); these numbers demonstrate the framework, they are not validated findings.

## Trajectory checks

| scenario   |   target_speed |   realised_speed |   max_speed |   stops_per_100km |   max_acc |   max_dec |
|:-----------|---------------:|-----------------:|------------:|------------------:|----------:|----------:|
| S1         |             80 |            80.11 |        90   |               0   |       0.5 |      0.81 |
| S2         |             55 |            54.91 |        77.1 |              10   |       0.5 |      0.97 |
| S3         |             18 |            17.99 |        30.7 |             175.6 |       0.5 |      0.99 |
| S4         |             75 |            75.03 |        84.4 |               0   |       0.5 |      0.8  |

## Estimates by data level (kg CO2e per trip, WTW)

| scenario   | level   |   wtw_point_kg |   wtw_p5 |   wtw_p50 |   wtw_p95 |   wtw_rel_half_width |   ttw_point_kg |
|:-----------|:--------|---------------:|---------:|----------:|----------:|---------------------:|---------------:|
| S1         | low     |          102.3 |     72   |     103   |     148.9 |                0.374 |           83.3 |
| S1         | medium  |          112.7 |     81.9 |     112.7 |     155.4 |                0.326 |           91.8 |
| S1         | high    |          101.9 |     86.1 |     102.6 |     123   |                0.18  |           83   |
| S2         | low     |          102.3 |     72   |     103   |     148.9 |                0.374 |           83.3 |
| S2         | medium  |           94.9 |     68.9 |      94.9 |     130.8 |                0.326 |           77.3 |
| S2         | high    |          119.8 |    102.2 |     120.6 |     143.2 |                0.17  |           97.6 |
| S3         | low     |          102.3 |     72   |     103   |     148.9 |                0.374 |           83.3 |
| S3         | medium  |          129.9 |     94.4 |     130   |     179.1 |                0.326 |          105.8 |
| S3         | high    |          128.8 |    112.3 |     129.9 |     151.2 |                0.15  |          104.9 |
| S4         | low     |          507.4 |    357.2 |     510.9 |     738.8 |                0.373 |          413.3 |
| S4         | medium  |          532   |    386.6 |     531.9 |     733.3 |                0.326 |          433.3 |
| S4         | high    |          531.2 |    448.4 |     534.8 |     643.5 |                0.182 |          432.7 |

## Decision: road vs rail (per tonne, WTW; scenarios S1 and S4 shown)

| scenario   | road_level   | alternative     | nominal_winner   |   nominal_difference_pct |   p_wrong |   expected_regret_kg_per_t |   ratio_a_over_b_p5 |   ratio_a_over_b_p95 | robust   |
|:-----------|:-------------|:----------------|:-----------------|-------------------------:|----------:|---------------------------:|--------------------:|---------------------:|:---------|
| S1         | low          | Rail (electric) | B                |                    89.31 |     0     |                       0    |               4.825 |               18.696 | True     |
| S1         | medium       | Rail (electric) | B                |                    90.3  |     0     |                       0    |               5.467 |               20.008 | True     |
| S1         | high         | Rail (electric) | B                |                    89.27 |     0     |                       0    |               5.378 |               16.977 | True     |
| S1         | low          | Rail (diesel)   | B                |                    67.18 |     0     |                       0    |               1.757 |                5.437 | True     |
| S1         | medium       | Rail (diesel)   | B                |                    70.22 |     0     |                       0    |               2.002 |                5.828 | True     |
| S1         | high         | Rail (diesel)   | B                |                    67.06 |     0     |                       0    |               1.946 |                4.839 | True     |
| S4         | low          | Rail (electric) | B                |                    84.04 |     0     |                       0    |               3.228 |               12.504 | True     |
| S4         | medium       | Rail (electric) | B                |                    84.78 |     0     |                       0    |               3.488 |               12.661 | True     |
| S4         | high         | Rail (electric) | B                |                    84.76 |     0     |                       0    |               3.801 |               11.908 | True     |
| S4         | low          | Rail (diesel)   | B                |                    51    |     0.019 |                       0.04 |               1.188 |                3.594 | True     |
| S4         | medium       | Rail (diesel)   | B                |                    53.27 |     0.009 |                       0.02 |               1.285 |                3.681 | True     |
| S4         | high         | Rail (diesel)   | B                |                    53.2  |     0.002 |                       0.01 |               1.382 |                3.39  | True     |

## Routing decision: route A (100 km motorway, 80 km/h) vs route B (rural, 55 km/h, varying length)

signed_b_minus_a_pct < 0: B has lower nominal emissions. p_wrong = probability the nominal winner is truly worse INSIDE that level (parameter uncertainty only, paired draws). wrong_vs_high_reference = the level picks a different route than the high-data estimate (model-level error; high-data model used as reference, itself a placeholder).

|   dist_b_km | level   | nominal_winner   |   signed_b_minus_a_pct |   p_wrong | wrong_vs_high_reference   |   regret_vs_high_pct |
|------------:|:--------|:-----------------|-----------------------:|----------:|:--------------------------|---------------------:|
|        70   | low     | B                |                 -30    |     0     | False                     |                 0    |
|        70   | medium  | B                |                 -41.03 |     0     | False                     |                 0    |
|        70   | high    | B                |                 -22.94 |     0     | False                     |                 0    |
|        72.5 | low     | B                |                 -27.5  |     0     | False                     |                 0    |
|        72.5 | medium  | B                |                 -38.94 |     0     | False                     |                 0    |
|        72.5 | high    | B                |                 -20.62 |     0     | False                     |                 0    |
|        75   | low     | B                |                 -25    |     0     | False                     |                 0    |
|        75   | medium  | B                |                 -36.85 |     0     | False                     |                 0    |
|        75   | high    | B                |                 -18.32 |     0     | False                     |                 0    |
|        77.5 | low     | B                |                 -22.5  |     0     | False                     |                 0    |
|        77.5 | medium  | B                |                 -34.7  |     0     | False                     |                 0    |
|        77.5 | high    | B                |                 -15.14 |     0     | False                     |                 0    |
|        80   | low     | B                |                 -20    |     0     | False                     |                 0    |
|        80   | medium  | B                |                 -32.64 |     0     | False                     |                 0    |
|        80   | high    | B                |                 -11.99 |     0     | False                     |                 0    |
|        82.5 | low     | B                |                 -17.5  |     0     | False                     |                 0    |
|        82.5 | medium  | B                |                 -30.5  |     0     | False                     |                 0    |
|        82.5 | high    | B                |                  -9.12 |     0     | False                     |                 0    |
|        85   | low     | B                |                 -15    |     0     | False                     |                 0    |
|        85   | medium  | B                |                 -28.36 |     0     | False                     |                 0    |
|        85   | high    | B                |                  -5.46 |     0.003 | False                     |                 0    |
|        87.5 | low     | B                |                 -12.5  |     0     | False                     |                 0    |
|        87.5 | medium  | B                |                 -26.25 |     0     | False                     |                 0    |
|        87.5 | high    | B                |                  -3.3  |     0.048 | False                     |                 0    |
|        90   | low     | B                |                 -10    |     0     | False                     |                 0    |
|        90   | medium  | B                |                 -24.16 |     0     | False                     |                 0    |
|        90   | high    | B                |                  -0.83 |     0.332 | False                     |                 0    |
|        92.5 | low     | B                |                  -7.5  |     0     | True                      |                 1.16 |
|        92.5 | medium  | B                |                 -22.12 |     0     | True                      |                 1.16 |
|        92.5 | high    | A                |                   1.16 |     0.32  | False                     |                 0    |
|        95   | low     | B                |                  -5    |     0     | True                      |                 4.83 |
|        95   | medium  | B                |                 -19.96 |     0     | True                      |                 4.83 |
|        95   | high    | A                |                   4.83 |     0.022 | False                     |                 0    |
|        97.5 | low     | B                |                  -2.5  |     0     | True                      |                 6.77 |
|        97.5 | medium  | B                |                 -17.96 |     0     | True                      |                 6.77 |
|        97.5 | high    | A                |                   6.77 |     0.003 | False                     |                 0    |
|       100   | low     | A                |                   0    |     0     | False                     |                 0    |
|       100   | medium  | B                |                 -15.84 |     0     | True                      |                 9.45 |
|       100   | high    | A                |                   9.45 |     0     | False                     |                 0    |
