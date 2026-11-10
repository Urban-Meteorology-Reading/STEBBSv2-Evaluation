# Indoor evaluation-period observations

`BRTYND_indoor_temperature_sample.csv.csv` contains the processed
indoor air temperatures needed for Figures 10 and 11. It is an evaluation-period
subset, not the raw sensor record or a full-year indoor dataset.

## Coverage

- Summer: 1-31 July 2025.
- Winter: 26 November-16 December 2025.
- Resolution: 15 minutes; temperatures are in degrees C.
- Timestamps are UTC interval ends. A value at 00:15 describes (00:00, 00:15].

The file has 4,994 rows in two separate blocks, with endpoint timestamps from
1 July 00:00 to 1 August 00:00, and from 26 November 00:00 to 17 December 00:00.
The final midnight completes each last evaluation day. The initial midnight
is a boundary value summarising the preceding 15 minutes, retained for plot
continuity (including the summer weekly line at 1 July 00:00). The gap between
seasons is intentional; do not interpolate across it.

## Columns

| Column | Meaning |
|---|---|
| `timestamp_utc` | UTC interval-ending timestamp |
| `master_bedroom` | Master bedroom temperature |
| `guest_bedroom` | Guest bedroom temperature |
| `landing1` | Landing1 temperature, sensor 39 |
| `landing2` | Landing2 temperature, sensor 121 |
| `dining_room` | Dining room temperature |
| `living_room` | Living room temperature |
| `kitchen` | Kitchen temperature |
| `OBS_mean` | Concurrent room-volume-weighted mean, excluding kitchen and basement |
| `OBS_min` | Minimum of the six concurrent 15-minute sensor means |
| `OBS_max` | Maximum of the six concurrent 15-minute sensor means |

## Preparation

Values were aggregated from the existing quality-controlled minute observations
using right-closed, right-labelled intervals before selecting these periods,
preserving the boundary means. An individual room mean requires
at least 12 valid minute records. For `OBS_mean`, `OBS_min` and `OBS_max`, only
minutes with all six non-kitchen sensors present are used; at least 12 such
concurrent minutes are required in each interval. Missing results are blank,
not zero, and are not interpolated.

The building mean uses these fixed room-volume weights (m3): master bedroom
35.1000, guest bedroom 29.1024, Landing1 8.6840, Landing2 8.6840, dining room
31.0300 and living room 39.4400 (total 152.0404). The landing volume is split
equally between its two sensors. Kitchen is available as an individual series
but is not included in the building mean or range; basement is excluded.

Individual room columns use each sensor's available minutes. Consequently, when
readings are missing, their weighted average need not exactly equal `OBS_mean`,
which uses only concurrent minutes. Use the supplied mean and range directly to
reproduce the figures. Retained decimal precision preserves the existing analysis;
it does not imply equivalent measurement accuracy.

The private minute records are not included or required by the public notebook.
