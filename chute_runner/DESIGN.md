# Chute Runner (Working Title)

## One-Liner
A gate-runner dungeon crawl powered by a compact factory: build injectors and machines to feed action chutes in real time, survive the gate sequence, and expand your layout between runs.

## Design Pillars
- Tension from the top lane: gates demand resources on a timer.
- Spatial puzzle: a small grid forces throughput tradeoffs.
- Chutes are the contract: the crawl only consumes what your chutes deliver.

## Core Loop
1. Pre-run planning: pick a loadout, place machines, and route belts.
2. Run phase: the hero auto-runs a gate sequence that drains action resources.
3. Factory management: adjust routes, toggle injectors, and handle demand spikes.
4. Outcome: salvage + blueprints on defeat or victory.
5. Meta progression: expand grid, unlock machines, add chute capacity.

## Screen Layout
- Top strip: side-scrolling gate runner with upcoming demand preview.
- Bottom strip: fixed factory grid (Factorio-like) for production and routing.
- Right edge: vertical chute bank with gauges, intake ports, and overflow buffers.

## Top Lane (Gate Runner)
- The runner auto-advances at a constant speed; gates appear in a fixed sequence.
- Each gate shows a demand bar (e.g., 8 swords, 4 shields, 1 key). Demand starts when the runner enters the gate zone.
- The gate consumes tokens pulled from the matching chutes in real time.
- Failure states:
  - If a gate is unmet by its deadline, the runner takes damage or the run ends (tunable per gate type).
  - Some gates allow partial success (consume what is available, apply remaining as damage).
- Gate types:
  - Monsters: consume sword tokens as DPS.
  - Doors/locks: consume keys in a single burst.
  - Traps: consume shields; leftover damage bleeds into HP.
  - Spell seals: consume spell charge tokens to bypass.
  - Hunger/darkness: continuous drain that slows the runner if unmet.
  - Boss gates: multi-stage demands with mixed resource types.

## Bottom Lane (Factory Grid)
- Grid starts small (example: 10x6) and expands with progression.
- Conveyor belts move items as discrete tokens; splitters and mergers route flow.
- Machines transform raw materials into intermediate parts and action resources.
- Space is the primary constraint; the player must choose between throughput and flexibility.
- Short reconfiguration windows can appear between gates for quick fixes.

## Chutes and Injectors (Primary Mechanic)
- Chutes are vertical channels that feed the top lane; the gate runner only pulls from chutes.
- Each chute is tied to an action resource (swords, shields, keys, spell charge, food, etc.).
- Chutes have:
  - Capacity (how many tokens they can buffer).
  - Pull rate (how fast the top lane can drain them).
  - Intake ports (where injectors can feed items).
- Injectors are the core interaction (Factorio inserter equivalent):
  - They handle all item movement: belt ↔ machine, machine ↔ machine, belt ↔ chute.
  - Machines have no built-in I/O; injectors must feed inputs and extract outputs.
  - They can also launch items into chute intakes.
  - Upgrades improve speed, stack size, reach, or filtering.
- Chute pressure:
  - If a chute is full, injectors jam and back up the line.
  - If a chute is empty, gates stall or damage the runner.
- Optional: chutes can be reconfigured mid-run (swap demand channels), but this consumes a limited "wrench" resource.

## Resources and Recipes (Example Set)
- Raw: ore, fiber, crystal, oil.
- Intermediate: plates, blades, wraps, runes, charges.
- Action tokens:
  - Swords: damage tokens generated from blades + wraps.
  - Shields: defense tokens from wraps + plates.
  - Keys: crafted from plates + oil.
  - Spell charge: crafted from runes + crystal.
  - Food/torch: crafted from fiber + oil for survival gates.

## Machines (Example Set)
- Smelter: ore -> plates.
- Press: plates -> blades.
- Loom: fiber -> wraps.
- Forge: blades + wraps -> swords.
- Armory: wraps + plates -> shields.
- Lockbench: plates + oil -> keys.
- Runeforge: crystal + oil -> runes.
- Capacitor: runes + crystal -> spell charge.
- Kitchen: fiber + oil -> food.
- Recycler: excess items -> base raw materials.

## Run Phase Controls
- Hotkey toggles for injector priority (e.g., swords over shields for 3 seconds).
- Emergency "dump" lever to feed all storage into a single chute.
- Short pause/slow window between gates for reroutes (optional).

## Progression
- Grid expansion: unlock extra rows/columns.
- Chute upgrades: larger buffers, faster pull rates, more intake ports.
- Injector upgrades: faster cycles, longer reach, filter rules.
- Machine unlocks: advanced recipes (e.g., area-of-effect spell charge).
- Hero upgrades: more HP, gate delay, or auto-cast abilities.

## Example Run (Minute 1)
1. The first gates demand swords and a single key.
2. The factory routes ore -> plates -> blades -> swords, with a side line for keys.
3. The sword chute stays full, but the key chute is slow; a door gate drains it instantly.
4. The player pivots an injector to pull plates into the key chute for 10 seconds.
5. A trap gate appears; shield chute is empty, causing minor HP loss.
6. The player installs a tiny wrap + shield line before the next gate window.

## UX and Readability
- Chute gauges show fill, pull rate, and jam state.
- Gate preview shows two gates ahead, including demand counts.
- Injectors glow when idle, pulsing when starved or jammed.
- Tooltips show throughput per second and estimated time to fill a gate demand.

## Balance Notes
- Provide a recycler or "overflow sink" to avoid hard deadlocks.
- Early runs should be forgiving on demand timing to teach choke points.
- Ensure at least one generic conversion path (e.g., overflow -> spell charge).

## Open Questions
- Should the run be fully real-time or allow timed pause slices between gates?
- How many chute types can a player realistically manage before it becomes cluttered?
- Do gates always consume instantly at contact, or drain over a short window?
