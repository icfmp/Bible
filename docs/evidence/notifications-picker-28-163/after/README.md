# Translation picker native verification

- Application: `/app/lib/bible-python/bible/ui.py`
- GTK: 4.20.4
- Renderer: GLRenderer
- Baseline: False
- Resources: real CrossWire KJV, FreSegond1910; YouVersion BDS (21), LSG (93).
- Environment: Xvfb/X11; developer automation, not client GNOME acceptance.

| Case | Window width | Popup content width |
| --- | ---: | ---: |
| light-1200-primary | 1200 | 520 |
| light-1200-compared | 1200 | 520 |
| light-1200-comparison | 1200 | 520 |
| light-560-primary | 560 | 512 |
| light-560-compared | 560 | 512 |
| light-560-comparison | 560 | 512 |
| light-360-primary | 360 | 312 |
| light-360-compared | 360 | 312 |
| light-360-comparison | 360 | 312 |
| dark-1200-primary | 1200 | 520 |
| dark-1200-compared | 1200 | 520 |
| dark-1200-comparison | 1200 | 520 |
| dark-560-primary | 560 | 512 |
| dark-560-compared | 560 | 512 |
| dark-560-comparison | 560 | 512 |
| dark-360-primary | 360 | 312 |
| dark-360-compared | 360 | 312 |
| dark-360-comparison | 360 | 312 |
| large-text-360 | 360 | 312 |

Native input:
- keyboard selection and reselection light
- Download more opens contextual Library
- keyboard selection and reselection dark
- Download more opens contextual Library
