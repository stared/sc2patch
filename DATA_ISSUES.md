# Known Data Issues

## Ramp Range Entity IDs

**Issue**: The patch data uses per-race entity IDs for the same change:
- `terran-ramp`
- `protoss-ramp`
- `zerg-ramp`

**Problem**: This creates duplicate entries for what is actually a single game-wide change (ramp range affects all races identically).

**Recommended fix**: Normalize to `neutral-ramp` in the parsing pipeline, since this change is race-agnostic.

**Impact**:
- Causes unnecessary duplication in visualization
- Makes it harder to track the actual number of unique balance changes
- Inconsistent with how other universal changes are handled

**Example patches affected**: Check patches where ramp mechanics were changed.

---

## Future Improvements

1. **Entity ID Normalization**: Create a mapping in the parsing stage to normalize equivalent entity IDs
2. **Validation**: Add validation to catch when the same change text appears with different race prefixes
3. **Tech Tree Integration**: Use tech tree data to validate entity IDs during parsing
