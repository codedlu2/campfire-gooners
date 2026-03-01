import pygame

GRAVITY = 1200
JUMP_FORCE = -400

def movement(player_pos, vertical_velocity, on_ground, speed, dt, ground_y, image, max_x=1280-64, min_x=0):
    velocity = pygame.math.Vector2(0, 0)
    
    image_flipped = pygame.transform.flip(image, True, False)

    facing_right = 1
    if facing_right == 1:
        image = image
    else:
        image = image_flipped

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
    
    hovered_block = None
    if keys[pygame.K_RIGHT]:
        block_posx = (int(player_pos.x) // 128 + 1) * 128
        block_posy = (int(player_pos.y) // 128) * 128 - 12
        hovered_block = (block_posx, block_posy)
    if keys[pygame.K_LEFT]:
        block_posx = (int(player_pos.x) // 128 - 1) * 128
        block_posy = (int(player_pos.y) // 128) * 128 - 12
        hovered_block = (block_posx, block_posy)
    if keys[pygame.K_DOWN]:
        block_posx = (int(player_pos.x) // 128) * 128
        block_posy = (int(player_pos.y) // 128 + 1) * 128 - 12
        hovered_block = (block_posx, block_posy)

    # apply gravity
    vertical_velocity += GRAVITY * dt
    player_pos.y += vertical_velocity * dt

    # ground collision
    if player_pos.y >= ground_y:
        player_pos.y = ground_y
        vertical_velocity = 0
        on_ground = True

    if velocity.length() > 0:
        velocity = velocity.normalize()

    player_pos += velocity * speed * dt
    return player_pos, vertical_velocity, on_ground, hovered_block