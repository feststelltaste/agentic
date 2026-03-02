---
name: mikado-graph
description: Plan and track a complex refactoring using the Mikado Method. Trigger when the user mentions "mikado", wants to plan a refactoring or upgrade incrementally, needs to untangle blockers before changing code, or asks to track dependencies visually.
---

# Mikado Graph

## Node types

| Shape           | Type        | Meaning                                           |
|-----------------|-------------|---------------------------------------------------|
| double-oval     | **goal**    | The root goal you want to achieve                 |
| rectangle       | **problem** | A blocking obstacle just discovered               |
| rect + orange   | **impact**  | Non-obvious side-effect needing migration/fix     |
| ellipse         | **todo**    | Leaf node -- actionable right now, no blockers    |
| any + gray      | done        | Completed, shown dashed + gray fill               |

Impact nodes (type=impact) are problems caused by non-obvious coupling:
DB columns storing class/field names, serialized JSON shapes, config keys,
event-sourcing event names, reflection-based lookups, generated code, etc.
They look like rectangles but with fillcolor="#ffe8cc" (orange tint) to signal
"this requires work outside the codebase".

## Workflow

**Start a new graph**
User says: "I want to [goal]"
Derive a kebab-case slug from the goal (e.g. "Upgrade Postgres v3->v5" -> "upgrade-postgres-v3-v5").
Create <slug>.md with YAML frontmatter + <slug>.dot.
Then immediately run: dot -Tsvg <slug>.dot > <slug>.svg
Show the DOT content and confirm the SVG was written.

**Surface non-obvious impacts**
Whenever a new goal or problem node is added, proactively scan for hidden coupling
and add impact nodes for anything found. Ask the user to confirm before adding.
See REFERENCE.md "Impact checklist" for the full list of areas to probe.

**Discover a problem**
User says: "I tried [X], hit problem: [Y]"
Add a problem or impact rectangle node as child of X (use type=impact if it is
a non-obvious side-effect). If X was a todo leaf, it is no longer a leaf.

**Mark solved**
User says: "I solved [X]" or "done: [X]"
Set status: done on that node. Mark parent as actionable todo if all siblings are done.

**Link cross-dependencies**
User says: "[A] depends on [B]" or "[A] must happen before [B]"
Add B's id to A's depends_on list in the YAML. Render as a dashed arrow B -> A
(B must be done before A can start). These are peer dependencies, not parent-child.

**Show the graph**
User says: "render" or "show graph" or "update"
Re-render <slug>.dot from <slug>.md, run dot -Tsvg <slug>.dot > <slug>.svg, show DOT.

## Rules

- <slug>.md is the source of truth -- edit it, then regenerate <slug>.dot
- Slug = kebab-case of the goal, max ~5 words, no special chars except hyphens
- Store the slug in the YAML frontmatter as field: slug
- Leaf nodes with status: open and no children -- render as ellipse (shape=ellipse)
- Non-leaf open nodes that have unresolved children -- render as rectangle (shape=rectangle)
- type=impact nodes -- shape=rectangle, fillcolor="#ffe8cc" (orange tint), tooltip="non-obvious impact"
- The root goal node -- shape=doublecircle
- Done nodes -- style="dashed,filled" fillcolor=lightgray
- Edges point from child to parent (child must be done before parent can be done)
- Cross-dependencies (depends_on) render as dashed arrows: dependency -> dependent  [style=dashed color=gray]
- A node is only a leaf (ellipse/actionable) if it has no open children AND no open depends_on targets
- Always show the full DOT block after any change, with filename as a comment header
- After writing <slug>.dot, immediately run: dot -Tsvg <slug>.dot > <slug>.svg
- Tell the user the SVG was generated and its path
- Node ID prefix for impacts: I<n> (e.g. I1, I2) to distinguish from P<n> problems
- See REFERENCE.md for full data structure and DOT generation examples
