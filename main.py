import pygame
import sys
import os
import random
from player import movement

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

SKY_HEIGHT = 500
BLOCK_SIZE = 128

GRID_COLS = SCREEN_WIDTH // BLOCK_SIZE + 1
GRID_ROWS = 40

DEPTH_LAYERS = [
    (2,  [("grass", 100)]),
    (5,  [("soil", 90), ("stone", 10)]),
    (10, [("soil", 60), ("stone", 40)]),
    (15, [("stone", 70), ("copper", 30)]),
    (20, [("stone", 40), ("copper", 40), ("gold", 20)]),
    (25, [("stone", 20), ("copper", 20), ("gold", 40), ("diamond", 20)]),
    (999,[("stone", 10), ("gold", 20), ("diamond", 40), ("ruby", 30)]),
]

ORE_TYPES = ["grass", "soil", "stone", "copper", "gold", "diamond", "ruby"]

pygame.init()


def pick_block_type(row):
    for max_row, choices in DEPTH_LAYERS:
        if row < max_row:
            types = [c[0] for c in choices]
            weights = [c[1] for c in choices]
            return random.choices(types, weights=weights, k=1)[0]
    return "stone"


class Block:
    def __init__(self, x, y, block_type):
        self.x = x
        self.y = y
        self.block_type = block_type

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

        self.block_imgs = {}
        for ore in ORE_TYPES:
            path = os.path.join(assets_dir, f"dip_{ore}.png")
            if os.path.exists(path):
                raw = pygame.image.load(path).convert_alpha()
            else:
                raw = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE))
                fallback_colors = {
                    "grass": (34, 139, 34),
                    "soil": (139, 90, 43),
                    "stone": (128, 128, 128),
                    "copper": (184, 115, 51),
                    "gold": (255, 215, 0),
                    "diamond": (0, 255, 255),
                    "ruby": (155, 17, 30),
                }
                raw.fill(fallback_colors.get(ore, (200, 200, 200)))
            self.block_imgs[ore] = pygame.transform.scale(raw, (BLOCK_SIZE, BLOCK_SIZE))

        self.hud_icons = {}
        for ore in ORE_TYPES:
            if ore == "grass":
                continue
            self.hud_icons[ore] = pygame.transform.scale(self.block_imgs[ore], (32, 32))

        self.grid = []
        for row in range(GRID_ROWS):
            grid_row = []
            for col in range(GRID_COLS):
                x = col * BLOCK_SIZE
                y = SKY_HEIGHT + row * BLOCK_SIZE
                block_type = "grass" if row == 0 else pick_block_type(row)
                grid_row.append(Block(x, y, block_type))
            self.grid.append(grid_row)

        self.inventory = {ore: 0 for ore in ORE_TYPES if ore != "grass"}
        self.font = pygame.font.SysFont(None, 28)

    def get_block_at(self, world_x, world_y):
        col = world_x // BLOCK_SIZE
        row = (world_y - SKY_HEIGHT) // BLOCK_SIZE
        if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
            return self.grid[row][col]
        return None

    def resolve_collision(self, player_pos, vertical_velocity, on_ground):
        """Check if the player is standing on a solid block and snap them to it."""
        PLAYER_WIDTH = 60
        PLAYER_HEIGHT = 100

        feet_y = player_pos.y + PLAYER_HEIGHT
        left_x = player_pos.x + 2
        right_x = player_pos.x + PLAYER_WIDTH

        on_ground = False

        # Check the block directly under the left and right foot
        for check_x in [left_x, right_x]:
            col = int(check_x) // BLOCK_SIZE
            # Find the topmost solid block at or below the player's feet
            row = int(feet_y) // BLOCK_SIZE - SKY_HEIGHT // BLOCK_SIZE
            # Convert feet world Y to grid row
            grid_row = (int(feet_y) - SKY_HEIGHT) // BLOCK_SIZE

            if 0 <= grid_row < GRID_ROWS and 0 <= col < GRID_COLS:
                block = self.grid[grid_row][col]
                if block.block_type != "air":
                    block_top = block.y  # world Y of the top of this block
                    # If player's feet are at or past this block's top, snap up
                    if feet_y >= block_top and feet_y <= block_top + BLOCK_SIZE:
                        player_pos.y = block_top - PLAYER_HEIGHT
                        vertical_velocity = 0
                        on_ground = True

        return player_pos, vertical_velocity, on_ground

    def draw_background(self, camera_y):
        self.screen.blit(self.background_sky, (0, -camera_y))
        for row in self.grid:
            for block in row:
                if block.block_type != "air":
                    img = self.block_imgs.get(block.block_type)
                    if img:
                        self.screen.blit(img, (block.x, block.y - camera_y))

    def draw_hud(self):
        panel_x = 10
        panel_y = SCREEN_HEIGHT - 50
        icon_size = 32
        padding = 8

        panel_width = len(self.inventory) * (icon_size + padding + 40) + padding
        panel_surf = pygame.Surface((panel_width, 48), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 140))
        self.screen.blit(panel_surf, (panel_x - padding, panel_y - 8))

        x = panel_x
        for ore in ["soil", "stone", "copper", "gold", "diamond", "ruby"]:
            icon = self.hud_icons[ore]
            self.screen.blit(icon, (x, panel_y))
            count_surf = self.font.render(str(self.inventory[ore]), True, (255, 255, 255))
            self.screen.blit(count_surf, (x + icon_size + 4, panel_y + 8))
            x += icon_size + 4 + count_surf.get_width() + padding + 4

    def main(self):
        player_pos = pygame.math.Vector2(400, SKY_HEIGHT - 100)
        speed = 300
        vertical_velocity = 0
        on_ground = False
        # ground_y is only a hard floor safety net at the very bottom
        ground_y = SKY_HEIGHT + GRID_ROWS * BLOCK_SIZE - 100
        hovered_block = None

        while True:
            dt = self.clock.tick(60) / 1000

            player_pos, vertical_velocity, on_ground, hovered_block = movement(
                player_pos, vertical_velocity, on_ground, speed, dt, ground_y, self.player
            )

            # Grid-based collision replaces the fixed ground_y check
            player_pos, vertical_velocity, on_ground = self.resolve_collision(
                player_pos, vertical_velocity, on_ground
            )

            camera_y = int(player_pos.y - SCREEN_HEIGHT // 2)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_e and hovered_block:
                        bx, by = hovered_block
                        block = self.get_block_at(bx, by)
                        if block and block.block_type != "air":
                            mined = block.block_type
                            block.block_type = "air"
                            if mined in self.inventory:
                                self.inventory[mined] += 1

            self.draw_background(camera_y)

            if hovered_block:
                bx, by = hovered_block
                block = self.get_block_at(bx, by)
                if block and block.block_type != "air":
                    pygame.draw.rect(self.screen, (255, 255, 0), (bx, by - camera_y, BLOCK_SIZE, BLOCK_SIZE), 3)

            self.screen.blit(self.player, (int(player_pos.x), int(player_pos.y) - camera_y))
            self.draw_hud()
            pygame.display.flip()


if __name__ == "__main__":
    game = digging()
    game.main()