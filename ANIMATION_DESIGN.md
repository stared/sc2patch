# Animation Design Document

## Problem Statement

The SC2 Patches visualization needs smooth, minimal animations when:
1. Filtering to a specific unit (switching from grid view to filtered view)
2. Clearing filter (switching back to grid view)
3. Clicking on entities

## Core Principles

Based on Framer Motion (Motion) v12 best practices:

1. **Use `layout` prop for position changes** - Don't manually animate transforms
2. **AnimatePresence for enter/exit** - But only when elements are truly added/removed from DOM
3. **Shared element transitions with `layoutId`** - For morphing the same entity across views
4. **Minimal is better** - "Movement should be exactly what's needed, nothing more (or less)"
5. **Performance** - Avoid animating expensive properties (width, height), prefer transforms

## Animation Strategy

### 1. Entity Cards - Shared Element Transitions

**Goal**: When clicking a unit, it should smoothly morph from the grid to the filtered view position.

**Implementation**:
- Use `layoutId={entityId}` (not `layoutId={entityId-patchVersion}`) so the SAME entity across different patches is treated as one continuous element
- Add `layout` prop to let Framer Motion automatically animate position/scale changes
- NO manual `initial`, `animate`, or `exit` props - trust the layout animation

```tsx
<motion.div
  layoutId={`entity-${entityId}`}  // Stable across all patches
  layout  // Auto-animate position changes
  className="entity-cell"
>
```

### 2. Grid Structure Changes

**Challenge**: Grid changes from 4 columns (terran/zerg/protoss/neutral) to 2 columns (unit + changes) when filtering.

**Implementation**:
- Use CSS Grid with transition on grid-template-columns
- Let Framer Motion's `layout` prop handle entity repositioning
- NO AnimatePresence at the grid level - elements stay in DOM

```css
.patch-grid {
  display: grid;
  grid-template-columns: auto repeat(4, 1fr);
  transition: grid-template-columns 0.3s ease;
}

.patch-grid.filtered {
  grid-template-columns: auto 1fr 2fr;
}
```

### 3. Race Headers

**Implementation**:
- Use AnimatePresence with `mode="popLayout"` (not "wait") for smooth transitions
- Each header needs unique `key` prop
- Add `layout` prop for position animations

```tsx
<AnimatePresence mode="popLayout">
  {selectedEntityId ? (
    <motion.div key="filtered-race" layout>
      {selectedEntity.race}
    </motion.div>
  ) : (
    races.map(race => (
      <motion.div key={race} layout>
        {race}
      </motion.div>
    ))
  )}
</AnimatePresence>
```

### 4. Patch Rows

**Critical Decision**: Do we use AnimatePresence for filtered patches?

**Answer**: NO - Keep all patches in DOM, use opacity for visibility

**Reasoning**:
- AnimatePresence causes "disappear then reappear" when toggling filter
- Framer Motion needs elements in DOM to track position for smooth morphing
- Use CSS opacity transition instead

**Implementation**:
```tsx
{patches.map(patch => (
  <div
    key={patch.version}
    style={{
      opacity: shouldShow ? 1 : 0,
      pointerEvents: shouldShow ? 'auto' : 'none',
      transition: 'opacity 0.2s ease'
    }}
  >
```

**WAIT**: This doesn't work with the user's requirement to "only show patches with selected entity"

**NEW APPROACH**:
- When filtering, actually filter the patches array
- Use AnimatePresence around the entire patch list
- Add `layout` to each patch row

### 5. Expansion Separators

**Implementation**:
- Simple opacity fade in/out
- Only show when NOT filtered

```tsx
{!selectedEntityId && showExpansionBar && (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    transition={{ duration: 0.2 }}
  >
```

## What NOT To Do

1. ❌ NO manual y-axis animations (`initial={{ y: -10 }}`)
2. ❌ NO stagger delays - causes cascading jitter
3. ❌ NO `mode="wait"` with multiple children in AnimatePresence
4. ❌ NO mixing layout animations with manual transform animations
5. ❌ NO aggressive spring physics - use simple easing
6. ❌ NO `display: none` toggle - breaks position tracking

## Implementation Plan

### Phase 1: Add layoutId to entities
- Single `layoutId` per entity (not per patch)
- This enables shared element transitions

### Phase 2: Add layout prop
- Add to entities, race headers, patch rows
- Remove all manual position animations

### Phase 3: Wrap with AnimatePresence
- Race headers (mode="popLayout")
- Expansion separators
- Filtered patches list (if using filtering approach)

### Phase 4: Fine-tune transitions
- Add specific transition configs to layout prop
- Test and adjust timing

## Transition Configuration

```tsx
const layoutTransition = {
  type: "spring",
  stiffness: 300,
  damping: 30,
  mass: 0.8
};

// OR simpler:
const layoutTransition = {
  duration: 0.3,
  ease: [0.16, 1, 0.3, 1]  // easeOutExpo
};
```

## Testing Checklist

- [ ] Click unit → smooth morph to filtered view
- [ ] Clear filter → smooth morph back
- [ ] No flickering/blinking during transitions
- [ ] No "appear from bottom" issues
- [ ] All patches with selected unit are visible
- [ ] Grid column change is smooth
- [ ] Race headers transition cleanly
- [ ] Performance is good (60fps)

## References

- Framer Motion v12 (latest)
- React 19
- Motion is rebranded from Framer Motion (motion.dev)
- Use `layout` prop for automatic FLIP animations
- Use `layoutId` for shared element transitions
