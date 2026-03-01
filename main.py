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

PLAYER_WIDTH = 64
PLAYER_HEIGHT = 100

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
        self.player_img = pygame.transform.scale(raw_player, (PLAYER_WIDTH, PLAYER_HEIGHT))

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

    def get_block_at_world(self, world_x, world_y):
        col = int(world_x) // BLOCK_SIZE
        row = (int(world_y) - SKY_HEIGHT) // BLOCK_SIZE
        if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
            return self.grid[row][col]
        return None

    def find_ground_y(self, player_x):
        """Scan downward under both feet and return the Y the player should stand at."""
        best_ground = SKY_HEIGHT + GRID_ROWS * BLOCK_SIZE

        for foot_x in [player_x + 4, player_x + PLAYER_WIDTH - 4]:
            col = int(foot_x) // BLOCK_SIZE
            if not (0 <= col < GRID_COLS):
                continue
            for row in range(GRID_ROWS):
                block = self.grid[row][col]
                if block.block_type != "air":
                    candidate = block.y - PLAYER_HEIGHT
                    if candidate < best_ground:
                        best_ground = candidate
                    break

        return best_ground

    def snap_player_to_ground(self, player_pos, vertical_velocity, on_ground):
        """Prevent player falling through solid blocks."""
        feet_y = player_pos.y + PLAYER_HEIGHT

        for foot_x in [player_pos.x + 4, player_pos.x + PLAYER_WIDTH - 4]:
            col = int(foot_x) // BLOCK_SIZE
            if not (0 <= col < GRID_COLS):
                continue
            row = (int(feet_y) - SKY_HEIGHT) // BLOCK_SIZE
            if 0 <= row < GRID_ROWS:
                block = self.grid[row][col]
                if block.block_type != "air" and vertical_velocity >= 0:
                    player_pos.y = block.y - PLAYER_HEIGHT
                    vertical_velocity = 0
                    on_ground = True

        return player_pos, vertical_velocity, on_ground

    def mine_block(self, hovered_block, player_pos, vertical_velocity, on_ground):
        bx, by = hovered_block
        block = self.get_block_at_world(bx, by)
        if not block or block.block_type == "air":
            return vertical_velocity, on_ground

        mined = block.block_type
        block.block_type = "air"
        if mined in self.inventory:
            self.inventory[mined] += 1

        # Instantly snap player to where they should now be standing
        new_ground = self.find_ground_y(player_pos.x)
        player_pos.y = new_ground
        vertical_velocity = 0
        on_ground = True

        return vertical_velocity, on_ground

    def draw_world(self, camera_y):
        self.screen.fill((20, 12, 8))  # dark background - prevents any trail
        self.screen.blit(self.background_sky, (0, -camera_y))

        for row in self.grid:
            for block in row:
                if block.block_type != "air":
                    img = self.block_imgs.get(block.block_type)
                    if img:
                        screen_y = block.y - camera_y
                        if -BLOCK_SIZE < screen_y < SCREEN_HEIGHT + BLOCK_SIZE:
                            self.screen.blit(img, (block.x, screen_y))

    def draw_hud(self):
        panel_x = 10
        panel_y = SCREEN_HEIGHT - 50
        icon_size = 32
        padding = 8

        panel_width = 6 * (icon_size + padding + 40) + padding
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
        player_pos = pygame.math.Vector2(400, SKY_HEIGHT - PLAYER_HEIGHT)
        speed = 300
        vertical_velocity = 0
        on_ground = False
        ground_y = SKY_HEIGHT + GRID_ROWS * BLOCK_SIZE
        hovered_block = None

        while True:
            dt = self.clock.tick(60) / 1000

            player_pos, vertical_velocity, on_ground, hovered_block = movement(
                player_pos, vertical_velocity, on_ground, speed, dt, ground_y, self.player_img
            )

            player_pos, vertical_velocity, on_ground = self.snap_player_to_ground(
                player_pos, vertical_velocity, on_ground
            )

            camera_y = int(player_pos.y - SCREEN_HEIGHT // 2)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_e and hovered_block:
                        vertical_velocity, on_ground = self.mine_block(
                            hovered_block, player_pos, vertical_velocity, on_ground
                        )

            self.draw_world(camera_y)

            if hovered_block:
                bx, by = hovered_block
                block = self.get_block_at_world(bx, by)
                if block and block.block_type != "air":
                    pygame.draw.rect(
                        self.screen, (255, 255, 0),
                        (bx, by - camera_y, BLOCK_SIZE, BLOCK_SIZE), 3
                    )

            self.screen.blit(self.player_img, (int(player_pos.x), int(player_pos.y) - camera_y))
            self.draw_hud()
            pygame.display.flip()


if __name__ == "__main__":
    game = digging()
    game.main()