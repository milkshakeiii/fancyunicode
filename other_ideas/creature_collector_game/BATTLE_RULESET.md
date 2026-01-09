# Hybrid Battle Ruleset (curses + cursesgame)

## Overview
This ruleset blends cursesgame's team-based grid combat with curses-style research
and summoning. It focuses on base battle flow and leaves conversion outcomes and
ability systems flexible for later expansion.

## Board and Coordinates
- Each side has a 4x4 grid (columns 0-3, rows 0-3).
- Columns represent depth: 0 = back, 3 = front (adjacent to the enemy).
- Rows are top to bottom: 0 = top, 3 = bottom.
- Targeting empty squares is allowed.
- For range math, treat the two grids as adjacent global columns:
  - Player local columns 0-3 map to global 0-3 (back to front).
  - Enemy local columns 0-3 map to global 4-7 (front to back).
  - Column distance = abs(global_col_a - global_col_b).

## Units and Stats
- Units have max_hp and current_hp.
- Units have three defense stats:
  - defense (vs melee)
  - dodge (vs ranged)
  - resistance (vs magic)
- Units have one or more attacks. Each attack has:
  - attack_type: melee, ranged, magic
  - damage
  - range_min, range_max (ranged only)
- Damage is deterministic:
  - final_damage = max(1, attack_damage - relevant_defense)

## Unit Footprints (Any Size)
- Units have width and height (1-4 each).
- A unit occupies a rectangular footprint on its side's grid.
- Footprints cannot overlap and must fit within the 4x4 grid.
- Reference square for a unit is the front-most column, then top-most row within
  its footprint.
  - Ranged and magic attacks use the reference square as the origin.
  - Melee attacks may use any row the unit occupies.
- If an attack would hit multiple occupied squares of the same unit, apply the
  effect only once.

## Battle Setup
- The player side fields a player unit (the "king" unit).
- The enemy side fields a control crystal (the "king" unit).
- The battle ends when either king unit is destroyed.
- Player places units on the player grid; enemies are placed randomly on the
  enemy grid, respecting footprints.

## Turn Structure
- Teams alternate turns. Player acts first unless an enemy has Haste.
- Each team gets 3 action slots per turn.
- Actions resolve sequentially; state updates after each action.
- The chosen unit resolves its action; some actions affect multiple units at once.
- Deaths are removed after each action resolves.
- Units can act in multiple actions per turn unless a status prevents it.
- After the team's 3 actions, status effects tick once and cooldowns reduce by 1.
- Research is the only action where multiple units act together.

## Actions
### Attack (single unit)
- Choose an allied unit and a target square on the enemy grid.
- The acting unit performs one attack if it can legally target that square.
- If the acting unit has multiple attacks, the player chooses which attack to
  use (AI picks one for enemy units).

### Move (single unit)
- Choose one allied unit and a direction (N/E/S/W).
- The unit shifts its footprint by 1 square.
- The move is valid if:
  - The destination footprint is entirely inside the grid.
  - The destination footprint stays within the unit's own side (no crossing into
    the enemy grid).
  - If destination squares contain allied units, those units are displaced by
    the inverse shift (one square) and their footprints remain valid (no overlap,
    in bounds).
- If any displaced unit cannot fit, the move is invalid.

### Research (team action)
- All allied units with research_efficiency > 0 add that value to the team
  research pool.
- Research pool is shared by the team and persists for the battle.
- Research is a requirement check for summoning; it is not consumed.

### Summon Charge (single unit)
- Choose one allied unit with max_summoning_pool > 0.
- The unit adds summon_efficiency to its current_summoning_pool, capped at
  max_summoning_pool.

### Summon (single unit)
- Choose one summoner and one prototype.
- A summon succeeds if:
  - team_research_pool >= prototype.research_requirement_to_summon
  - summoner.current_summoning_pool >= prototype.summoning_pool_cost_to_summon
  - A valid spawn footprint exists adjacent to the summoner's footprint
- On success, subtract the summoning pool cost and place the new unit.
- Summoned units appear after the Summon action resolves and can act in later
  actions that same turn.

### Pass
- Skip one action slot.

## Targeting and Attack Types
### Melee
- Attacks the closest enemy horizontally in the attacker's row.
- If the chosen target square is not that closest enemy, the attacker does not act.
- Multi-size units may choose any row they occupy to satisfy melee targeting.

### Ranged
- A target square is valid if its column distance is within the attack's
  range_min to range_max (inclusive).
- Row does not affect ranged validity.

### Magic
- Magic targets the mirror column on the enemy side (same depth index).
- The chosen target square must be in the mirror column for the attack to resolve.
- Magic hits all units in that enemy column.

## King Units and Win Conditions
- Destroying the player unit ends the battle immediately (player loses).
- Destroying the enemy control crystal ends the battle immediately (player wins).
- The player unit and control crystal act like normal units and can take actions.
- The control crystal typically has no attacks unless defined.
- If the enemy control crystal is destroyed, all remaining enemy units are
  converted. (Post-battle conversion effects are out of scope here.)

## Special Abilities (Draft, Non-Exhaustive)
These are placeholders for a future ability system. Keep them data-driven with
clear triggers (on_attack, on_hit, on_damage, on_turn_start, aura, etc.).
- Flying: immune to melee damage.
- Deathtouch X: melee attacks deal bonus damage equal to X% of target max HP.
- Lifelink: heal for damage dealt.
- Piercing: melee attacks hit all units in the target row.
- Splash: ranged attacks also hit orthogonally adjacent squares of the target.
- Evasion: % chance to avoid all damage from an attack.
- Shield Wall: gain defense/dodge for each allied unit of the same type.
- Pack Hunter: gain melee/ranged damage for each allied unit of the same type.

## Notes / TODO
- Confirm whether summoning should be "one summon per summoner" or "one total
  summon per action" if pacing needs tightening.
