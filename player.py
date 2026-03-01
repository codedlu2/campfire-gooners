import pygame

# constants are passed into movement() now; no globals here

def movement(player_pos, vertical_velocity, on_ground, speed, dt, ground_y, image,
             facing,
             gravity=1200, jump_force=-600,
             block_size=128, sky_height=500,
             max_x=1280-64, min_x=0):

    velocity = pygame.math.Vector2(0, 0)

    keys = pygame.key.get_pressed()
    if keys[pygame.K_a] and player_pos.x > min_x:
        velocity.x -= 1
        facing = -1
    if keys[pygame.K_d] and player_pos.x < max_x:
        velocity.x += 1
        facing = 1
    if (keys[pygame.K_w] or keys[pygame.K_SPACE]) and on_ground:
        vertical_velocity = jump_force
        on_ground = False

    # Player's center column
    player_center_x = int(player_pos.x) + 32
    player_col = player_center_x // block_size

    # Row at player's body (torso)
    player_body_row = max(0, (int(player_pos.y) - sky_height) // block_size)
    # Row at player's feet
    player_feet_y   = int(player_pos.y) + 100
    player_feet_row = max(0, (player_feet_y - sky_height) // block_size)

    hovered_block = None
    if keys[pygame.K_RIGHT]:
        hovered_block = ((player_col + 1) * block_size, player_body_row * block_size + sky_height)
    elif keys[pygame.K_LEFT]:
        hovered_block = ((player_col - 1) * block_size, player_body_row * block_size + sky_height)
    elif keys[pygame.K_DOWN]:
        hovered_block = (player_col * block_size, player_feet_row * block_size + sky_height)
    elif keys[pygame.K_UP]:
        hovered_block = (player_col * block_size, player_body_row * block_size + sky_height)

    # Gravity only — no ground collision here, main.py handles it
    vertical_velocity += gravity * dt
    player_pos.y += vertical_velocity * dt

    if velocity.length() > 0:
        velocity = velocity.normalize()

    player_pos += velocity * speed * dt

    if player_pos.x < min_x:
        player_pos.x = float(min_x)
    if player_pos.x > max_x:
        player_pos.x = float(max_x)

    # Return a flipped copy of the image based on current facing direction
    # The source image is assumed to face RIGHT by default
    if facing == -1:
        flipped_image = pygame.transform.flip(image, True, False)
    else:
        flipped_image = image

    return player_pos, vertical_velocity, on_ground, hovered_block, facing, flipped_image