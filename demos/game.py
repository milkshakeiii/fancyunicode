#!/usr/bin/env python3
"""
Unicode Tyrian - A vertical scrolling shooter
Built with pyunicodegame to showcase visual effects
"""

import pygame
import pyunicodegame
import random
import math

# Game constants
GAME_WIDTH = 60
GAME_HEIGHT = 35
PLAYER_Y = GAME_HEIGHT - 4
BULLET_SPEED = 15  # Slower bullets
ENEMY_BASE_SPEED = 3  # Slower enemies
STAR_SPAWN_RATE = 0.08  # Stars per cell per second
PLAYER_MOVE_SPEED = 12  # Cells per second for held keys
SPRITE_INTERPOLATION_SPEED = 15  # Visual smoothing speed

# Colors
COLOR_PLAYER = (100, 200, 255)
COLOR_PLAYER_GLOW = (80, 180, 255)
COLOR_BULLET = (255, 255, 100)
COLOR_BULLET_GLOW = (255, 255, 150)
COLOR_ENEMY = (255, 80, 80)
COLOR_EXPLOSION = [(255, 200, 50), (255, 150, 30), (255, 100, 0), (255, 50, 0)]
COLOR_STAR_DIM = (60, 60, 80)
COLOR_STAR_BRIGHT = (150, 150, 200)
COLOR_HUD = (100, 255, 100)

