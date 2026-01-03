# Game Rules (Combat and Play)
This document covers the core in-game rules and omits ship building and shipyard features.

## Game Start
- When the Game scene loads, the campaign spawns the player ship ("king") and a single enemy ship.
- The enemy is placed at (2, 2) and assigned a simple attack behavior.
- Resource patches are spawned in the playfield (see Resources below).

## Goal and End State
- There is no explicit victory condition yet.
- Play effectively ends for the player when the king vessel is destroyed.

## Core Entities
### Vessels
- Vessels are 2D physics bodies with no gravity, linear drag of 1, and angular drag of 1.
- Hitpoints = size^2 * durability.
- Taking damage darkens the vessel sprite proportionally; if hitpoints < 0, the vessel is destroyed.
- A vessel cannot be damaged by its own projectiles, but projectiles can damage other vessels.

### Engines (Movement)
- Engines apply force at their world position while active.
- Thrust direction is the engine's local up vector; off-center thrust creates rotation.
- Thrust magnitude = engine scale * quality1 (thrust factor = 1).
- Maximum linear speed = quality2 * 10.
- Angular velocity is capped at 1080 degrees per second.
- Engines are turned on with key down and turned off with key up.

### Launchers (Combat)
- Launchers fire a single active projectile at a time. A launcher cannot fire again until its current projectile despawns.
- Launch velocity = quality1 (launch velocity factor = 1).
- Range = quality2 * 2.

### Projectiles
- A projectile's size equals its launcher's scale.
- Lifetime = range / velocity.
- Projectiles fade in over the first 1/8 of lifetime and fade out over the last 1/8.
- Projectiles are triggers; they do not bounce.
- On hit, a projectile deals damage = projectile size * projectile speed.
- After a hit or timeout, the projectile despawns and returns to a pool.

### Bays (Resource Harvesting)
- Bays harvest from resource patches they overlap.
- Harvest rate ramps up over time: rate += warmup * 0.1 * deltaTime, capped at max = quality2.
- Each frame, the bay converts rate * deltaTime into player resources and shrinks the resource patch by the same amount.
- Resource patches disappear once their scale drops below 0.

## Resources and Stockpiles
- Three resource types exist: Build, Move, Launch.
- Stockpiles start at 1.0 for each type.
- Resource patches spawn randomly within a rectangle (width 10, height 5), mirrored above and below the origin.
- Only Launch resources are currently spent in combat:
  - Each shot costs 0.01 Launch resources.
  - If you lack Launch resources, the launcher does not fire.
- Build and Move resources are tracked but not consumed by combat rules.

## Player Controls (Game Scene)
- Engines (toggle on/off): A, S, D, W, Q, E, Z, X, C.
- Launchers (fire): Space, F, G, V, B, R, T, LeftCtrl, Tab.
- Each key maps to the corresponding engine or launcher index in the ship's part list (first key = index 0, etc.).

## Enemy Behavior
- The default enemy is assigned a simple attack behavior that attempts to shoot at the player's king ship when in range and within 10 degrees of facing.
- Movement AI is not implemented beyond this attack behavior.
