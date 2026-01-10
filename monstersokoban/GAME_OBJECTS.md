# MonsterSokoban: Game Objects Reference

> Complete reference for all game objects, tech tree, monsters, skills, items, and workshops.

**Version**: 1.0  
**Date**: January 2026  
**Based On**: MonsterMakers GAME_RULES.md (adapted for sokoban mechanics)

---

## Table of Contents

1. [Monsters](#1-monsters)
2. [Equipment](#2-equipment)
3. [Skills](#3-skills)
4. [Raw Materials](#4-raw-materials)
5. [Crafted Items](#5-crafted-items)
6. [Tools](#6-tools)
7. [Workshops](#7-workshops)
8. [Tech Tree](#8-tech-tree)
9. [Locations](#9-locations)
10. [Visual Specifications](#10-visual-specifications)
11. [Formulas](#11-formulas)

---

## 1. Monsters

### 1.1 Monster Types Overview

| Type | Glyph | Renown Cost | Body Cap | Mind Cap | STR | DEX | CON | INT | WIS | CHA | Specialty |
|------|-------|-------------|----------|----------|-----|-----|-----|-----|-----|-----|-----------|
| **Cyclops** | `C` | 100 | 100 | 100 | 18 | 10 | 16 | 10 | 10 | 10 | Heavy work, quantity |
| **Elf** | `E` | 150 | 50 | 150 | 10 | 16 | 10 | 18 | 10 | 10 | Precision, learning |
| **Goblin** | `G` | 50 | 150 | 50 | 10 | 18 | 10 | 10 | 10 | 16 | Speed, charisma |
| **Orc** | `O` | 2000 | 150 | 50 | 16 | 10 | 18 | 10 | 10 | 10 | Durability, transport |
| **Troll** | `T` | 1 | 1500 | 1500 | 18 | 10 | 16 | 10 | 10 | 10 | Massive capacity |

### 1.2 Detailed Monster Profiles

#### Cyclops (C)
```
      (O)        
     /===\       Base Cost: 100 renown
    | ___ |      
    |     |      Primary: Heavy lifting, bulk production
     \___/       
      |_|        Abilities:
                 - STR 18: Can push 3 items in chain
                 - CON 16: Pull loaded wagons effectively
                 - Good at quantity-focused crafting
                 
    Special: One-eyed artisan, excellent at metalwork
```

**Best Roles**: Smith, Miner, Heavy Transport  
**Pushing Power**: Can push heavy items and 3-item chains  
**Movement**: Standard (1 cell/tick at DEX 10)  
**Visual**: Large, single-eye sprite, orange/brown tones

#### Elf (E)
```
       ^         
      /|\        Base Cost: 150 renown
     / | \       
    |  |  |      Primary: Precision work, quality crafting
     \ | /       
      \|/        Abilities:
       |         - INT 18: Fastest skill learning
      / \        - DEX 16: Quick movements
                 - WIS bonus for quality rolls
                 
    Special: Ancient craftsman, excels at fine arts
```

**Best Roles**: Enchanter, Alchemist, Fine Craftsman  
**Pushing Power**: Light items only (STR 10)  
**Movement**: Fast (can sometimes move 2 cells at DEX 16)  
**Visual**: Slender, pointed ears, green/silver tones

#### Goblin (G)
```
       ,         
      /`\        Base Cost: 50 renown (cheapest!)
     (o o)       
      |~|        Primary: Speed, social interactions
       V         
      /|\        Abilities:
     / | \       - DEX 18: Fastest movement
                 - CHA 16: Better value from scored goods
                 - Quick but weak pusher
                 
    Special: Scrappy worker, good with people
```

**Best Roles**: Gatherer, Courier, Trader  
**Pushing Power**: Light items only (STR 10)  
**Movement**: Very fast (1 cell/tick guaranteed, occasional bursts)  
**Visual**: Small, pointy-eared, green tones

#### Orc (O)
```
      ___        
     /   \       Base Cost: 2000 renown (expensive!)
    | O O |      
    |  _  |      Primary: Endurance, heavy transport
     \___/       
      |||        Abilities:
     /|||\       - CON 18: Best wagon pulling
                 - STR 16: Strong pusher
                 - Built for long hauls
                 
    Special: Tireless laborer, transport expert
```

**Best Roles**: Transport, Heavy Labor, Mining  
**Pushing Power**: Can push heavy items and 2-item chains  
**Movement**: Standard but tireless  
**Visual**: Muscular, tusked, gray/brown tones

#### Troll (T)
```
      ___        
     /   \       Base Cost: 1 renown (unique!)
    |O   O|      
    |  ▄  |      Note: HUGE capacity costs
     \___/       Body 1500, Mind 1500 = can use everything
    / ||| \      
   /  |||  \     Abilities:
                 - STR 18: Strongest pusher
                 - CON 16: Good transport
                 - 100 slots each type = unlimited equipment
                 
    Special: Walking workshop, can equip everything
```

**Best Roles**: Mobile Workshop, Storage, Heavy Everything  
**Pushing Power**: Can push anything  
**Movement**: Slow but unstoppable  
**Visual**: Huge sprite (2x2?), lumbering, gray/green tones

### 1.3 Monster Aging

| Age | Stat Bonus | Visual Change |
|-----|------------|---------------|
| 0-29 days | None | Youthful appearance |
| 30-59 days | +1 all abilities | Mature appearance |
| 60+ days | +2 all abilities | Elder appearance, subtle glow |

### 1.4 Monster Sprites

Each monster has animation frames:
- Frame 0: Idle/standing
- Frame 1: Walk left
- Frame 2: Walk right
- Frame 3: Push (strain)
- Frame 4: Work (crafting)

```python
# Example monster sprite creation
goblin_sprite = pyunicodegame.create_sprite(
    """
     ,
    /`\\
   (o o)
    |~|
     V
    """,
    x=10, y=10,
    fg=(100, 180, 100),  # Green tint
    z_index=35,
    lerp_speed=8
)

# Walk animation with bob
walk_anim = pyunicodegame.create_animation(
    "walk",
    frame_indices=[0, 1, 0, 2],
    frame_duration=0.15,
    offsets=[(0, 0), (0, -1), (0, 0), (0, -1)],
    loop=True,
    offset_speed=50
)
goblin_sprite.add_animation(walk_anim)
```

---

## 2. Equipment

### 2.1 Equipment Overview

Equipment is purchased when attracting a monster and provides permanent bonuses.

| ID | Name | Renown | Body Cost | Mind Cost | Slot | Effect |
|----|------|--------|-----------|-----------|------|--------|
| 0 | Gloves | 50 | 10 | 0 | Worn | +1 STR |
| 1 | Headband | 50 | 10 | 0 | Worn | +1 DEX |
| 2 | Shoes | 50 | 10 | 0 | Worn | +1 CON |
| 3 | Glasses | 2 | 0 | 10 | Personal | +1 INT |
| 4 | Amulet | 50 | 0 | 10 | Worn | +1 WIS |
| 5 | Earrings | 50 | 0 | 10 | Worn | +1 CHA |
| 6 | Magnifying Glass | 50 | 10 | 50 | Personal | +10% quality |
| 7 | Towel | 50 | 50 | 10 | Personal | +1 quantity |
| 8 | Wristwatch | 50 | 10 | 50 | Personal | -10s production time |
| 9 | Backpack | 50 | 50 | 50 | Personal | -10s transport time |
| 10 | Cart | 50 | 50 | 50 | Personal | +10 transport weight |
| 11 | Pen | 50 | 50 | 50 | Personal | +0.01% learning bonus |
| 12 | Notebook | 50 | 50 | 50 | Internal | -0.001% forgetting |
| 13 | Rubber Stamp | 50 | 50 | 50 | Internal | +10 value |

### 2.2 Equipment Slots

| Slot Type | Description | Typical Items |
|-----------|-------------|---------------|
| **Personal** | Held/carried items | Tools, accessories |
| **Worn** | Clothing/accessories | Gloves, shoes, jewelry |
| **Internal** | Mental/magical | Books, enchantments |

### 2.3 Fitting System

- **Body Fitting Capacity**: Physical equipment limit
- **Mind Fitting Capacity**: Mental equipment limit
- Each monster type has different capacities

**Example**: Goblin (Body 150, Mind 50)
- Can wear lots of physical gear
- Limited mental equipment
- Good for tool-heavy roles

### 2.4 Equipment Visual Representation

Equipped monsters show equipment as overlaid glyphs or modified sprites:

```
Without equipment:    With equipment:
       ,                    ,^       (Headband)
      /`\                  /`\
     (o o)                (o o)      
      |~|                  |~|       
       V                    V
      /|\                  /|\+      (Gloves)
```

---

## 3. Skills

### 3.1 Transferable Skills (Choose 3 at creation)

These are general aptitudes that provide bonuses to related crafts.

| ID | Skill | Related Crafts | Lore |
|----|-------|----------------|------|
| 1 | **Mathematics** | Lutherie, Engineering, Accounting | "Numbers speak truths" |
| 2 | **Science** | Brewing, Alchemy, Glassware | "Understanding is power" |
| 3 | **Engineering** | Furniture, Wagons, Masonry | "Build to last" |
| 4 | **Writing** | Essays, Creative Writing, Enchanting | "Words have power" |
| 5 | **Visual Art** | Painting, Sculpting, Windows | "Beauty in form" |
| 6 | **Music** | Lutherie, Wind Instruments, Singing | "Harmony of creation" |
| 7 | **Handcrafts** | Tailoring, Weaving, Leather | "Skilled fingers" |
| 8 | **Athletics** | Hauling, Mining, Chopping | "Strength of body" |
| 9 | **Outdoorsmonstership** | Gathering, Traveling, Husbandry | "Know the land" |
| 10 | **Social** | Brewing, Trading, Performing | "Know the people" |

### 3.2 Applied Skills (Learned through doing)

Skills gain experience when performing related tasks.

#### Transport Skills
| Skill | Description | Primary Ability |
|-------|-------------|-----------------|
| **Hauling** | Local transport | STR |
| **Wagon Driving** | Inter-city transport | CHA |

#### Resource Skills
| Skill | Description | Primary Ability |
|-------|-------------|-----------------|
| **Gathering** | Foraging, collecting | WIS |
| **Traveling** | Long-distance movement | CON |
| **Planting** | Agriculture setup | INT |
| **Harvesting** | Crop collection | DEX |
| **Husbandry** | Animal care | WIS |
| **Chopping** | Wood harvesting | STR |
| **Mining** | Ore extraction | STR |

#### Crafting Skills
| Skill | Workshop | Products |
|-------|----------|----------|
| **Dishes** | Kitchen | Plates, bowls |
| **Baking** | Kitchen/Oven | Bread, pastries |
| **Brewing** | Brewery | Ale, wine, potions |
| **Lutherie** | Workbench | Stringed instruments |
| **Furniture** | Workbench | Chairs, tables |
| **Wagon Wright** | Workshop | Wagons, carts |
| **Sculpting** | Workbench | Statues, figurines |
| **Masonry** | Stone Workshop | Walls, foundations |
| **Windows** | Glass Workshop | Glass panes, stained glass |
| **Glassware** | Glass Workshop | Bottles, lenses |
| **Smelting** | Forge | Ingots |
| **Blacksmithing** | Forge | Tools, weapons |
| **Metal Crafting** | Forge | Fine metalwork |
| **Tailoring** | Loom | Clothes |
| **Weaving** | Loom | Fabric, textiles |
| **Painting** | Art Studio | Pictures, decorations |
| **String Instruments** | Workshop | Violins, harps |
| **Wind Instruments** | Workshop | Flutes, horns |
| **Singing** | Performance Hall | Vocal performances |
| **Dancing** | Performance Hall | Dance performances |
| **Essays** | Study | Written works |
| **Creative Writing** | Study | Stories, poetry |
| **Enchanting** | Alchemy Table | Enchanted items |
| **Potion Making** | Alchemy Table | Potions, elixirs |

### 3.3 Specific Skills

Each recipe has its own specific skill that develops:
- "Make Iron Sword"
- "Brew Wheat Ale"
- "Craft Oak Chair"

These stack with Applied Skills for maximum efficiency.

### 3.4 Skill Value Calculation

```
Current_Skill_Value = Total_Learned - Monster.Total_Forgotten
```

Where:
- `Total_Learned`: Cumulative XP from performing tasks
- `Total_Forgotten`: Cumulative decay (increases slowly over time)

### 3.5 Transferable Skill Mappings

| Applied Skill | Transferable 1 | Transferable 2 | Transferable 3 |
|---------------|----------------|----------------|----------------|
| Brewing | Science | Engineering | Social |
| Lutherie | Mathematics | Engineering | Music |
| Blacksmithing | Athletics | Engineering | Handcrafts |
| Hauling | Athletics | Outdoorsmonstership | Social |
| Enchanting | Writing | Science | Visual Art |
| ... | ... | ... | ... |

Having matching transferable skills:
- Drops lowest tool quality weights from calculations
- Drops lowest secondary skill values
- Improves overall quality/quantity rolls

### 3.6 Skill Visual Representation

In the skills panel:
```
+-----------------+
| SKILLS          |
|-----------------|
| Blacksmithing   |
|  [*****-----]   |  (50%)
|  Level: 3       |
|                 |
| Mining          |
|  [***-------]   |  (30%)
|  Level: 2       |
|                 |
| Hauling         |
|  [********--]   |  (80%)
|  Level: 4       |
+-----------------+
```

---

## 4. Raw Materials

### 4.1 Raw Material Categories

Raw materials are the foundation of all crafting. They can only be gathered at locations with matching tags.

#### Organic Materials
| Material | Tags | Base Value | Density | Rarity | Location |
|----------|------|------------|---------|--------|----------|
| Oak Log | wood, hardwood | 10 | 800 | 1 | Forest |
| Pine Log | wood, softwood | 8 | 550 | 1 | Forest |
| Birch Log | wood, flexible | 9 | 650 | 2 | Forest |
| Wheat | grain, food | 5 | 750 | 1 | Farm |
| Barley | grain, brewing | 6 | 700 | 1 | Farm |
| Cotton | fiber, plant | 7 | 400 | 2 | Farm |
| Flax | fiber, plant | 8 | 350 | 2 | Farm |
| Wool | fiber, animal | 12 | 300 | 2 | Farm |
| Hide | leather, animal | 15 | 900 | 2 | Farm |
| Herbs | plant, medicine | 10 | 200 | 3 | Wilderness |

#### Mineral Materials
| Material | Tags | Base Value | Density | Rarity | Location |
|----------|------|------------|---------|--------|----------|
| Iron Ore | ore, metal | 15 | 5000 | 1 | Mine |
| Copper Ore | ore, metal | 12 | 4500 | 1 | Mine |
| Tin Ore | ore, metal | 10 | 7300 | 2 | Mine |
| Gold Ore | ore, precious | 50 | 19300 | 4 | Deep Mine |
| Silver Ore | ore, precious | 30 | 10500 | 3 | Deep Mine |
| Coal | fuel, mineral | 8 | 1500 | 1 | Mine |
| Clay | earth, moldable | 5 | 2000 | 1 | Riverbank |
| Sand | earth, glass | 4 | 1600 | 1 | Beach |
| Stone | earth, building | 6 | 2600 | 1 | Quarry |
| Gems (Raw) | gem, magical | 100 | 3500 | 5 | Cavern |

#### Liquid/Other Materials
| Material | Tags | Base Value | Density | Rarity | Location |
|----------|------|------------|---------|--------|----------|
| Water | liquid, pure | 1 | 1000 | 1 | Well |
| Honey | liquid, sweet | 20 | 1400 | 3 | Apiary |
| Milk | liquid, animal | 8 | 1030 | 2 | Farm |
| Oil | liquid, fuel | 15 | 900 | 3 | Press |

### 4.2 Raw Material Visual

Raw materials have distinct glyphs and colors:

```python
RAW_MATERIAL_VISUALS = {
    "oak_log": {"glyph": "=", "fg": (139, 90, 43)},      # Brown
    "iron_ore": {"glyph": "*", "fg": (128, 128, 128)},   # Gray
    "gold_ore": {"glyph": "*", "fg": (255, 215, 0)},     # Gold
    "wheat": {"glyph": "%", "fg": (255, 220, 100)},      # Yellow
    "cotton": {"glyph": "~", "fg": (255, 255, 240)},     # White
    "coal": {"glyph": ".", "fg": (40, 40, 40)},          # Black
    "gems": {"glyph": "+", "fg": (255, 100, 255), "emissive": True}, # Pink glow
}
```

### 4.3 Gathering Mechanics

1. Find raw resource location with correct tags
2. Have appropriate tool (if required)
3. Monster interacts with resource node
4. Gathering task begins (progress indicators)
5. Raw material appears as pushable item
6. Node may deplete after multiple harvests

---

## 5. Crafted Items

### 5.1 Basic Crafted Items

#### From Wood
| Item | Inputs | Workshop | Time | Quality | Tags |
|------|--------|----------|------|---------|------|
| Plank | 1x Log | Saw | 10s | Yes | wood, processed |
| Handle | 1x Plank | Workbench | 15s | Yes | wood, component |
| Chair | 2x Plank, 1x Handle | Workbench | 60s | Yes | furniture, wood |
| Table | 4x Plank, 2x Handle | Workbench | 90s | Yes | furniture, wood |
| Barrel | 6x Plank | Workbench | 45s | Yes | container, wood |
| Crate | 4x Plank | Workbench | 30s | Yes | container, wood |

#### From Metal
| Item | Inputs | Workshop | Time | Quality | Tags |
|------|--------|----------|------|---------|------|
| Iron Ingot | 2x Iron Ore, 1x Coal | Forge | 30s | Yes | metal, processed |
| Steel Ingot | 1x Iron Ingot, 1x Coal | Forge | 45s | Yes | metal, processed, refined |
| Copper Ingot | 2x Copper Ore | Forge | 25s | Yes | metal, processed |
| Bronze Ingot | 1x Copper Ingot, 1x Tin Ore | Forge | 35s | Yes | metal, alloy |
| Nails | 1x Iron Ingot | Forge | 20s | Fixed | metal, fastener |
| Chain | 2x Iron Ingot | Forge | 40s | Yes | metal, binding |

#### From Fiber
| Item | Inputs | Workshop | Time | Quality | Tags |
|------|--------|----------|------|---------|------|
| Thread | 1x Cotton OR 1x Flax | Loom | 15s | Yes | fiber, processed |
| Cloth | 2x Thread | Loom | 30s | Yes | fabric |
| Rope | 3x Thread | Loom | 25s | Yes | binding, fiber |
| Leather | 1x Hide | Tanning Rack | 60s | Yes | leather, processed |
| Fine Leather | 1x Leather + Special Process | Tanning Rack | 90s | Yes | leather, refined |

### 5.2 Intermediate Crafted Items

#### Tools (See Section 6)

#### Weapons
| Item | Inputs | Workshop | Time | Quality | Tags |
|------|--------|----------|------|---------|------|
| Iron Sword | 2x Iron Ingot, 1x Handle | Forge | 60s | Yes | weapon, metal |
| Steel Sword | 2x Steel Ingot, 1x Handle | Forge | 90s | Yes | weapon, metal, refined |
| Axe | 1x Iron Ingot, 1x Handle | Forge | 45s | Yes | tool, weapon |
| Spear | 1x Iron Ingot, 1x Handle, 1x Rope | Forge | 50s | Yes | weapon, polearm |

#### Food/Consumables
| Item | Inputs | Workshop | Time | Quality | Tags |
|------|--------|----------|------|---------|------|
| Bread | 2x Wheat, 1x Water | Oven | 30s | Yes | food, baked |
| Ale | 2x Barley, 2x Water | Brewery | 120s | Yes | drink, alcohol |
| Healing Potion | 2x Herbs, 1x Water | Alchemy Table | 90s | Yes | potion, healing |

### 5.3 Advanced Crafted Items

#### Enchanted Items
| Item | Inputs | Workshop | Time | Quality | Tags |
|------|--------|----------|------|---------|------|
| Enchanted Ring | 1x Gold Ingot, 1x Gem | Alchemy Table | 180s | Yes | jewelry, magical |
| Magic Staff | 1x Hardwood Handle, 1x Gem | Alchemy Table | 240s | Yes | weapon, magical |
| Rune Stone | 1x Stone, 1x Enchanting Ink | Alchemy Table | 120s | Yes | magical, inscription |

#### Luxury Items
| Item | Inputs | Workshop | Time | Quality | Tags |
|------|--------|----------|------|---------|------|
| Tapestry | 4x Fine Cloth, 1x Dye | Loom | 300s | Yes | decoration, luxury |
| Statue | 4x Stone, Special Tool | Workbench | 360s | Yes | decoration, art |
| Stained Glass | 2x Glass, 1x Dye | Glass Workshop | 180s | Yes | decoration, glass |

### 5.4 Item Visual Representation

Items have consistent visual language:

```python
# Item glyph categories
ITEM_GLYPHS = {
    "weapon": "!",       # Sword/weapon
    "tool": "/",         # General tool
    "container": "U",    # Barrel/crate
    "furniture": "#",    # Tables/chairs
    "food": "%",         # Food items
    "potion": "!",       # Bottles (different from weapon by color)
    "material": "o",     # Generic material
    "gem": "+",          # Gems/jewelry
    "cloth": "~",        # Fabric items
}

# Quality affects color saturation
def get_item_color(base_color, quality):
    if quality < 0.20:
        return desaturate(base_color, 0.5)  # Gray-ish
    elif quality < 0.50:
        return base_color  # Normal
    elif quality < 0.80:
        return saturate(base_color, 1.2)  # More vivid
    elif quality < 1.10:
        return saturate(base_color, 1.4)  # Very vivid
    else:
        return (255, 215, 0)  # Masterwork gold tint
```

---

## 6. Tools

### 6.1 Tool Categories

Tools are required for many crafting operations and lose durability with use.

| Tool | Durability | Weight | Required For | Tags |
|------|------------|--------|--------------|------|
| **Hammer** | 100 | 2 | Metalworking, Construction | tool, smithing |
| **Tongs** | 100 | 1 | Forging | tool, smithing |
| **Saw** | 100 | 3 | Woodworking | tool, woodwork |
| **Chisel** | 100 | 1 | Fine woodwork, Stone carving | tool, precision |
| **Needle** | 50 | 0.1 | Sewing, Tailoring | tool, textile |
| **Pestle** | 100 | 1 | Grinding, Alchemy | tool, alchemy |
| **Pickaxe** | 100 | 4 | Mining | tool, mining |
| **Axe** | 100 | 3 | Chopping | tool, woodwork |
| **Knife** | 100 | 0.5 | General cutting | tool, general |
| **Bellows** | 200 | 5 | Forge heating | tool, smithing |
| **Crucible** | 150 | 2 | Smelting | tool, smithing |
| **Mold** | 100 | 1 | Casting | tool, smithing |

### 6.2 Tool Quality Effects

Higher quality tools improve output quality:

```
Tool_Quality_Contribution = (tool_quality * tool_weight) / total_tool_weights
```

### 6.3 Tool Durability Visual

```
Durability States:
100-70%:  Normal display
 70-40%:  Slightly faded, "wear" particles on use
 40-10%:  Warning badge (!), visible cracks in sprite
  <10%:   Critical (!!), flickering, red tint
    0%:   Tool breaks, disappears with particles
```

### 6.4 Tool Recipes

| Tool | Inputs | Workshop | Time | Special |
|------|--------|----------|------|---------|
| Hammer | 1x Iron Ingot, 1x Handle | Forge | 30s | - |
| Tongs | 2x Iron Ingot | Forge | 25s | - |
| Saw | 1x Iron Ingot, 1x Handle | Forge | 35s | Requires Hammer |
| Chisel | 1x Steel Ingot, 1x Handle | Forge | 40s | Precision work |
| Needle | 1x Steel Ingot | Forge | 20s | Very fine work |
| Pickaxe | 2x Iron Ingot, 1x Handle | Forge | 45s | Heavy duty |

---

## 7. Workshops

### 7.1 Workshop Overview

Workshops are special items that must be deployed in workshop areas. Once deployed, they become immobile and can process crafting tasks.

| Workshop | Size | Slots | Durability | Tags | Products |
|----------|------|-------|------------|------|----------|
| **Workbench** | 2x2 | 2 | 1000 | woodwork, basic | Furniture, handles |
| **Forge** | 3x3 | 3 | 1000 | metalwork, smithing | Ingots, tools, weapons |
| **Loom** | 2x2 | 2 | 1000 | textile, weaving | Cloth, rope, tapestry |
| **Oven** | 2x2 | 2 | 800 | cooking, baking | Bread, pastries |
| **Brewery** | 2x3 | 2 | 1000 | brewing, fermentation | Ale, wine |
| **Alchemy Table** | 2x2 | 1 | 800 | alchemy, enchanting | Potions, enchanted items |
| **Glass Workshop** | 2x2 | 2 | 800 | glass, precision | Glassware, windows |
| **Tanning Rack** | 2x1 | 1 | 600 | leather, processing | Leather |
| **Kiln** | 2x2 | 2 | 1000 | pottery, firing | Pottery, bricks |
| **Sawmill** | 3x2 | 3 | 1200 | woodwork, processing | Planks |

### 7.2 Workshop Details

#### Forge
```
+---+---+---+
| F | F | F |   F = Forge cell
+---+---+---+   * = Working area (deposits go here)
| F | * | F |   
+---+---+---+   Glow: Orange light when active
| F | F | F |   Particles: Sparks upward
+---+---+---+   
```

**Visual Effects (RUNNING)**:
```python
forge_light = pyunicodegame.create_light(
    x=center_x, y=center_y,
    radius=10, color=(255, 150, 50),
    intensity=0.7, falloff=1.2
)

forge_sparks = pyunicodegame.create_emitter(
    x=center_x, y=center_y - 1,
    chars="*.", colors=[(255, 200, 50), (255, 150, 30)],
    spawn_rate=10, speed=5, direction=90, arc=45,
    drag=0.4, fade_time=0.5
)
```

#### Loom
```
+---+---+
| L | L |   L = Loom cell
+---+---+   Threads animate when weaving
| L | * |   Subtle click sounds (future)
+---+---+
```

**Visual Effects (RUNNING)**:
```python
loom_particles = pyunicodegame.create_emitter(
    x=center_x, y=center_y,
    chars="~-", colors=[(200, 200, 255)],
    spawn_rate=3, speed=1, direction=0, arc=180,
    drag=0.9, fade_time=1.0
)
```

#### Alchemy Table
```
+---+---+
| A | A |   A = Alchemy table cell
+---+---+   Bubbles and mystical glow
| A | * |   
+---+---+
```

**Visual Effects (RUNNING)**:
```python
alchemy_light = pyunicodegame.create_light(
    x=center_x, y=center_y,
    radius=6, color=(150, 100, 255),
    intensity=0.5, falloff=1.0
)

alchemy_bubbles = pyunicodegame.create_emitter(
    x=center_x, y=center_y,
    chars="o.", colors=[(150, 100, 255), (200, 150, 255)],
    spawn_rate=5, speed=2, direction=90, arc=30,
    drag=0.8, fade_time=1.2
)
```

### 7.3 Workshop States

| State | Visual | Description |
|-------|--------|-------------|
| **IDLE** | Dim, static | No active tasks |
| **READY** | Pulsing outline | All inputs present, can start |
| **RUNNING** | Glowing, particles | Task in progress |
| **COMPLETE** | Burst effect | Output ready |
| **BLOCKED** | Red outline | Cannot start (missing tool/space) |

### 7.4 Workshop Input Slots

Each workshop has designated input cells:

```
Forge input layout (example):
+---+---+---+
|   | 1 |   |   Slot 1: Primary material
+---+---+---+   Slot 2: Secondary material
| 2 | W | 3 |   Slot 3: Fuel
+---+---+---+   W: Work area (tool check)
|   |OUT|   |   OUT: Output appears here
+---+---+---+
```

**Slot States**:
- Empty: `o` (dim)
- Valid item adjacent: `O` (bright, pulsing)
- Filled: `@` (solid)
- Wrong item: `x` (red flash, item bounces)

### 7.5 Workshop Recipes

Workshops can be crafted like other items but require significant resources:

| Workshop | Inputs | Built At | Time | Required Skill |
|----------|--------|----------|------|----------------|
| Workbench | 6x Plank, 4x Nails | Outdoors | 120s | Furniture 0.2 |
| Forge | 20x Stone, 10x Iron Ingot, 2x Bellows | Workbench | 300s | Masonry 0.3 |
| Loom | 8x Plank, 4x Rope | Workbench | 180s | Furniture 0.2 |
| Alchemy Table | 4x Plank, 2x Glass, 1x Gem | Workbench | 240s | Enchanting 0.3 |

---

## 7.5 Dispensers

Dispensers are special storage cells that auto-replenish items when pushed away. They are the backbone of the batch crafting system.

### 7.5.1 Dispenser Overview

| Property | Value |
|----------|-------|
| **Size** | 1x1 cell |
| **Capacity** | 10-50 items (varies by type) |
| **Moveable** | No (fixed infrastructure) |
| **Placement** | Storage zones only |
| **Interaction** | Push to stock, push away to retrieve |

### 7.5.2 Dispenser Types

| Type | Glyph | Color | Capacity | Typical Contents |
|------|-------|-------|----------|------------------|
| **Ore Dispenser** | `[*]` | Gray | 20 | Iron Ore, Copper Ore, Coal |
| **Wood Dispenser** | `[=]` | Brown | 15 | Oak Log, Pine Log, Plank |
| **Fiber Dispenser** | `[~]` | White | 25 | Cotton, Flax, Thread |
| **Food Dispenser** | `[%]` | Yellow | 30 | Wheat, Barley, Herbs |
| **Metal Dispenser** | `[#]` | Silver | 15 | Ingots (any type) |
| **General Dispenser** | `[o]` | Neutral | 10 | Any single item type |

### 7.5.3 Dispenser States

| State | Visual | Badge | Description |
|-------|--------|-------|-------------|
| **Stocked** | Normal color | None | 5+ items remaining |
| **Low** | Dimmer, subtle pulse | None | 2-4 items remaining |
| **Critical** | Orange tint | `!` | 1 item remaining |
| **Empty** | Gray outline | None | 0 items, shows last item type ghosted |

### 7.5.4 Dispenser Mechanics

**Retrieving Items (Push Away)**:
```
Before push:     [Fe]  ← Iron Ore visible
                   ↓
Player pushes:   [Fe] → Fe  ← Item pushed out
                   ↓
Auto-replenish:  [Fe]  ← Next item rises up (if stock > 0)
```

**Stocking Items (Push Toward)**:
```
Player pushes item toward dispenser:
   Fe → [Fe]
         ↓
Item absorbed, count increases:
       [Fe]+1
```

### 7.5.5 Dispenser Data Structure

```python
Dispenser = {
    "id": "dispenser_ore_001",
    "type": "ore",
    "position": {"x": 15, "y": 8},
    "item_type": "iron_ore",          # Currently stocked item type
    "inventory_count": 12,            # Items in stock
    "max_capacity": 20,               # Maximum items
    "last_restocked": "2026-01-09",   # For analytics
}
```

### 7.5.6 Dispenser Visual Effects

**Replenish Animation**:
```python
def replenish_dispenser(dispenser, item_type):
    # Create new item slightly below surface
    new_item = create_item(item_type, dispenser.x, dispenser.y)
    new_item.sprite.y_offset = 8  # Start 8 pixels below
    
    # Rise up animation
    new_item.sprite.lerp_to(y_offset=0, speed=40)
    
    # Small dust puff
    pyunicodegame.create_emitter(
        x=dispenser.x, y=dispenser.y,
        chars=".", colors=[(180, 180, 200)],
        spawn_rate=8, emitter_duration=0.1,
        speed=2, direction=90, arc=120,
        drag=0.7, fade_time=0.3, max_particles=6
    )
```

**Stocking Animation**:
```python
def stock_dispenser(dispenser, item):
    # Item slides into dispenser
    item.sprite.lerp_to(x=dispenser.x, y=dispenser.y, speed=12)
    
    # Absorption flash
    pyunicodegame.create_emitter(
        x=dispenser.x, y=dispenser.y,
        chars="+", colors=[(100, 255, 100)],
        spawn_rate=15, emitter_duration=0.1,
        speed=3, arc=360, fade_time=0.25, max_particles=10
    )
    
    # Update inventory
    dispenser.inventory_count += 1
    
    # Remove absorbed item from world
    destroy_item(item)
```

**Low Stock Warning**:
```python
def update_dispenser_visual(dispenser):
    if dispenser.inventory_count == 0:
        # Empty - gray outline, ghost of last item
        dispenser.sprite.fg = (60, 60, 60)
        dispenser.sprite.alpha = 0.3
    elif dispenser.inventory_count == 1:
        # Critical - orange tint, warning badge
        dispenser.sprite.fg = (255, 180, 100)
        show_badge(dispenser, "!", (255, 150, 50))
    elif dispenser.inventory_count <= 4:
        # Low - subtle pulse
        dispenser.sprite.add_animation(pulse_animation)
    else:
        # Normal
        dispenser.sprite.fg = get_dispenser_color(dispenser.type)
```

### 7.5.7 Dispenser Rules

| Rule | Description |
|------|-------------|
| **Single Type** | Each dispenser holds only one item type at a time |
| **Type Lock** | Once stocked, dispenser only accepts same item type |
| **Type Clear** | When empty, dispenser can accept any valid item type |
| **No Overflow** | Items pushed to full dispenser bounce back |
| **Player Only** | Only player-controlled monsters can stock dispensers |
| **Fixed Position** | Dispensers cannot be pushed or moved |

### 7.5.8 Dispenser Placement in Storage Zones

Typical Storage zone layout:
```
STORAGE ZONE (8x8 example)
+---+---+---+---+---+---+---+---+
| o | o | o |   |   | o | o | o |  o = Ore dispensers
+---+---+---+---+---+---+---+---+
| = | = | = |   |   | ~ | ~ | ~ |  = = Wood dispensers
+---+---+---+---+---+---+---+---+  ~ = Fiber dispensers
|   |   |   |   |   |   |   |   |
+---+---+---+---+---+---+---+---+  Central area = 
|   |   |       PATH      |   |   pathways for
+---+---+---+---+---+---+---+---+  pushing items
|   |   |   |   |   |   |   |   |
+---+---+---+---+---+---+---+---+
| % | % | % |   |   | # | # | # |  % = Food dispensers
+---+---+---+---+---+---+---+---+  # = Metal dispensers
| % | % | % |   |   | # | # | # |
+---+---+---+---+---+---+---+---+
```

---

## 8. Tech Tree

### 8.1 Tech Tree Overview

The tech tree represents the progression of crafting complexity.

```
TIER 0: Raw Materials
   |
   v
TIER 1: Basic Processing
   |--- Wood: Log -> Plank -> Handle
   |--- Metal: Ore -> Ingot
   |--- Fiber: Cotton/Flax -> Thread
   |
   v
TIER 2: Basic Items
   |--- Tools: Hammer, Tongs, Saw
   |--- Materials: Steel, Bronze, Leather
   |
   v
TIER 3: Complex Items
   |--- Equipment: Weapons, Armor
   |--- Furniture: Tables, Chairs
   |--- Consumables: Food, Potions
   |
   v
TIER 4: Advanced Items
   |--- Refined: Fine weapons, luxury goods
   |--- Magical: Enchanted items
   |
   v
TIER 5: Legendary
   |--- Masterwork items
   |--- Unique artifacts
```

### 8.2 Detailed Tech Tree

#### Wood Path
```
Oak Log (T0)
  |
  +-> Plank (T1) [Saw]
        |
        +-> Handle (T1) [Workbench]
        |     |
        |     +-> Hammer (T2) [+ Iron Ingot, Forge]
        |     +-> Axe (T2) [+ Iron Ingot, Forge]
        |     +-> Furniture Handles
        |
        +-> Chair (T2) [Workbench, + Handle]
        +-> Table (T3) [Workbench, + 2 Handle]
        +-> Barrel (T2) [Workbench]
        +-> Crate (T1) [Workbench]
```

#### Metal Path
```
Iron Ore (T0)
  |
  +-> Iron Ingot (T1) [Forge, + Coal]
        |
        +-> Nails (T1) [Forge]
        +-> Chain (T2) [Forge]
        +-> Tools (T2) [+ Handle]
        |     |
        |     +-> Hammer, Tongs, Saw, etc.
        |
        +-> Steel Ingot (T2) [Forge, + more Coal]
              |
              +-> Steel Tools (T3)
              +-> Steel Weapons (T3)
              +-> Fine Metalwork (T4)

Copper Ore (T0)
  |
  +-> Copper Ingot (T1) [Forge]
        |
        +-> Bronze Ingot (T2) [+ Tin Ore]
              |
              +-> Bronze Tools (T2)
              +-> Bronze Decorations (T3)

Gold Ore (T0)
  |
  +-> Gold Ingot (T1) [Forge]
        |
        +-> Jewelry (T3) [+ Gems]
        +-> Enchanted Items (T4) [Alchemy Table]
```

#### Fiber Path
```
Cotton/Flax (T0)
  |
  +-> Thread (T1) [Loom]
        |
        +-> Cloth (T2) [Loom]
        |     |
        |     +-> Clothes (T3)
        |     +-> Tapestry (T4) [+ Dye]
        |
        +-> Rope (T2) [Loom]
              |
              +-> Bindings (T2)
              +-> Wagon Parts (T3)

Hide (T0)
  |
  +-> Leather (T1) [Tanning Rack]
        |
        +-> Leather Armor (T3)
        +-> Fine Leather (T2)
              |
              +-> Luxury Goods (T4)
```

#### Alchemy Path
```
Herbs (T0) + Water
  |
  +-> Healing Potion (T2) [Alchemy Table]
  +-> Enchanting Ink (T2) [Alchemy Table, + Gems]
        |
        +-> Rune Stone (T3)
        +-> Enchanted Weapon (T4) [+ Weapon]
        +-> Enchanted Ring (T4) [+ Gold Ring]
```

### 8.3 Tech Tree Visualization (In-Game)

The tech tree can be displayed as a network graph:

```
+----------------------------------------------+
|                 TECH TREE                    |
|----------------------------------------------|
|                                              |
|   [Log]--->[Plank]--->[Handle]--->[Hammer]   |
|              |                       |       |
|              v                       v       |
|           [Chair]            [Iron Sword]    |
|              |                       |       |
|              v                       v       |
|           [Table]            [Steel Sword]   |
|                                              |
|   Legend: [ ] = Discovered  [?] = Unknown    |
|           --> = Requires                     |
+----------------------------------------------+
```

### 8.4 Recipe Unlocking

Recipes unlock through:
1. **Skill Level**: Reach required skill level
2. **Discovery**: Find recipe books in world
3. **NPC Teaching**: Learn from master NPCs
4. **Experimentation**: Try valid combinations

---

## 9. Locations

### 9.1 Location Types

| Type | Function | Contains | Movement |
|------|----------|----------|----------|
| **City** | Hub container | All local zones | Portal to zones |
| **Workshop Area** | Crafting | Deployed workshops | Walk |
| **Raw Resource** | Gathering | Resource nodes | Walk |
| **Storage Zone** | Item dispensers | Dispensers by category | Walk |
| **Drop-off** | Scoring | Accepted goods | Walk |
| **Road** | Inter-city | Wagons, travelers | Walk (slow) |

### 9.2 City Layout Example

```
IRONFORGE CITY (32x32 cells)
+--------------------------------+
|  FOREST    |    MINE           |
|   [T][T]   |   [*][*][*]       |
|   [T][T]   |                   |
|------------|-------------------|
|  WORKSHOP DISTRICT             |
|   [Forge]  [Workbench]  [Loom] |
|   [Forge]  [Alchemy]           |
|--------------------------------|
|  STORAGE ZONE  |   DROP-OFF    |
|   [o][o][=][=] |      [D]      |
|   [~][~][#][#] |               |
|----------------|---------------|
|            ROAD TO OAKVILLE -> |
+--------------------------------+

Legend:
[T] = Tree (harvestable)
[*] = Ore node
[o] = Ore dispenser
[=] = Wood dispenser
[~] = Fiber dispenser
[#] = Metal dispenser
[D] = Drop-off zone
```

### 9.2.1 Storage Zone Detail

Storage zones contain organized dispensers for batch crafting:

```
STORAGE ZONE (12x8 detailed view)
+---+---+---+---+---+---+---+---+---+---+---+---+
| o | o | o |   |   | = | = | = |   |   | ~ | ~ |
|Fe |Fe |Cu |   |   |Oak|Oak|Pin|   |   |Cot|Flx|
+---+---+---+---+---+---+---+---+---+---+---+---+
| o | o |   |       PATH        |   | ~ | ~ |   |
|Co |Co |   |                   |   |Wol|Thr|   |
+---+---+---+---+---+---+---+---+---+---+---+---+
|   |   |   |                   |   |   |   |   |
|   |   |   |    (open for      |   |   |   |   |
+---+---+---+    pushing items) +---+---+---+---+
|   |   |   |                   |   |   |   |   |
|   |   |   |                   |   |   |   |   |
+---+---+---+---+---+---+---+---+---+---+---+---+
| # | # | # |   |   | % | % | % |   |   | + | + |
|Irn|Stl|Brz|   |   |Wht|Bar|Hrb|   |   |Gem|Gld|
+---+---+---+---+---+---+---+---+---+---+---+---+

Dispenser Labels:
Fe = Iron Ore    Oak = Oak Log     Cot = Cotton
Cu = Copper Ore  Pin = Pine Log    Flx = Flax
Co = Coal        Wol = Wool        Thr = Thread
Irn = Iron Ingot Wht = Wheat       Gem = Gems
Stl = Steel Ingot Bar = Barley     Gld = Gold Ore
Brz = Bronze Ingot Hrb = Herbs
```

**Design Principles for Storage Zones**:
1. **Clear pathways** - Wide lanes for pushing items without obstruction
2. **Category grouping** - Similar items clustered together
3. **Proximity to workshops** - Shorter paths = faster batch cycles
4. **Expansion space** - Room to add more dispensers as needed

### 9.3 Zone Connections

Cities are connected via roads:

```
       [Ironforge]
            |
           road
            |
    [Oakville]---road---[Coastport]
            |               |
           road            road
            |               |
      [Deepmine]      [Farmstead]
```

Travel between cities requires:
- Wagon for goods
- Time (multiple ticks per road segment)
- Wagon Driving skill affects speed

### 9.4 Resource Node Details

| Node Type | Glyph | Color | Products | Regeneration |
|-----------|-------|-------|----------|--------------|
| Oak Tree | `T` | Brown/Green | Oak Log | 1 day |
| Pine Tree | `Y` | Dark Green | Pine Log | 1 day |
| Iron Vein | `*` | Gray | Iron Ore | 2 days |
| Gold Vein | `*` | Gold | Gold Ore | 7 days |
| Wheat Field | `%` | Yellow | Wheat | 12 hours |
| Herb Patch | `"` | Green | Herbs | 1 day |

### 9.5 Location Visual Themes

Each location type has distinct visual characteristics:

```python
LOCATION_THEMES = {
    "forest": {
        "floor": (".", (50, 80, 50)),      # Dark green floor
        "ambient": (40, 60, 40),            # Green tint lighting
        "particles": "leaf_fall"            # Occasional falling leaves
    },
    "mine": {
        "floor": (".", (60, 60, 70)),      # Gray stone floor
        "ambient": (30, 30, 40),            # Dark, blue tint
        "particles": "dust_drift"           # Floating dust
    },
    "workshop": {
        "floor": (",", (80, 70, 60)),      # Wooden floor
        "ambient": (60, 55, 50),            # Warm indoor
        "particles": None
    },
    "farm": {
        "floor": (".", (80, 70, 50)),      # Dirt/grass
        "ambient": (80, 80, 70),            # Bright outdoor
        "particles": "pollen_drift"
    }
}
```

---

## 10. Visual Specifications

### 10.1 Color Palette

#### Monster Colors
| Monster | Primary | Secondary | Accent |
|---------|---------|-----------|--------|
| Cyclops | #A67C52 (tan) | #8B4513 (brown) | #FFD700 (gold eye) |
| Elf | #90EE90 (light green) | #228B22 (forest) | #C0C0C0 (silver) |
| Goblin | #32CD32 (lime) | #006400 (dark green) | #FF6347 (red ears) |
| Orc | #808080 (gray) | #696969 (dark gray) | #8B0000 (dark red) |
| Troll | #556B2F (olive) | #2F4F4F (dark slate) | #00FF00 (green eyes) |

#### Quality Colors
| Tier | Hex | RGB | Usage |
|------|-----|-----|-------|
| Poor | #786450 | (120, 100, 80) | Desaturated items |
| Common | #C8C8C8 | (200, 200, 200) | Standard items |
| Good | #96C8FF | (150, 200, 255) | Good items |
| Fine | #64FF64 | (100, 255, 100) | Fine items |
| Masterwork | #FFD700 | (255, 215, 0) | Masterwork items |

#### Workshop Colors (Active)
| Workshop | Glow Color | Particle Color |
|----------|------------|----------------|
| Forge | #FF9632 | #FFC832 (sparks) |
| Loom | #C8C8FF | #E0E0FF (threads) |
| Alchemy | #9664FF | #C896FF (bubbles) |
| Kitchen | #FFAA64 | #FFFFFF (steam) |
| Brewery | #AA8855 | #DDBB88 (foam) |

### 10.2 Particle Effect Presets

```python
PARTICLE_PRESETS = {
    # Movement dust
    "push_dust": {
        "chars": ".",
        "colors": [(120, 100, 80)],
        "spawn_rate": 20,
        "emitter_duration": 0.1,
        "speed": 2,
        "arc": 60,
        "drag": 0.7,
        "fade_time": 0.3,
        "max_particles": 8
    },
    
    # Craft completion
    "craft_burst": {
        "chars": "*+.",
        "colors": [(255, 255, 100), (255, 200, 50)],
        "spawn_rate": 50,
        "emitter_duration": 0.15,
        "speed": 8,
        "arc": 360,
        "drag": 0.3,
        "fade_time": 0.7,
        "max_particles": 30
    },
    
    # Workshop running - forge
    "forge_sparks": {
        "chars": "*.",
        "colors": [(255, 200, 50), (255, 150, 30)],
        "spawn_rate": 10,
        "speed": 5,
        "direction": 90,
        "arc": 45,
        "drag": 0.4,
        "fade_time": 0.5,
        "max_particles": 20
    },
    
    # Workshop running - alchemy
    "alchemy_bubbles": {
        "chars": "o.",
        "colors": [(150, 100, 255), (200, 150, 255)],
        "spawn_rate": 5,
        "speed": 2,
        "direction": 90,
        "arc": 30,
        "drag": 0.8,
        "fade_time": 1.2,
        "max_particles": 15
    },
    
    # Item deposit suction
    "deposit_suction": {
        "chars": ".",
        "colors": [(200, 200, 255)],
        "spawn_rate": 30,
        "emitter_duration": 0.1,
        "speed": 4,
        "arc": 90,  # Inward
        "drag": 0.5,
        "fade_time": 0.25,
        "max_particles": 15
    },
    
    # Error/blocked
    "blocked_burst": {
        "chars": "x",
        "colors": [(255, 80, 80)],
        "spawn_rate": 10,
        "emitter_duration": 0.1,
        "speed": 3,
        "arc": 360,
        "drag": 0.6,
        "fade_time": 0.3,
        "max_particles": 8
    },
    
    # Masterwork sparkle
    "masterwork_sparkle": {
        "chars": ".",
        "colors": [(255, 255, 200), (255, 215, 0)],
        "spawn_rate": 1,
        "speed": 1,
        "arc": 360,
        "drag": 0.9,
        "fade_time": 1.0,
        "max_particles": 4
    },
    
    # Tool wear chips
    "tool_wear": {
        "chars": ".",
        "colors": [(100, 100, 100)],
        "spawn_rate": 5,
        "emitter_duration": 0.05,
        "speed": 2,
        "arc": 180,
        "drag": 0.6,
        "fade_time": 0.3,
        "max_particles": 3
    }
}
```

### 10.3 Animation Specifications

```python
ANIMATION_PRESETS = {
    # Monster walk bob
    "walk": {
        "frame_indices": [0, 1, 0, 2],
        "frame_duration": 0.15,
        "offsets": [(0, 0), (0, -1), (0, 0), (0, -1)],
        "loop": True,
        "offset_speed": 50
    },
    
    # Push strain
    "push": {
        "frame_indices": [0, 3, 3, 0],
        "frame_duration": 0.1,
        "offsets": [(0, 0), (1, 0), (0, 0)],
        "loop": False,
        "offset_speed": 30
    },
    
    # Blocked shake
    "blocked_shake": {
        "frame_indices": [0],
        "frame_duration": 0.05,
        "offsets": [(-2, 0), (2, 0), (-1, 0), (1, 0), (0, 0)],
        "loop": False,
        "offset_speed": 100
    },
    
    # Item deposit slide
    "deposit_slide": {
        "frame_indices": [0],
        "frame_duration": 0.2,
        "offsets": [(0, 0), (4, 0), (8, 0)],  # Slides into slot
        "loop": False,
        "offset_speed": 40
    },
    
    # Speech bubble pop
    "bubble_pop": {
        "frame_indices": [0],
        "frame_duration": 0.08,
        "offsets": [(0, 4), (0, 2), (0, 0)],
        "loop": False,
        "offset_speed": 100
    }
}
```

### 10.4 Lighting Presets

```python
LIGHTING_PRESETS = {
    # Controlled monster aura
    "player_aura": {
        "radius": 8,
        "color": (100, 200, 255),
        "intensity": 0.8,
        "falloff": 1.5,
        "casts_shadows": True
    },
    
    # Active forge
    "forge_glow": {
        "radius": 10,
        "color": (255, 150, 50),
        "intensity": 0.7,
        "falloff": 1.2,
        "casts_shadows": True
    },
    
    # Alchemy table
    "alchemy_glow": {
        "radius": 6,
        "color": (150, 100, 255),
        "intensity": 0.5,
        "falloff": 1.0,
        "casts_shadows": False
    },
    
    # Torch/lamp
    "torch": {
        "radius": 8,
        "color": (255, 200, 100),
        "intensity": 0.6,
        "falloff": 1.3,
        "casts_shadows": True
    },
    
    # Masterwork item glow
    "masterwork_glow": {
        "radius": 3,
        "color": (255, 215, 0),
        "intensity": 0.4,
        "falloff": 0.8,
        "casts_shadows": False
    },
    
    # Craft completion flash
    "completion_flash": {
        "radius": 12,
        "color": (255, 255, 200),
        "intensity": 2.0,
        "falloff": 0.5,
        "casts_shadows": False
    }
}

# Ambient lighting by zone
AMBIENT_PRESETS = {
    "outdoor_day": (80, 80, 90),
    "outdoor_dusk": (60, 50, 60),
    "outdoor_night": (15, 15, 25),
    "indoor_workshop": (40, 40, 50),
    "indoor_home": (50, 45, 40),
    "underground": (10, 10, 15),
    "forest": (40, 60, 40),
    "mine": (30, 30, 40)
}
```

### 10.5 Bloom Presets

```python
BLOOM_PRESETS = {
    # Default subtle bloom
    "default": {
        "enabled": True,
        "threshold": 220,
        "blur_scale": 2,
        "intensity": 0.5
    },
    
    # Important event (craft complete, masterwork)
    "event": {
        "enabled": True,
        "threshold": 180,
        "blur_scale": 4,
        "intensity": 1.2
    },
    
    # Night mode (more visible lights)
    "night": {
        "enabled": True,
        "threshold": 200,
        "blur_scale": 3,
        "intensity": 0.8
    },
    
    # Underground (dramatic lighting)
    "underground": {
        "enabled": True,
        "threshold": 190,
        "blur_scale": 4,
        "intensity": 1.0
    }
}
```

---

## 11. Formulas

### 11.1 Quality Roll Formula

For goods with variable quality:

```python
def calculate_quality(monster, batch, good_type):
    # Average input quality
    if batch.input_goods.count() == 0:
        avg_input_quality = 1.0
    else:
        avg_input_quality = mean([g.quality for g in batch.input_goods])
    
    # Skill values
    primary_skill = monster.get_skill(good_type.primary_applied_skill).value
    secondary_avg = mean([monster.get_skill(s).value 
                          for s in good_type.secondary_applied_skills])
    specific_skill = monster.get_specific_skill(good_type).value
    
    # Tool quality (weighted)
    tool_quality_avg = weighted_tool_quality(batch, good_type)
    
    # Ability factor
    ability = monster.effective_ability(good_type.relevant_ability_score)
    ability_factor = min(1.2, ability / good_type.difficulty_rating)
    
    # Mean for normal distribution
    mu = (avg_input_quality * primary_skill * secondary_avg + 
          tool_quality_avg * specific_skill * ability_factor)
    
    # Sigma (variance from destabilizer skills)
    destabilizer_avg = mean([monster.get_skill(s).value 
                             for s in good_type.destabilizer_skills])
    sigma = 0.1 + (destabilizer_avg / 10)
    
    # Roll
    quality = max(0, random.gauss(mu, sigma))
    
    # Monster modification (WIS + STR bonus)
    distance_from_perfect = max(1 - quality, 0)
    wis_str_bonus = (monster.WIS + monster.STR * 0.25) / 25
    quality += wis_str_bonus * distance_from_perfect * 0.25
    
    return quality
```

### 11.2 Quantity Roll Formula

```python
def calculate_quantity(monster, batch, good_type):
    base_quantity = good_type.quantity
    
    # Skill and ability factors
    ability = monster.effective_ability(good_type.relevant_ability_score)
    primary_skill = monster.get_skill(good_type.primary_applied_skill).value
    specific_skill = monster.get_specific_skill(good_type).value
    tool_quality_avg = weighted_tool_quality(batch, good_type)
    secondary_avg = mean([monster.get_skill(s).value 
                          for s in good_type.secondary_applied_skills])
    
    # Sigma for normal distribution
    sigma = (base_quantity * 0.05 * ability * primary_skill * 
             specific_skill * tool_quality_avg * secondary_avg)
    
    # Roll (always positive)
    quantity = abs(random.gauss(0, sigma)) + base_quantity
    
    # Monster modification (STR + DEX bonus)
    str_mult = (monster.STR - 10) / 10
    dex_mult = (monster.DEX - 10) / 10 * 0.25
    quantity += quantity * str_mult
    quantity += quantity * dex_mult
    
    return max(1, round(quantity))
```

### 11.3 Value Calculation

```python
def calculate_value(good):
    # Raw materials
    if good.is_raw_material():
        return good.raw_material_base_value * (good.quality + 0.5) ** 0.5
    
    # Crafted goods
    raw_materials, max_depth = good.get_raw_materials_and_depth()
    raw_value_sum = sum([rm.raw_material_base_value for rm in raw_materials])
    
    value = raw_value_sum * (good.quality + 0.5) ** (0.5 + 0.5 * max_depth)
    
    # Monster CHA bonus
    monster = good.created_by_batch.production_task.monster
    cha_bonus = (10 + monster.CHA / 2) / 10
    value *= cha_bonus
    
    return round(value)
```

### 11.4 Production Time Calculation

```python
def calculate_production_time(monster, task, num_batches):
    base_time = num_batches * task.output_good_type.production_time
    
    # DEX and INT modifiers
    time = base_time * (10 / monster.DEX)
    time *= (30 / (20 + monster.INT))
    
    # Equipment bonuses
    for eq in monster.equipment:
        time += eq.production_time_bonus(base_time, monster, task)
    
    return max(1, round(time))  # Minimum 1 second
```

### 11.5 Transport Calculation

```python
def calculate_transport_time(monster, task):
    base_time = 6 * task.task_multiplier  # 6 seconds per trip
    
    # CON and CHA modifiers
    time = base_time * (10 / monster.CON)
    time *= (30 / (20 + monster.CHA))
    
    # Equipment bonuses
    for eq in monster.equipment:
        time += eq.transport_time_bonus(base_time, monster, task)
    
    return max(1, round(time))

def calculate_transport_capacity(monster, task):
    skill = task.relevant_applied_skill()
    capacity = 1 + skill.value
    
    if task.is_wagon_journey():
        capacity *= monster.CHA
    else:
        capacity *= monster.STR
    
    # Equipment bonuses
    for eq in monster.equipment:
        capacity += eq.transport_weight_bonus(capacity, monster, task)
    
    return capacity
```

### 11.6 Learning Rate Calculation

```python
def calculate_learning(monster, task, skill_type):
    int_con = (monster.INT * 0.8 + monster.CON * 0.2) / 20
    
    if skill_type == "specific":
        primary_skill = monster.get_skill(task.output_good_type.primary_applied_skill)
        rate = 0.002 * (1 - skill.value) * int_con * primary_skill.value
    
    elif skill_type == "primary":
        relevant_trans = count_relevant_transferable_skills(monster, task)
        trans_factor = 1 + (relevant_trans / 4)
        rate = 0.001 * (1 - skill.value) * int_con * trans_factor
    
    elif skill_type == "secondary":
        rate = 0.0005 * (1 - skill.value) * int_con
    
    elif skill_type == "transport":
        rate = 0.001 * (1 - skill.value) * int_con
    
    # Apply per 10 seconds of task duration
    learning = rate * (task.duration // 10)
    
    # Equipment bonus
    for eq in monster.equipment:
        learning += eq.learning_bonus(learning, monster, task)
    
    return learning
```

### 11.7 Forgetting Rate Calculation

```python
def calculate_forgetting(monster, task):
    wis_factor = 1 - (monster.WIS / 20) * 0.25
    rate = 0.0001 * wis_factor
    
    forgetting = rate * (task.duration // 10)
    
    # Equipment bonus (reduction)
    for eq in monster.equipment:
        forgetting += eq.forgetting_modifier(forgetting, monster, task)
    
    return forgetting
```

### 11.8 Weight Calculation

```python
def calculate_weight(good):
    if good.is_workshop():
        return 100000  # Fixed workshop weight
    
    if good.is_raw_material():
        return good.density * good.storage_volume
    
    # Crafted goods use average density of raw materials
    raw_materials, _ = good.get_raw_materials_and_depth()
    avg_density = mean([rm.density for rm in raw_materials])
    return avg_density * good.storage_volume
```

### 11.9 Upkeep Calculation

```python
def calculate_upkeep(commune):
    total_monster_value = sum([
        MONSTER_TYPES[m.monster_type].renown_cost 
        for m in commune.monsters
    ])
    
    upkeep = max(0, ((total_monster_value / 10) - 100)) ** 1.5
    return upkeep
```

### 11.10 Cost Multiplier

```python
def calculate_cost_multiplier(commune):
    total_spent = sum([
        MONSTER_TYPES[m.monster_type].renown_cost +
        sum([EQUIPMENT_TYPES[e].renown_cost for e in m.equipment])
        for m in commune.monsters
    ])
    
    return 1 + (total_spent / 1000)
```

---

## Appendix A: Complete Item ID List

| ID | Item Name | Category | Tier |
|----|-----------|----------|------|
| 001 | Oak Log | Raw | 0 |
| 002 | Pine Log | Raw | 0 |
| 003 | Iron Ore | Raw | 0 |
| 004 | Copper Ore | Raw | 0 |
| 005 | Gold Ore | Raw | 0 |
| ... | ... | ... | ... |
| 101 | Plank | Processed | 1 |
| 102 | Iron Ingot | Processed | 1 |
| 103 | Thread | Processed | 1 |
| ... | ... | ... | ... |
| 201 | Hammer | Tool | 2 |
| 202 | Tongs | Tool | 2 |
| 203 | Saw | Tool | 2 |
| ... | ... | ... | ... |
| 301 | Chair | Furniture | 2 |
| 302 | Table | Furniture | 3 |
| ... | ... | ... | ... |
| 401 | Iron Sword | Weapon | 3 |
| 402 | Steel Sword | Weapon | 3 |
| ... | ... | ... | ... |
| 501 | Forge | Workshop | 2 |
| 502 | Workbench | Workshop | 1 |
| ... | ... | ... | ... |

## Appendix B: Tag Reference

| Tag | Category | Examples |
|-----|----------|----------|
| wood | Material | Logs, planks |
| metal | Material | Ores, ingots |
| fiber | Material | Cotton, thread |
| food | Consumable | Bread, ale |
| tool | Equipment | Hammer, saw |
| weapon | Equipment | Sword, axe |
| furniture | Item | Chair, table |
| container | Item | Barrel, crate |
| workshop | Building | Forge, loom |
| processed | State | Planks, ingots |
| refined | State | Steel, fine leather |
| magical | Property | Enchanted items |
| precious | Property | Gold, gems |

## Appendix C: Skill-Workshop Mapping

| Workshop | Primary Skill | Secondary Skills |
|----------|---------------|------------------|
| Forge | Blacksmithing | Smelting, Metal Crafting |
| Workbench | Furniture | Lutherie, Sculpting |
| Loom | Weaving | Tailoring |
| Kitchen | Baking | Dishes |
| Brewery | Brewing | - |
| Alchemy Table | Potion Making | Enchanting |
| Glass Workshop | Glassware | Windows |

---

*End of Game Objects Reference*
