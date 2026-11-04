# Translation picker native verification

- Application: `/app/lib/bible-python/bible/ui.py`
- GTK: 4.20.4
- Baseline: True
- Resources: real CrossWire KJV, FreSegond1910; YouVersion BDS (21), LSG (93).
- Environment: Xvfb/X11; developer automation, not client GNOME acceptance.

| Case | Window width | Popup content width |
| --- | ---: | ---: |
| light-1200-primary | 1200 | 220 |
| light-1200-compared | 1200 | 220 |
| light-1200-comparison | 1200 | 220 |
| light-560-primary | 560 | 220 |
| light-560-compared | 560 | 220 |
| light-560-comparison | 560 | 220 |
| light-360-primary | 360 | 220 |
| light-360-compared | 360 | 220 |
| light-360-comparison | 360 | 220 |
| dark-1200-primary | 1200 | 220 |
| dark-1200-compared | 1200 | 220 |
| dark-1200-comparison | 1200 | 220 |
| dark-560-primary | 560 | 220 |
| dark-560-compared | 560 | 220 |
| dark-560-comparison | 560 | 220 |
| dark-360-primary | 360 | 220 |
| dark-360-compared | 360 | 220 |
| dark-360-comparison | 360 | 220 |

Native input:
- keyboard selection and reselection light
- Download more opens contextual Library
- keyboard selection and reselection dark
- Download more opens contextual Library