# Game state
class GameState:
    def __init__(self):
        self.player_x = float(GAME_WIDTH // 2)  # Float for smooth movement
        self.player_moving = 0  # -1 left, 0 still, 1 right
        self.bank_frame = 0
        self.bank_timer = 0
        self.bullets = []
        self.enemies = []
        self.score = 0
        self.scroll_offset = 0
        self.enemy_spawn_timer = 0
        self.player_health = 3
        self.game_over = False
        self.fire_cooldown = 0  # For held space bar

state = GameState()

# Windows
game_window = None
hud_window = None
stars_far = None

# Player sprite and related
player_sprite = None
player_light = None
player_emitter = None

# Star management
far_stars = []


def create_player():
    """Create player ship with banking frames"""
    global player_sprite, player_light, player_emitter, game_window

    # Create player at starting position with interpolation enabled
    player_sprite = pyunicodegame.create_sprite(
        "▟▙",
        x=int(state.player_x), y=PLAYER_Y,
        fg=COLOR_PLAYER, emissive=True,
        lerp_speed=SPRITE_INTERPOLATION_SPEED
    )

    # Add banking frames
    player_sprite.add_frame("▐▉", fg=COLOR_PLAYER)
    player_sprite.add_frame("▐▌", fg=COLOR_PLAYER)

    game_window.add_sprite(player_sprite)

    # Player light
    player_light = pyunicodegame.create_light(
        x=state.player_x + 1, y=PLAYER_Y,
        radius=8, color=COLOR_PLAYER_GLOW, intensity=0.8,
        follow_sprite=player_sprite
    )
    game_window.add_light(player_light)

    # Engine emitter - flames going down
    player_emitter = pyunicodegame.create_emitter(
        x=state.player_x + 0.5, y=PLAYER_Y + 1,
        chars="▼▽.*",
        colors=[(255, 200, 50), (255, 150, 30), (255, 100, 0)],
        spawn_rate=15,
        spawn_rate_variance=0.3,
        spread=(0.3, 0),
        speed=5,  # Slower flame particles
        speed_variance=0.3,
        direction=270,  # Down
        arc=25,
        drag=0.6,
        fade_time=0.4,
        fade_time_variance=0.2,
        max_particles=40,
        z_index=0
    )
    game_window.add_emitter(player_emitter)


def update_player_banking(dt):
    """Update player banking animation based on movement"""
    if state.player_moving != 0:
        # Banking - progress through frames
        state.bank_timer += dt
        if state.bank_timer > 0.05:
            state.bank_timer = 0
            if state.bank_frame < 2:
                state.bank_frame += 1
    else:
        # Return to neutral
        state.bank_timer += dt
        if state.bank_timer > 0.05:
            state.bank_timer = 0
            if state.bank_frame > 0:
                state.bank_frame -= 1

    player_sprite.current_frame = state.bank_frame
    state.player_moving = 0  # Reset for next frame


def spawn_star(window, stars_list, y=None):
    """Spawn a star in the given window"""
    sx = random.randint(0, GAME_WIDTH - 1)
    sy = y if y is not None else 0
    char = random.choice(['.', '·', '∙', '*', '✦'])
    brightness = random.random()
    color = COLOR_STAR_BRIGHT if brightness > 0.8 else COLOR_STAR_DIM

    star = pyunicodegame.create_sprite(char, x=sx, y=sy, fg=color)
    window.add_sprite(star)
    stars_list.append({'sprite': star, 'y': float(sy)})


def init_stars():
    """Initialize starfield with random stars"""
    global far_stars

    # Populate stars
    for _ in range(40):
        y = random.randint(0, GAME_HEIGHT - 1)
        spawn_star(stars_far, far_stars, y)


def update_stars(dt):
    """Update scrolling starfield"""
    for star_data in far_stars[:]:
        star_data['y'] += 1.5 * dt  # Gentle scroll
        star_data['sprite'].move_to(star_data['sprite'].x, int(star_data['y']))
        if star_data['y'] > GAME_HEIGHT:
            stars_far.remove_sprite(star_data['sprite'])
            far_stars.remove(star_data)

    # Spawn new stars at top
    if random.random() < STAR_SPAWN_RATE:
        spawn_star(stars_far, far_stars, 0)


def fire_bullet():
    """Fire a bullet from player position"""
    bullet_x = int(state.player_x)
    bullet_y = PLAYER_Y - 1

    bullet_sprite = pyunicodegame.create_sprite(
        "┃",
        x=bullet_x, y=bullet_y,
        fg=COLOR_BULLET, emissive=True,
        lerp_speed=SPRITE_INTERPOLATION_SPEED * 2
    )
    game_window.add_sprite(bullet_sprite)

    # Bullet light
    bullet_light = pyunicodegame.create_light(
        x=int(state.player_x), y=PLAYER_Y - 1,
        radius=3, color=COLOR_BULLET_GLOW, intensity=0.6,
        follow_sprite=bullet_sprite
    )
    game_window.add_light(bullet_light)

    state.bullets.append({
        'sprite': bullet_sprite,
        'light': bullet_light,
        'y': float(PLAYER_Y - 1),
        'x': int(state.player_x)
    })


def update_bullets(dt):
    """Update bullet positions"""
    for bullet in state.bullets[:]:
        bullet['y'] -= BULLET_SPEED * dt
        bullet['sprite'].move_to(bullet['x'], int(bullet['y']))

        # Remove if off screen
        if bullet['y'] < -1:
            game_window.remove_sprite(bullet['sprite'])
            game_window.remove_light(bullet['light'])
            state.bullets.remove(bullet)


def spawn_enemy():
    """Spawn an enemy at the top"""
    enemy_type = random.choices(
        ['small', 'medium', 'large'],
        weights=[0.6, 0.3, 0.1]
    )[0]

    x = random.randint(2, GAME_WIDTH - 5)

    if enemy_type == 'small':
        char = random.choice(['⏃', '▼', '◆'])
        sprite = pyunicodegame.create_sprite(
            char, x=x, y=-2,
            fg=COLOR_ENEMY, emissive=True,
            lerp_speed=SPRITE_INTERPOLATION_SPEED
        )
        hp = 1
        speed = ENEMY_BASE_SPEED * 1.5
        width = 1
    elif enemy_type == 'medium':
        sprite = pyunicodegame.create_sprite(
            "▄█▄\n▀▄▀", x=x, y=-2,
            fg=COLOR_ENEMY, emissive=True,
            lerp_speed=SPRITE_INTERPOLATION_SPEED
        )
        hp = 2
        speed = ENEMY_BASE_SPEED
        width = 3
    else:  # large
        sprite = pyunicodegame.create_sprite(
            "╔═⎈═╗\n║▓▓▓║\n╚═╤═╝", x=x, y=-2,
            fg=COLOR_ENEMY, emissive=True,
            lerp_speed=SPRITE_INTERPOLATION_SPEED
        )
        hp = 5
        speed = ENEMY_BASE_SPEED * 0.6
        width = 5

    game_window.add_sprite(sprite)

    # Movement pattern
    pattern = random.choice(['straight', 'sine', 'dive'])

    state.enemies.append({
        'sprite': sprite,
        'x': float(x),
        'y': -2.0,
        'hp': hp,
        'speed': speed,
        'width': width,
        'pattern': pattern,
        'time': 0,
        'type': enemy_type
    })


def update_enemies(dt):
    """Update enemy positions based on their patterns"""
    for enemy in state.enemies[:]:
        enemy['time'] += dt
        enemy['y'] += enemy['speed'] * dt

        if enemy['pattern'] == 'sine':
            enemy['x'] += math.sin(enemy['time'] * 3) * 10 * dt
            enemy['x'] = max(0, min(GAME_WIDTH - enemy['width'], enemy['x']))
        elif enemy['pattern'] == 'dive' and enemy['y'] > GAME_HEIGHT * 0.3:
            # Dive toward player
            dx = state.player_x - enemy['x']
            enemy['x'] += (dx * 0.5) * dt

        enemy['sprite'].move_to(int(enemy['x']), int(enemy['y']))

        # Remove if off screen
        if enemy['y'] > GAME_HEIGHT + 3:
            game_window.remove_sprite(enemy['sprite'])
            state.enemies.remove(enemy)


def spawn_explosion(x, y, size='small'):
    """Spawn explosion particles and light flash"""
    num_particles = {'small': 8, 'medium': 15, 'large': 25}[size]

    for _ in range(num_particles):
        char = random.choice(['*', '+', '.', '░', '▒'])
        color = random.choice(COLOR_EXPLOSION)

        angle = random.uniform(0, 360)
        speed = random.uniform(3, 10)  # Slower explosion particles
        vx = math.cos(math.radians(angle)) * speed
        vy = math.sin(math.radians(angle)) * speed

        particle = pyunicodegame.create_effect(
            pattern=char,
            x=x, y=y,
            vx=vx, vy=vy,
            fg=color,
            drag=0.4,  # More drag
            fade_time=random.uniform(0.4, 1.0),  # Longer fade
            z_index=10
        )
        particle.emissive = True
        game_window.add_sprite(particle)

    # Explosion flash light
    flash = pyunicodegame.create_light(
        x=x, y=y,
        radius=8 if size == 'large' else 5,
        color=(255, 200, 100),
        intensity=2.0
    )
    game_window.add_light(flash)

    # Schedule light removal (handled in update via decay)
    return flash


# Track active explosion lights for fadeout
explosion_lights = []


def update_explosion_lights(dt):
    """Fade out explosion lights"""
    for light_data in explosion_lights[:]:
        light_data['time'] += dt
        # Fade intensity
        t = light_data['time'] / light_data['duration']
        if t >= 1:
            game_window.remove_light(light_data['light'])
            explosion_lights.remove(light_data)
        else:
            light_data['light'].intensity = light_data['initial_intensity'] * (1 - t)


def check_collisions():
    """Check bullet-enemy and player-enemy collisions"""
    # Bullet vs enemy
    for bullet in state.bullets[:]:
        bx, by = bullet['x'], int(bullet['y'])
        for enemy in state.enemies[:]:
            ex, ey = int(enemy['x']), int(enemy['y'])
            ew = enemy['width']
            # Simple AABB
            if ex <= bx < ex + ew and ey <= by < ey + 3:
                enemy['hp'] -= 1
                # Remove bullet
                game_window.remove_sprite(bullet['sprite'])
                game_window.remove_light(bullet['light'])
                state.bullets.remove(bullet)

                if enemy['hp'] <= 0:
                    # Destroy enemy
                    game_window.remove_sprite(enemy['sprite'])
                    state.enemies.remove(enemy)

                    # Explosion
                    size = enemy['type']
                    flash = spawn_explosion(ex + ew // 2, ey + 1, size)
                    explosion_lights.append({
                        'light': flash,
                        'time': 0,
                        'duration': 0.3,
                        'initial_intensity': flash.intensity
                    })

                    # Score
                    state.score += {'small': 10, 'medium': 25, 'large': 100}[enemy['type']]
                break

    # Enemy vs player
    px = int(state.player_x)
    py = PLAYER_Y
    for enemy in state.enemies[:]:
        ex, ey = int(enemy['x']), int(enemy['y'])
        ew = enemy['width']
        if ex <= px + 1 < ex + ew and ey <= py < ey + 3:
            state.player_health -= 1
            # Remove enemy
            game_window.remove_sprite(enemy['sprite'])
            state.enemies.remove(enemy)

            # Explosion at collision
            flash = spawn_explosion(px, py, 'medium')
            explosion_lights.append({
                'light': flash,
                'time': 0,
                'duration': 0.3,
                'initial_intensity': flash.intensity
            })

            if state.player_health <= 0:
                state.game_over = True


def handle_input(dt):
    """Handle held keys for continuous movement"""
    keys = pygame.key.get_pressed()

    # Movement
    if keys[pygame.K_LEFT]:
        state.player_x -= PLAYER_MOVE_SPEED * dt
        state.player_x = max(0, state.player_x)
        state.player_moving = -1
        player_sprite.move_to(int(state.player_x), PLAYER_Y)
    elif keys[pygame.K_RIGHT]:
        state.player_x += PLAYER_MOVE_SPEED * dt
        state.player_x = min(GAME_WIDTH - 2, state.player_x)
        state.player_moving = 1
        player_sprite.move_to(int(state.player_x), PLAYER_Y)

    # Shooting with held space
    if keys[pygame.K_SPACE] and state.fire_cooldown <= 0:
        fire_bullet()
        state.fire_cooldown = 0.15  # Fire rate limit


def update(dt):
    """Main update function"""
    if state.game_over:
        return

    # Always decrement fire cooldown
    state.fire_cooldown -= dt

    handle_input(dt)
    update_player_banking(dt)
    update_stars(dt)
    update_bullets(dt)
    update_enemies(dt)
    update_explosion_lights(dt)
    check_collisions()

    # Update emitter position to follow player
    player_emitter.move_to(state.player_x + 0.5, PLAYER_Y + 1)

    # Spawn enemies
    state.enemy_spawn_timer += dt
    if state.enemy_spawn_timer > 2.0:  # Every 2 seconds (slower spawn)
        state.enemy_spawn_timer = 0
        spawn_enemy()


def render():
    """Render HUD"""
    # Score
    hud_window.put_string(1, 1, f"SCORE: {state.score}", COLOR_HUD)

    # Health
    health_str = "♥ " * state.player_health + "♡ " * (3 - state.player_health)
    hud_window.put_string(1, 2, health_str, (255, 100, 100))

    if state.game_over:
        hud_window.put_string(GAME_WIDTH // 2 - 5, GAME_HEIGHT // 2, "GAME OVER", (255, 0, 0))
        hud_window.put_string(GAME_WIDTH // 2 - 8, GAME_HEIGHT // 2 + 1, f"Final Score: {state.score}", COLOR_HUD)


def on_key(key):
    """Handle single key presses (non-held actions)"""
    if state.game_over:
        if key == pygame.K_r:
            restart_game()
        return

    # Shooting triggers on key press
    if key == pygame.K_SPACE:
        fire_bullet()
        state.fire_cooldown = 0.15
    elif key == pygame.K_q:
        pyunicodegame.quit()


def restart_game():
    """Reset game state"""
    global state
    # Clear all entities
    for bullet in state.bullets:
        game_window.remove_sprite(bullet['sprite'])
        game_window.remove_light(bullet['light'])
    for enemy in state.enemies:
        game_window.remove_sprite(enemy['sprite'])

    state = GameState()
    player_sprite.move_to(state.player_x, PLAYER_Y)


def main():
    global game_window, hud_window, stars_far

    # Initialize with dark blue background
    root = pyunicodegame.init(
        "Unicode Tyrian",
        width=GAME_WIDTH,
        height=GAME_HEIGHT,
        bg=(10, 10, 25, 255)
    )

    # Create window layers
    # Stars background
    stars_far = pyunicodegame.create_window(
        "stars_far", 0, 0, GAME_WIDTH, GAME_HEIGHT,
        z_index=0, bg=(5, 5, 15, 255)
    )

    # Main game window
    game_window = pyunicodegame.create_window(
        "game", 0, 0, GAME_WIDTH, GAME_HEIGHT,
        z_index=5, bg=None
    )

    # Enable bloom on game window
    game_window.set_bloom(enabled=True, threshold=150, blur_scale=4, intensity=1.2)

    # Enable lighting
    game_window.set_lighting(enabled=True, ambient=(15, 15, 30))

    # HUD (fixed, no parallax)
    hud_window = pyunicodegame.create_window(
        "hud", 0, 0, GAME_WIDTH, GAME_HEIGHT,
        z_index=10, bg=None, fixed=True
    )

    # Initialize game elements
    init_stars()
    create_player()

    # Run game loop
    pyunicodegame.run(update=update, render=render, on_key=on_key)


if __name__ == "__main__":
    main()
