import pygame
import sys
import os
from player import movement

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

SKY_HEIGHT = 500
BLOCK_SIZE = 128

# Grid dimensions
GRID_COLS = SCREEN_WIDTH // BLOCK_SIZE + 1
GRID_ROWS = 10  # how many rows of underground blocks you want

pygame.init()


class Block:
    def __init__(self, x, y, block_type):
        self.x = x
        self.y = y
        self.block_type = block_type  # "grass" or "soil"
        self.alive = True

    def get_pos(self):
        return (self.x, self.y)


class digging:

    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Diggers In Paris")
        self.clock = pygame.time.Clock()
        assets_dir = os.path.join(os.path.dirname(__file__), "assets", "images")

        raw_player = pygame.image.load(os.path.join(assets_dir, "player.jpg")).convert_alpha()
        self.player = pygame.transform.scale(raw_player, (64, 100))

        raw_sky = pygame.image.load(os.path.join(assets_dir, "dip_background.png")).convert()
        self.background_sky = pygame.transform.scale(raw_sky, (SCREEN_WIDTH, SKY_HEIGHT))

        raw_grass = pygame.image.load(os.path.join(assets_dir, "dip_grass.png")).convert_alpha()
        self.grass_img = pygame.transform.scale(raw_grass, (BLOCK_SIZE, BLOCK_SIZE))

        raw_soil = pygame.image.load(os.path.join(assets_dir, "dip_soil.png")).convert()
        self.soil_img = pygame.transform.scale(raw_soil, (BLOCK_SIZE, BLOCK_SIZE))

        # Build the grid: row 0 = grass, rows 1+ = soil
        self.grid = []
        for row in range(GRID_ROWS):
            grid_row = []
            for col in range(GRID_COLS):
                x = col * BLOCK_SIZE
                y = SKY_HEIGHT + row * BLOCK_SIZE
                block_type = "grass" if row == 0 else "soil"
                grid_row.append(Block(x, y, block_type))
            self.grid.append(grid_row)

    def draw_background(self, camera_y):
        self.screen.blit(self.background_sky, (0, -camera_y))

        for row in self.grid:
            for block in row:
                if block.block_type != "air":
                    img = self.grass_img if block.block_type == "grass" else self.soil_img
                    self.screen.blit(img, (block.x, block.y - camera_y))

    def get_block_at(self, world_x, world_y):
        """Return the block at a given world position, or None."""
        col = world_x // BLOCK_SIZE
        row = (world_y - SKY_HEIGHT) // BLOCK_SIZE
        if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
            return self.grid[row][col]
        return None

    def main(self):
        player_pos = pygame.math.Vector2(400, SKY_HEIGHT - 100)
        speed = 300
        vertical_velocity = 0
        on_ground = False
        ground_y = SKY_HEIGHT - 100
        hovered_block = None  # define it here first

        while True:
            dt = self.clock.tick(60) / 1000

            player_pos, vertical_velocity, on_ground, hovered_block = movement(
                player_pos, vertical_velocity, on_ground, speed, dt, ground_y, self.player
            )

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_e:
                            print(f"E pressed! hovered_block={hovered_block}")
                            if hovered_block:
                                bx, by = hovered_block
                                block = self.get_block_at(bx, by)
                                print(f"block found: {block.block_type if block else None}")
                                if block and block.block_type != "air":
                                    block.block_type = "air"
                                    print(f"after delete: {block.block_type}")
                                    # also check the grid directly
                                    bx2, by2 = hovered_block
                                    b2 = self.get_block_at(bx2, by2)
                                    print(f"grid check: {b2.block_type if b2 else None}") 

            camera_y = int(player_pos.y - SCREEN_HEIGHT // 2)
            self.draw_background(camera_y)

            if hovered_block:
                bx, by = hovered_block
                block = self.get_block_at(bx, by)
                if block and block.block_type != "air":
                    pygame.draw.rect(self.screen, (255, 255, 0), (bx, by - camera_y, BLOCK_SIZE, BLOCK_SIZE), 3)
            self.screen.blit(self.player, (int(player_pos.x), int(player_pos.y) - camera_y))
            pygame.display.flip()


if __name__ == "__main__":
    game = digging()
    game.main()