# Data Documentation

## Patch Coverage

**Release patches only** (live multiplayer balance changes).

| Era | Launch | Patch Range | First Balance |
|-----|--------|-------------|---------------|
| Wings of Liberty | Jul 2010 | 1.1.0 - 1.5.4 | Sep 2010 |
| Heart of the Swarm | Mar 2013 | 2.0.8 - 2.1.9 | May 2013 |
| Legacy of the Void | Nov 2015 | 3.1.1 - 3.14.0 | Jan 2016 |
| Free-to-Play | Nov 2017 | 4.0 - 4.12.0 | Nov 2017 |
| 10th Anniversary | Jul 2020 | 5.0.2 - 5.0.15 | Aug 2020 |

**Total:** ~49 release patches

### Excluded

**Beta patches** (~39 total) are excluded:
- WoL Beta: 0.3.0 - 0.20.0
- HotS Beta: Updates #1-15
- LotV Beta: 2.5.0 - 2.5.5

Reason: Beta = design iteration, not live balance. Frequent drastic changes, dead URLs.

### Limitations

- Multiplayer only (no Campaign/Co-op)
- Balance only (no bug fixes, UI, maps)

## Unit Notes

### LotV Units (Nov 2015)

Adept, Liberator, Ravager, Lurker, Disruptor appear from their **first live balance change**, not launch.

**Disruptor:** First change in Patch 4.0 (Nov 2017). No 3.x balance changes despite being playable.

## Known Issues

### Ramp Entity IDs

Ramp mechanics use per-race IDs (`terran-ramp`, `protoss-ramp`, `zerg-ramp`) instead of `neutral-ramp`. Creates duplicates for game-wide changes.

**Status:** Pending normalization fix.

