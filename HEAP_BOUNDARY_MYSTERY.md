# Heap Boundary Mystery - e329e42e

## The Question
Message e329e42e-8b63-4d3f-b66d-858d62b9fc67 (a `/compact` command) correctly started a new heap in an earlier import, but we can't figure out WHY.

## What We Know
- e329e42e is a command message (not a CompactingAction)
- Parent: 26c96481 (caveat message)
- Grandparent: eece5bd8 (continuation message)
- Both e329e42e and 26c96481 had `created=False` (already existed from previous import)
- No CompactingAction exists for this boundary
- Conversationally, it IS clearly a compact boundary - subsequent messages reference the compact

## The Mystery
The only way e329e42e should start a new heap is if `heap` was `None` when we encountered it (triggering lines 360-363 to pick up its heap). But we can't figure out why `heap` would be `None` at that point, since 26c96481 should have set it.

## Resolution
Accepting this as an edge case. The heap boundaries are mostly correct, and this doesn't block importing Era 2.

Block 23,557,831 - October 24, 2025
