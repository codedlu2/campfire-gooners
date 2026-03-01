import pygame

GRAVITY = 1200
JUMP_FORCE = -400
BLOCK_SIZE = 128
SKY_HEIGHT = 500

def movement(player_pos, vertical_velocity, on_ground, speed, dt, ground_y, image, max_x=1280-64, min_x=0):
    velocity = pygame.math.Vector2(0, 0)

    image_flipped = pygame.transform.flip(image, True, False)
    facing_right = 1

    keys = pygame.key.get_pressed()
    if keys[pygame.K_a] and player_pos.x > min_x:
        velocity.x -= 1
        if facing_right == 1:
            facing_right *= -1

    if keys[pygame.K_d] and player_pos.x < max_x:
        velocity.x += 1
        if facing_right == -1:
            facing_right *= -1

    if (keys[pygame.K_w] or keys[pygame.K_SPACE]) and on_ground:
        vertical_velocity = JUMP_FORCE
        on_ground = False

    # Player's block column (snapped to grid)
    player_col = int(player_pos.x) // BLOCK_SIZE
    # Player's feet in world space, snapped to the block row they're standing in
    player_feet_y = int(player_pos.y) + 100  # 100 = player height
    player_row_y = (player_feet_y // BLOCK_SIZE) * BLOCK_SIZE

    hovered_block = None
    if keys[pygame.K_RIGHT]:
        hovered_block = ((player_col + 1) * BLOCK_SIZE-12, player_row_y)
    if keys[pygame.K_LEFT]:
        hovered_block = ((player_col - 1) * BLOCK_SIZE-12, player_row_y)
    if keys[pygame.K_DOWN]:
        hovered_block = (player_col * BLOCK_SIZE-12, player_row_y + BLOCK_SIZE)

    # Apply gravity
    vertical_velocity += GRAVITY * dt
    player_pos.y += vertical_velocity * dt

    # Ground collision
    if player_pos.y >= ground_y:
        player_pos.y = ground_y
        vertical_velocity = 0
        on_ground = True

    if velocity.length() > 0:
        velocity = velocity.normalize()

    player_pos += velocity * speed * dt
    return player_pos, vertical_velocity, on_ground, hovered_block