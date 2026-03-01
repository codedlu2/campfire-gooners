import pygame

GRAVITY = 1200
JUMP_FORCE = -400
BLOCK_SIZE = 128
SKY_HEIGHT = 500

def movement(player_pos, vertical_velocity, on_ground, speed, dt, ground_y, image, max_x=1280-64, min_x=0):
    velocity = pygame.math.Vector2(0, 0)

    keys = pygame.key.get_pressed()
    if keys[pygame.K_a] and player_pos.x > min_x:
        velocity.x -= 1

    if keys[pygame.K_d] and player_pos.x < max_x:
        velocity.x += 1

    if (keys[pygame.K_w] or keys[pygame.K_SPACE]) and on_ground:
        vertical_velocity = JUMP_FORCE
        on_ground = False

    # Player's center column
    player_center_x = int(player_pos.x) + 32
    player_col = player_center_x // BLOCK_SIZE

    # Row the player's body is in
    player_body_row = (int(player_pos.y) - SKY_HEIGHT) // BLOCK_SIZE
    # Row at player's feet
    player_feet_y = int(player_pos.y) + 100
    player_feet_row = (player_feet_y - SKY_HEIGHT) // BLOCK_SIZE

    hovered_block = None
    if keys[pygame.K_RIGHT]:
        hovered_block = ((player_col + 1) * BLOCK_SIZE, player_body_row * BLOCK_SIZE + SKY_HEIGHT)
    elif keys[pygame.K_LEFT]:
        hovered_block = ((player_col - 1) * BLOCK_SIZE, player_body_row * BLOCK_SIZE + SKY_HEIGHT)
    elif keys[pygame.K_DOWN]:
        hovered_block = (player_col * BLOCK_SIZE, player_feet_row * BLOCK_SIZE + SKY_HEIGHT)
    elif keys[pygame.K_UP]:
        hovered_block = (player_col * BLOCK_SIZE, player_body_row * BLOCK_SIZE + SKY_HEIGHT)

    # Apply gravity
    vertical_velocity += GRAVITY * dt
    player_pos.y += vertical_velocity * dt

    # Ground collision (handled by main now, but keep fallback)
    if player_pos.y >= ground_y:
        player_pos.y = ground_y
        vertical_velocity = 0
        on_ground = True

    if velocity.length() > 0:
        velocity = velocity.normalize()

    player_pos += velocity * speed * dt
    return player_pos, vertical_velocity, on_ground, hovered_block