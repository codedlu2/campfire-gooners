import asyncio
import pygame
import sys
import os
import random
from player import movement

SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 720
SKY_HEIGHT    = 500
BLOCK_SIZE    = 128

GRID_COLS = SCREEN_WIDTH // BLOCK_SIZE + 1
GRID_ROWS = 40

PLAYER_WIDTH  = 85
PLAYER_HEIGHT = 100

# values used by the movement helper (formerly defined in player.py)
GRAVITY = 1200
JUMP_FORCE = -600

WORLD_LEFT  = 0
WORLD_RIGHT = SCREEN_WIDTH - PLAYER_WIDTH

SHOP_TRIGGER_X = WORLD_RIGHT - 2

ORE_PRICES = {
    "soil": 1, "stone": 2, "copper": 5,
    "gold": 15, "diamond": 40, "ruby": 80,
}

ORE_HARDNESS = {
    "grass": 1, "soil": 1, "stone": 3,
    "copper": 5, "gold": 7, "diamond": 12, "ruby": 18,
}

FOSSIL_PIECES = [
    "headblock2", "armblock2_a", "armblock2_b",
    "legblock2_a", "legblock2_b", "tailblock", "ribblock2",
]
FOSSIL_ASSET = {
    "headblock2":  "dip_headblock2",
    "armblock2_a": "dip_armblock2",
    "armblock2_b": "dip_armblock2",
    "legblock2_a": "dip_legblcok2",
    "legblock2_b": "dip_legblcok2",
    "tailblock":   "dip_tailblock",
    "ribblock2":   "dip_ribblock2",
}

BLOCK_HP = {
    "grass":   2,
    "soil":    3,
    "stone":   6,
    "copper":  10,
    "gold":    16,
    "diamond": 26,
    "ruby":    40,
}
for _fp in FOSSIL_PIECES:
    BLOCK_HP[_fp] = 16

DEPTH_LAYERS = [
    (1,   [("grass",  100)]),
    (5,   [("soil",    90), ("stone",   10)]),
    (10,  [("soil",    60), ("stone",   40)]),
    (15,  [("stone",   70), ("copper",  30)]),
    (20,  [("stone",   40), ("copper",  40), ("gold",    20)]),
    (25,  [("stone",   20), ("copper",  20), ("gold",    40), ("diamond", 20)]),
    (999, [("stone",   10), ("gold",    20), ("diamond", 40), ("ruby",    30)]),
]

ORE_TYPES = ["grass", "soil", "stone", "copper", "gold", "diamond", "ruby"]

TOOL_DEFS = {
    "fists": {
        "label": "Fists", "base_durability": 999999, "damage": 1,
        "fortune_mult": 1.0, "mine_radius": 0, "price": 0,
        "description": "Your bare hands. Slow but free.",
    },
    "pickaxe": {
        "label": "Pickaxe", "base_durability": 30, "damage": 2,
        "fortune_mult": 1.0, "mine_radius": 0, "price": 40,
        "description": "Mines faster. Can be upgraded.",
    },
    "dynamite": {
        "label": "Dynamite", "base_durability": 1, "damage": 999,
        "fortune_mult": 1.0, "mine_radius": 1, "price": 25,
        "description": "One-use. Destroys 3x3 area.",
    },
    "radar": {
        "label": "Radar", "base_durability": 999999, "damage": 1,
        "fortune_mult": 1.0, "mine_radius": 0, "price": 80,
        "description": "Reveals blocks around you. (placeholder)",
    },
    "drill": {
        "label": "Drill", "base_durability": 50, "damage": 4,
        "fortune_mult": 1.5, "mine_radius": 0, "price": 150,
        "description": "High damage, mines more, faster.",
    },
}

PICKAXE_UPGRADES = {
    "fortune": {
        "label": "Fortune",
        "description": "Boosts blocks collected per mine",
        "costs":   [30, 70, 140],
        "effects": [1.5, 2.0, 3.0],
    },
    "efficiency": {
        "label": "Efficiency",
        "description": "Increases mine speed (damage per hit)",
        "costs":   [25, 60, 120],
        "effects": [3, 4, 6],
    },
    "unbreaking": {
        "label": "Unbreaking",
        "description": "Reduces durability lost per block mined",
        "costs":   [20, 50, 100],
        "effects": [3, 2, 1],
    },
}

pygame.init()


def pick_block_type(row):
    for max_row, choices in DEPTH_LAYERS:
        if row < max_row:
            return random.choices(
                [c[0] for c in choices],
                weights=[c[1] for c in choices], k=1)[0]
    return "stone"


def draw_rounded_rect(surface, color, rect, radius=10,
                      border_color=None, border_width=2):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border_color:
        pygame.draw.rect(surface, border_color, rect, border_width,
                         border_radius=radius)


class Block:
    def __init__(self, x, y, block_type):
        self.x, self.y = x, y
        self.block_type = block_type
        self.max_hp = BLOCK_HP.get(block_type, 1)
        self.hp     = self.max_hp


class digging:

    def __init__(self):
        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
        # track facing direction instead of relying on a module global
        self.facing = 1  # 1=right, -1=left
        pygame.display.set_caption("Digging In Paris")
        self.clock = pygame.time.Clock()
        assets_dir = os.path.join(os.path.dirname(__file__), "assets", "images")

        # Default player skin
        raw = pygame.image.load(
            os.path.join(assets_dir, "dip_playerv2.png")).convert_alpha()
        self.player_img_default = pygame.transform.scale(raw, (PLAYER_WIDTH, PLAYER_HEIGHT))

        # Santa skin
        santa_path = os.path.join(assets_dir, "dip_player_santa.png")
        if os.path.exists(santa_path):
            raw = pygame.image.load(santa_path).convert_alpha()
            self.player_img_santa = pygame.transform.smoothscale(raw, (PLAYER_WIDTH, PLAYER_HEIGHT))
        else:
            self.player_img_santa = None

        self.player_img    = self.player_img_default
        self.owned_skins   = set()
        self.equipped_skin = None

        raw = pygame.image.load(
            os.path.join(assets_dir, "dip_background.png")).convert()
        self.background_sky = pygame.transform.scale(raw, (SCREEN_WIDTH, SKY_HEIGHT))
        self.sky_extend_color = self.background_sky.get_at((SCREEN_WIDTH // 2, 4))[:3]

        fallback_colors = {
            "grass": (34,139,34), "soil": (139,90,43), "stone": (128,128,128),
            "copper": (184,115,51), "gold": (255,215,0),
            "diamond": (0,255,255), "ruby": (155,17,30),
        }
        self.block_imgs  = {}
        self.hud_icons   = {}
        self.shop_icons  = {}
        for ore in ORE_TYPES:
            path = os.path.join(assets_dir, f"dip_{ore}.png")
            if os.path.exists(path):
                raw = pygame.image.load(path).convert_alpha()
            else:
                raw = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE))
                raw.fill(fallback_colors.get(ore, (200,200,200)))
            self.block_imgs[ore]  = pygame.transform.scale(raw, (BLOCK_SIZE, BLOCK_SIZE))
            if ore != "grass":
                self.hud_icons[ore]  = pygame.transform.scale(raw, (32, 32))
                self.shop_icons[ore] = pygame.transform.scale(raw, (48, 48))

        tool_fallbacks = {
            "pickaxe": (160,100,40), "dynamite": (220,60,60),
            "radar":   (60,160,220), "drill":    (80,80,200),
        }
        self.tool_imgs = {}
        for tool in ["pickaxe","dynamite","radar","drill"]:
            path = os.path.join(assets_dir, f"dip_{tool}.png")
            if os.path.exists(path):
                raw = pygame.image.load(path).convert_alpha()
            else:
                raw = pygame.Surface((48, 48), pygame.SRCALPHA)
                raw.fill(tool_fallbacks[tool])
            self.tool_imgs[tool] = pygame.transform.scale(raw, (48, 48))

        # Fossil block images
        self.fossil_imgs = {}
        for fp in FOSSIL_PIECES:
            stem = FOSSIL_ASSET[fp]
            path = os.path.join(assets_dir, f"{stem}.png")
            if os.path.exists(path):
                raw = pygame.image.load(path).convert_alpha()
            else:
                raw = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE))
                raw.fill((180, 170, 150))
            self.fossil_imgs[fp] = pygame.transform.scale(raw, (BLOCK_SIZE, BLOCK_SIZE))
            self.block_imgs[fp]  = self.fossil_imgs[fp]

        # Full fossil completion image
        full_path = os.path.join(assets_dir, "dip_fullfossil.png")
        if os.path.exists(full_path):
            raw = pygame.image.load(full_path).convert_alpha()
            fw, fh = raw.get_size()
            scale = min((SCREEN_WIDTH - 200) / fw, (SCREEN_HEIGHT - 200) / fh)
            self.fullfossil_img = pygame.transform.scale(
                raw, (int(fw * scale), int(fh * scale)))
        else:
            self.fullfossil_img = None

        self.grid = []
        for r in range(GRID_ROWS):
            row_list = []
            for c in range(GRID_COLS):
                bt = "grass" if r == 0 else pick_block_type(r)
                row_list.append(Block(c * BLOCK_SIZE,
                                      SKY_HEIGHT + r * BLOCK_SIZE, bt))
            self.grid.append(row_list)

        self.fossil_collected = {fp: False for fp in FOSSIL_PIECES}
        all_cells = [(r, c) for r in range(3, GRID_ROWS) for c in range(GRID_COLS)]
        chosen = random.sample(all_cells, len(FOSSIL_PIECES))
        for fp, (r, c) in zip(FOSSIL_PIECES, chosen):
            self.grid[r][c].block_type = fp
            self.grid[r][c].max_hp = BLOCK_HP[fp]
            self.grid[r][c].hp     = BLOCK_HP[fp]

        self.inventory = {ore: 0 for ore in ORE_TYPES if ore != "grass"}
        self.coins     = 10000

        self.active_tool      = "fists"
        self.owned_tools: dict[str, int] = {"fists": 999999}
        self.dynamite_count   = 0
        self.pickaxe_upgrades = {k: 0 for k in PICKAXE_UPGRADES}
        self.fossil_complete  = False

        self.font       = pygame.font.SysFont(None, 26)
        self.font_med   = pygame.font.SysFont(None, 32)
        self.font_large = pygame.font.SysFont(None, 42)
        self.font_title = pygame.font.SysFont(None, 72)

        self.state    = "game"
        self.shop_tab = "sell"

        self._flash_msg = ""
        self._flash_ttl = 0.0

    def _flash(self, msg, duration=1.4):
        self._flash_msg = msg
        self._flash_ttl = duration

    def _effective_tool(self):
        td = dict(TOOL_DEFS[self.active_tool])
        td["unbreaking_cost"] = 4
        if self.active_tool == "pickaxe":
            upgs = self.pickaxe_upgrades
            lv = upgs["fortune"]
            if lv > 0:
                td["fortune_mult"] = PICKAXE_UPGRADES["fortune"]["effects"][lv - 1]
            lv = upgs["efficiency"]
            if lv > 0:
                td["damage"] = PICKAXE_UPGRADES["efficiency"]["effects"][lv - 1]
            lv = upgs["unbreaking"]
            if lv > 0:
                td["unbreaking_cost"] = PICKAXE_UPGRADES["unbreaking"]["effects"][lv - 1]
        return td

    def _damage_tool(self, block_type):
        if self.active_tool == "fists":
            return
        if self.active_tool == "pickaxe":
            td = self._effective_tool()
            cost = td["unbreaking_cost"]
        else:
            cost = ORE_HARDNESS.get(block_type, 1)
        self.owned_tools[self.active_tool] = max(
            0, self.owned_tools[self.active_tool] - cost)
        if self.owned_tools[self.active_tool] <= 0:
            self._flash(f"{TOOL_DEFS[self.active_tool]['label']} broke!", 2.0)
            del self.owned_tools[self.active_tool]
            if self.active_tool == "dynamite":
                self.dynamite_count = max(0, self.dynamite_count - 1)
            self.active_tool = "fists"

    def get_block_at_world(self, wx, wy):
        col = int(wx) // BLOCK_SIZE
        row = (int(wy) - SKY_HEIGHT) // BLOCK_SIZE
        if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
            return self.grid[row][col]
        return None

    def find_ground_y(self, player_x):
        best = SKY_HEIGHT + GRID_ROWS * BLOCK_SIZE
        for fx in [player_x + 4, player_x + PLAYER_WIDTH - 4]:
            col = int(fx) // BLOCK_SIZE
            if not (0 <= col < GRID_COLS):
                continue
            for r in range(GRID_ROWS):
                b = self.grid[r][col]
                if b.block_type != "air":
                    cand = b.y - PLAYER_HEIGHT
                    if cand < best:
                        best = cand
                    break
        return best

    COLL_INSET_X   = 18
    COLL_INSET_TOP =  6

    def _col_left(self, p):
        return p.x + self.COLL_INSET_X

    def _col_right(self, p):
        return p.x + PLAYER_WIDTH - self.COLL_INSET_X

    def snap_player_to_ground(self, player_pos, vvel, on_ground):
        feet_y = player_pos.y + PLAYER_HEIGHT
        sample_xs = [
            self._col_left(player_pos)  + 2,
            player_pos.x + PLAYER_WIDTH // 2,
            self._col_right(player_pos) - 2,
        ]
        for fx in sample_xs:
            col = int(fx) // BLOCK_SIZE
            if not (0 <= col < GRID_COLS):
                continue
            row = (int(feet_y) - SKY_HEIGHT) // BLOCK_SIZE
            if not (0 <= row < GRID_ROWS):
                continue
            b = self.grid[row][col]
            if b.block_type != "air" and vvel >= 0 and feet_y >= b.y:
                player_pos.y = b.y - PLAYER_HEIGHT
                vvel = 0
                on_ground = True
                break
        return player_pos, vvel, on_ground

    def snap_player_to_ceiling(self, player_pos, vvel):
        head_y = player_pos.y + self.COLL_INSET_TOP
        sample_xs = [
            self._col_left(player_pos)  + 2,
            player_pos.x + PLAYER_WIDTH // 2,
            self._col_right(player_pos) - 2,
        ]
        for fx in sample_xs:
            col = int(fx) // BLOCK_SIZE
            if not (0 <= col < GRID_COLS):
                continue
            row = (int(head_y) - SKY_HEIGHT) // BLOCK_SIZE
            if not (0 <= row < GRID_ROWS):
                continue
            b = self.grid[row][col]
            if b.block_type != "air" and head_y < b.y + BLOCK_SIZE:
                player_pos.y = b.y + BLOCK_SIZE - self.COLL_INSET_TOP
                vvel = 0
                break
        return player_pos, vvel

    def resolve_horizontal_block_collision(self, player_pos):
        check_ys = [
            player_pos.y + PLAYER_HEIGHT * 0.30,
            player_pos.y + PLAYER_HEIGHT * 0.70,
        ]
        for cy in check_ys:
            row = (int(cy) - SKY_HEIGHT) // BLOCK_SIZE
            if not (0 <= row < GRID_ROWS):
                continue
            right_edge = self._col_right(player_pos)
            right_col  = int(right_edge) // BLOCK_SIZE
            if 0 <= right_col < GRID_COLS:
                b = self.grid[row][right_col]
                if b.block_type != "air" and right_edge > b.x:
                    player_pos.x = float(b.x - PLAYER_WIDTH + self.COLL_INSET_X)
            left_edge = self._col_left(player_pos)
            left_col  = int(left_edge) // BLOCK_SIZE
            if 0 <= left_col < GRID_COLS:
                b = self.grid[row][left_col]
                if b.block_type != "air" and left_edge < b.x + BLOCK_SIZE:
                    player_pos.x = float(b.x + BLOCK_SIZE - self.COLL_INSET_X)
        return player_pos

    def clamp_to_walls(self, player_pos):
        if player_pos.x < WORLD_LEFT:
            player_pos.x = float(WORLD_LEFT)
        if player_pos.x > WORLD_RIGHT:
            player_pos.x = float(WORLD_RIGHT)
        return player_pos

    def do_mine(self, hovered_block, player_pos, vvel, on_ground):
        bx, by = hovered_block
        center_block = self.get_block_at_world(bx, by)
        if not center_block or center_block.block_type == "air":
            return vvel, on_ground

        td = self._effective_tool()
        damage  = td["damage"]
        radius  = td["mine_radius"]
        fortune = td["fortune_mult"]

        if radius > 0:
            center_col = int(bx) // BLOCK_SIZE
            center_row = (int(by) - SKY_HEIGHT) // BLOCK_SIZE
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    r, c = center_row + dr, center_col + dc
                    if 0 <= r < GRID_ROWS and 0 <= c < GRID_COLS:
                        b = self.grid[r][c]
                        if b.block_type != "air":
                            ore = b.block_type
                            b.block_type = "air"
                            if ore in self.inventory:
                                self.inventory[ore] += max(1, int(fortune))
            self.dynamite_count -= 1
            del self.owned_tools["dynamite"]
            self.active_tool = "fists"
            if self.dynamite_count > 0:
                self.owned_tools["dynamite"] = 1
                self.active_tool = "dynamite"
        else:
            center_block.hp -= damage
            if center_block.hp <= 0:
                ore = center_block.block_type
                center_block.block_type = "air"
                if ore in FOSSIL_PIECES:
                    self.fossil_collected[ore] = True
                    self._flash(f"Fossil piece found! ({sum(self.fossil_collected.values())}/7)", 2.0)
                    if all(self.fossil_collected.values()):
                        self.fossil_complete = True
                        self.state = "fossil"
                elif ore in self.inventory:
                    amount = max(1, int(fortune))
                    if random.random() < (fortune - int(fortune)):
                        amount += 1
                    self.inventory[ore] += amount
                self._damage_tool(ore)

        if self.find_ground_y(player_pos.x) > player_pos.y:
            on_ground = False

        return vvel, on_ground

    def enter_shop(self, player_pos, vvel):
        self.state    = "shop"
        self.shop_tab = "sell"
        return vvel

    def exit_shop(self, player_pos, vvel):
        self.state      = "game"
        player_pos.x    = float(WORLD_RIGHT - PLAYER_WIDTH - 80)
        # make sure the player is seated on top of the ground at the new X
        player_pos.y    = self.find_ground_y(player_pos.x) - PLAYER_HEIGHT
        return player_pos, 0.0, True

    def _buy(self, cost, success_msg):
        if self.coins >= cost:
            self.coins -= cost
            self._flash(success_msg)
            return True
        self._flash("Not enough coins!", 1.0)
        return False

    def draw_world(self, camera_y):
        self.screen.fill((20, 12, 8))

        sky_img_top_on_screen = -camera_y
        if sky_img_top_on_screen > 0:
            self.screen.fill(self.sky_extend_color,
                             (0, 0, SCREEN_WIDTH, sky_img_top_on_screen))
        self.screen.blit(self.background_sky, (0, sky_img_top_on_screen))

        for row in self.grid:
            for block in row:
                if block.block_type != "air":
                    img = self.block_imgs.get(block.block_type)
                    if img:
                        sy = block.y - camera_y
                        if -BLOCK_SIZE < sy < SCREEN_HEIGHT + BLOCK_SIZE:
                            self.screen.blit(img, (block.x, sy))
                            if block.hp < block.max_hp:
                                dmg_frac = 1.0 - (block.hp / block.max_hp)
                                alpha = int(dmg_frac * 160)
                                tint = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
                                tint.fill((0, 0, 0, alpha))
                                self.screen.blit(tint, (block.x, sy))
                                cx, cy2 = block.x + BLOCK_SIZE // 2, sy + BLOCK_SIZE // 2
                                stages = int(dmg_frac * 4) + 1
                                pygame.draw.line(self.screen, (180,160,120),
                                                 (cx, cy2 - 20), (cx + 10, cy2 + 20), 2)
                                if stages >= 2:
                                    pygame.draw.line(self.screen, (180,160,120),
                                                     (cx - 15, cy2 - 10), (cx + 5, cy2 + 15), 2)
                                if stages >= 3:
                                    pygame.draw.line(self.screen, (180,160,120),
                                                     (cx + 8, cy2 - 25), (cx - 8, cy2 + 10), 2)
                                    pygame.draw.line(self.screen, (180,160,120),
                                                     (cx - 20, cy2 + 5), (cx + 20, cy2 - 5), 1)
                                if stages >= 4:
                                    pygame.draw.line(self.screen, (200,170,130),
                                                     (cx - 25, cy2 - 20), (cx + 25, cy2 + 25), 2)
                                    pygame.draw.line(self.screen, (200,170,130),
                                                     (cx + 20, cy2 - 30), (cx - 15, cy2 + 30), 2)

    def draw_fog(self, player_pos, camera_y, radius=250):
        if player_pos.y + PLAYER_HEIGHT < SKY_HEIGHT + BLOCK_SIZE:
            return

        fog = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        fog.fill((0, 0, 0, 220))

        cx = int(player_pos.x + PLAYER_WIDTH // 2)
        cy = int(player_pos.y + PLAYER_HEIGHT // 2) - camera_y

        for r in range(radius, 0, -4):
            alpha = int(220 * (r / radius) ** 2)
            pygame.draw.circle(fog, (0, 0, 0, alpha), (cx, cy), r)

        pygame.draw.circle(fog, (0, 0, 0, 0), (cx, cy), radius // 3)
        self.screen.blit(fog, (0, 0))

    def draw_fossil_complete(self):
        self.screen.fill((180, 180, 180))

        title = self.font_title.render("FOSSIL COMPLETE!", True, (40, 40, 40))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 40))

        if self.fullfossil_img:
            iw = self.fullfossil_img.get_width()
            ih = self.fullfossil_img.get_height()
            self.screen.blit(self.fullfossil_img,
                             (SCREEN_WIDTH // 2 - iw // 2,
                              SCREEN_HEIGHT // 2 - ih // 2 + 30))
        else:
            msg = self.font_large.render("(dip_fullfossil.png not found)", True, (100,100,100))
            self.screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2,
                                   SCREEN_HEIGHT // 2))

        sub = self.font_med.render("You uncovered the ancient fossil!", True, (60, 60, 60))
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2,
                               SCREEN_HEIGHT - 80))

    def draw_hud(self, dt):
        px, py = 10, SCREEN_HEIGHT - 50
        icon_sz, pad = 32, 8
        pw = 6 * (icon_sz + pad + 40) + pad
        surf = pygame.Surface((pw, 48), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 140))
        self.screen.blit(surf, (px - pad, py - 8))
        x = px
        for ore in ["soil", "stone", "copper", "gold", "diamond", "ruby"]:
            self.screen.blit(self.hud_icons[ore], (x, py))
            cs = self.font.render(str(self.inventory[ore]), True, (255, 255, 255))
            self.screen.blit(cs, (x + icon_sz + 4, py + 8))
            x += icon_sz + 4 + cs.get_width() + pad + 4

        coin_surf = self.font_med.render(f"Coins: {self.coins}", True, (255, 215, 0))
        self.screen.blit(coin_surf, (10, SCREEN_HEIGHT - 88))

        found = sum(self.fossil_collected.values())
        fossil_surf = self.font_med.render(f"Fossils: {found}/7", True, (200, 190, 160))
        self.screen.blit(fossil_surf, (10, SCREEN_HEIGHT - 116))

        td = self._effective_tool()
        tool_label = td["label"]
        if self.active_tool != "fists":
            dur = self.owned_tools.get(self.active_tool, 0)
            max_dur = td["base_durability"]
            dur_pct = dur / max_dur
            bar_w = 120
            tool_surf = self.font_med.render(
                f"{tool_label}  {dur}/{max_dur}", True, (200, 200, 200))
            self.screen.blit(tool_surf, (10, SCREEN_HEIGHT - 124))
            pygame.draw.rect(self.screen, (60, 60, 60),
                             (10, SCREEN_HEIGHT - 104, bar_w, 8), border_radius=4)
            bar_col = (80, 220, 80) if dur_pct > 0.4 else (
                       220, 180, 40) if dur_pct > 0.2 else (220, 60, 60)
            pygame.draw.rect(self.screen, bar_col,
                             (10, SCREEN_HEIGHT - 104, int(bar_w * dur_pct), 8),
                             border_radius=4)
            if self.active_tool == "dynamite":
                ds = self.font.render(f"x{self.dynamite_count}", True, (255,120,80))
                self.screen.blit(ds, (140, SCREEN_HEIGHT - 124))
        else:
            tool_surf = self.font_med.render(tool_label, True, (180, 180, 180))
            self.screen.blit(tool_surf, (10, SCREEN_HEIGHT - 124))

        bw, bh = 170, 46
        bx2, by2 = SCREEN_WIDTH - bw - 12, 12
        draw_rounded_rect(self.screen, (160, 120, 20),
                          (bx2, by2, bw, bh), radius=8,
                          border_color=(255, 215, 0), border_width=2)
        lbl = self.font_med.render("[ T ]  Shop", True, (255, 255, 255))
        self.screen.blit(lbl, (bx2 + (bw - lbl.get_width()) // 2,
                               by2 + (bh - lbl.get_height()) // 2))
        hint = self.font.render("or walk right ->", True, (255, 230, 100))
        self.screen.blit(hint, (SCREEN_WIDTH - hint.get_width() - 12, 64))

        if self._flash_ttl > 0:
            self._flash_ttl -= dt
            fs = self.font_large.render(self._flash_msg, True, (80, 220, 80))
            fs.set_alpha(min(255, int(self._flash_ttl * 300)))
            self.screen.blit(fs, (SCREEN_WIDTH // 2 - fs.get_width() // 2,
                                  SCREEN_HEIGHT // 2 - 60))

    def _tab_button(self, label, rect, active):
        col    = (55, 55, 62)  if active else (35, 35, 40)
        border = (255, 215, 0) if active else (90, 90, 100)
        draw_rounded_rect(self.screen, col, rect, radius=8,
                          border_color=border, border_width=2)
        txt = self.font_large.render(
            label, True, (255, 255, 255) if active else (140, 140, 150))
        self.screen.blit(txt, (rect[0] + (rect[2] - txt.get_width())  // 2,
                               rect[1] + (rect[3] - txt.get_height()) // 2))

    def draw_shop(self, dt, mouse_pos, mouse_clicked):
        self.screen.fill((22, 22, 28))

        title = self.font_title.render("SHOP", True, (220, 220, 230))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 14))
        coins_s = self.font_large.render(f"Coins: {self.coins}", True, (255, 215, 0))
        self.screen.blit(coins_s, (SCREEN_WIDTH // 2 - coins_s.get_width() // 2, 78))

        tab_y = 126
        tab_h = 46
        tab_w = 155
        gap   = 12
        total_w = 4 * tab_w + 3 * gap
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        sell_rect = (start_x,                     tab_y, tab_w, tab_h)
        upg_rect  = (start_x +   tab_w +   gap,   tab_y, tab_w, tab_h)
        tool_rect = (start_x + 2*(tab_w +   gap),  tab_y, tab_w, tab_h)
        skin_rect = (start_x + 3*(tab_w +   gap),  tab_y, tab_w, tab_h)

        self._tab_button("Sell Blocks", sell_rect, self.shop_tab == "sell")
        self._tab_button("Upgrades",   upg_rect,  self.shop_tab == "upgrades")
        self._tab_button("Tools",      tool_rect,  self.shop_tab == "tools")
        self._tab_button("Skins",      skin_rect,  self.shop_tab == "skins")

        if mouse_clicked:
            mx, my = mouse_pos
            for tab_name, rect in [("sell",      sell_rect),
                                    ("upgrades",  upg_rect),
                                    ("tools",     tool_rect),
                                    ("skins",     skin_rect)]:
                if rect[0] <= mx <= rect[0]+rect[2] and rect[1] <= my <= rect[1]+rect[3]:
                    self.shop_tab = tab_name

        content_rect = pygame.Rect(60, 188, SCREEN_WIDTH - 120, SCREEN_HEIGHT - 300)
        draw_rounded_rect(self.screen, (32, 32, 40), content_rect,
                          radius=12, border_color=(60, 60, 72), border_width=2)

        if self.shop_tab == "sell":
            self._draw_sell_tab(content_rect, mouse_pos, mouse_clicked)
        elif self.shop_tab == "upgrades":
            self._draw_upgrades_tab(content_rect, mouse_pos, mouse_clicked)
        elif self.shop_tab == "tools":
            self._draw_tools_tab(content_rect, mouse_pos, mouse_clicked)
        else:
            self._draw_skins_tab(content_rect, mouse_pos, mouse_clicked)

        ex_w, ex_h = 220, 50
        ex_x = SCREEN_WIDTH // 2 - ex_w // 2
        ex_y = SCREEN_HEIGHT - 72
        draw_rounded_rect(self.screen, (55, 30, 30), (ex_x, ex_y, ex_w, ex_h),
                          radius=8, border_color=(180, 70, 70), border_width=2)
        el = self.font_large.render("[ ESC ]  Exit", True, (220, 160, 160))
        self.screen.blit(el, (ex_x + (ex_w - el.get_width())  // 2,
                              ex_y + (ex_h - el.get_height()) // 2))

        if self._flash_ttl > 0:
            self._flash_ttl -= dt
            col = (80,220,80) if "Not" not in self._flash_msg else (220,80,80)
            fs = self.font_large.render(self._flash_msg, True, col)
            fs.set_alpha(min(255, int(self._flash_ttl * 300)))
            self.screen.blit(fs, (SCREEN_WIDTH // 2 - fs.get_width() // 2,
                                  SCREEN_HEIGHT - 130))

    def _draw_sell_tab(self, area, mouse_pos, mouse_clicked):
        ores   = ["soil", "stone", "copper", "gold", "diamond", "ruby"]
        cols   = 3
        row_h  = 88
        col_w  = (area.width - 40) // cols
        sx, sy = area.x + 20, area.y + 16

        for i, ore in enumerate(ores):
            ci = i % cols
            ri = i // cols
            rx = sx + ci * col_w
            ry = sy + ri * row_h

            row_rect = pygame.Rect(rx, ry, col_w - 10, row_h - 8)
            draw_rounded_rect(self.screen, (42, 42, 52), row_rect,
                              radius=8, border_color=(60, 60, 72), border_width=1)

            self.screen.blit(self.shop_icons[ore], (rx + 8, ry + (row_h-8-48)//2))

            name_s  = self.font_med.render(ore.capitalize(), True, (210,210,210))
            count_s = self.font.render(f"x{self.inventory[ore]}", True, (160,160,160))
            price_s = self.font.render(f"{ORE_PRICES[ore]}c ea", True, (255,215,0))
            self.screen.blit(name_s,  (rx+62, ry+8))
            self.screen.blit(count_s, (rx+62, ry+32))
            self.screen.blit(price_s, (rx+62, ry+52))

            bw, bh = 76, 28
            bx2 = rx + col_w - 18 - bw
            by2 = ry + (row_h - 8 - bh) // 2
            has = self.inventory[ore] > 0
            draw_rounded_rect(self.screen,
                              (38,110,38) if has else (45,45,45),
                              (bx2,by2,bw,bh), radius=6,
                              border_color=(70,190,70) if has else (65,65,65),
                              border_width=1)
            sl = self.font.render("Sell All", True,
                                  (210,255,210) if has else (90,90,90))
            self.screen.blit(sl, (bx2+(bw-sl.get_width())//2,
                                  by2+(bh-sl.get_height())//2))
            if mouse_clicked and has:
                mx, my = mouse_pos
                if bx2 <= mx <= bx2+bw and by2 <= my <= by2+bh:
                    earned = self.inventory[ore] * ORE_PRICES[ore]
                    self.coins += earned
                    self._flash(f"+{earned} coins!")
                    self.inventory[ore] = 0

    def _draw_upgrades_tab(self, area, mouse_pos, mouse_clicked):
        has_pick = "pickaxe" in self.owned_tools

        if not has_pick:
            msg = self.font_large.render(
                "Buy a Pickaxe in the Tools tab first.", True, (160,100,60))
            self.screen.blit(msg, (area.x + (area.width-msg.get_width())//2,
                                   area.y + 60))
            return

        upg_names = ["fortune", "efficiency", "unbreaking"]
        row_h = (area.height - 40) // 3
        sx, sy = area.x + 24, area.y + 16

        for i, upg_key in enumerate(upg_names):
            upg    = PICKAXE_UPGRADES[upg_key]
            cur_lv = self.pickaxe_upgrades[upg_key]
            ry     = sy + i * row_h

            row_rect = pygame.Rect(sx, ry, area.width - 48, row_h - 10)
            draw_rounded_rect(self.screen, (38, 40, 50), row_rect,
                              radius=8, border_color=(58,60,74), border_width=1)

            label_s = self.font_large.render(upg["label"], True, (220,220,230))
            desc_s  = self.font.render(upg["description"], True, (140,140,155))
            self.screen.blit(label_s, (sx+14, ry+10))
            self.screen.blit(desc_s,  (sx+14, ry+42))

            for lv in range(1, 4):
                pip_x = sx + 14 + (lv-1)*36
                pip_y = ry + 66
                filled = lv <= cur_lv
                pygame.draw.circle(self.screen,
                                   (255,200,40) if filled else (55,55,65),
                                   (pip_x+10, pip_y+10), 10)
                pygame.draw.circle(self.screen, (90,90,100),
                                   (pip_x+10, pip_y+10), 10, 2)
                if upg_key == "unbreaking":
                    cost_lbl = self.font.render(
                        f"-{PICKAXE_UPGRADES['unbreaking']['effects'][lv-1]}/hit",
                        True, (255,200,40) if filled else (80,80,90))
                    self.screen.blit(cost_lbl, (pip_x + 2, pip_y + 23))

            if cur_lv < 3:
                cost = upg["costs"][cur_lv]
                can_buy = self.coins >= cost
                bw, bh = 130, 36
                bx2 = sx + area.width - 48 - bw - 14
                by2 = ry + (row_h - 10 - bh) // 2
                draw_rounded_rect(self.screen,
                                  (35,100,40) if can_buy else (42,42,42),
                                  (bx2,by2,bw,bh), radius=6,
                                  border_color=(70,180,70) if can_buy else (62,62,62),
                                  border_width=1)
                bl = self.font_med.render(
                    f"Upgrade  {cost}c", True,
                    (200,255,200) if can_buy else (85,85,85))
                self.screen.blit(bl, (bx2+(bw-bl.get_width())//2,
                                      by2+(bh-bl.get_height())//2))
                if mouse_clicked and can_buy:
                    mx, my = mouse_pos
                    if bx2 <= mx <= bx2+bw and by2 <= my <= by2+bh:
                        if self._buy(cost, f"{upg['label']} {cur_lv+1} unlocked!"):
                            self.pickaxe_upgrades[upg_key] += 1
            else:
                maxed = self.font_med.render("MAX", True, (255,200,40))
                bx2 = sx + area.width - 48 - 130 - 14
                by2 = ry + (row_h - 10 - 36) // 2
                self.screen.blit(maxed, (bx2+40, by2+6))

    def _draw_tools_tab(self, area, mouse_pos, mouse_clicked):
        tools = ["pickaxe", "dynamite", "radar", "drill"]
        cols  = 2
        col_w = (area.width - 40) // cols
        row_h = (area.height - 30) // 2
        sx, sy = area.x + 20, area.y + 12

        for i, tool_key in enumerate(tools):
            ci = i % cols
            ri = i // cols
            rx = sx + ci * col_w
            ry = sy + ri * row_h
            td = TOOL_DEFS[tool_key]

            card = pygame.Rect(rx, ry, col_w - 12, row_h - 10)
            draw_rounded_rect(self.screen, (38, 40, 50), card,
                              radius=10, border_color=(58,60,74), border_width=1)

            self.screen.blit(self.tool_imgs[tool_key], (rx+10, ry+10))

            name_s = self.font_large.render(td["label"], True, (220,220,230))
            self.screen.blit(name_s, (rx+68, ry+10))

            desc_s = self.font.render(td["description"], True, (130,130,145))
            self.screen.blit(desc_s, (rx+68, ry+42))

            stats = (f"DMG:{td['damage']}  "
                     f"DUR:{td['base_durability']}  "
                     f"FORT:x{td['fortune_mult']}")
            stat_s = self.font.render(stats, True, (100,160,200))
            self.screen.blit(stat_s, (rx+68, ry+64))

            owned = tool_key in self.owned_tools
            if tool_key == "dynamite":
                owned = self.dynamite_count > 0

            bw, bh = 120, 34
            bx2 = card.right - bw - 10
            by2 = card.bottom - bh - 10

            if tool_key == "dynamite":
                can_buy = self.coins >= td["price"]
                draw_rounded_rect(self.screen,
                                  (35,100,40) if can_buy else (42,42,42),
                                  (bx2,by2,bw,bh), radius=6,
                                  border_color=(70,180,70) if can_buy else (62,62,62),
                                  border_width=1)
                cnt_txt = f"Buy ({td['price']}c)"
                if self.dynamite_count > 0:
                    cnt_txt += f"  x{self.dynamite_count}"
                bl = self.font.render(cnt_txt, True,
                                      (200,255,200) if can_buy else (85,85,85))
                self.screen.blit(bl, (bx2+(bw-bl.get_width())//2,
                                      by2+(bh-bl.get_height())//2))
                if mouse_clicked and can_buy:
                    mx, my = mouse_pos
                    if bx2 <= mx <= bx2+bw and by2 <= my <= by2+bh:
                        if self._buy(td["price"], "Dynamite purchased!"):
                            self.dynamite_count += 1
                            if "dynamite" not in self.owned_tools:
                                self.owned_tools["dynamite"] = 1
                                self.active_tool = "dynamite"

            elif owned:
                is_active = self.active_tool == tool_key
                draw_rounded_rect(self.screen,
                                  (50,50,130) if is_active else (38,80,100),
                                  (bx2,by2,bw,bh), radius=6,
                                  border_color=(100,100,230) if is_active else (60,130,160),
                                  border_width=1)
                label_txt = "Equipped" if is_active else "Equip"
                bl = self.font_med.render(label_txt, True,
                                          (160,160,255) if is_active else (160,210,230))
                self.screen.blit(bl, (bx2+(bw-bl.get_width())//2,
                                      by2+(bh-bl.get_height())//2))
                if mouse_clicked and not is_active:
                    mx, my = mouse_pos
                    if bx2 <= mx <= bx2+bw and by2 <= my <= by2+bh:
                        self.active_tool = tool_key

                dur = self.owned_tools.get(tool_key, 0)
                max_dur = td["base_durability"]
                dur_s = self.font.render(
                    f"Durability: {dur}/{max_dur}", True, (160,160,160))
                self.screen.blit(dur_s, (rx+10, by2-2))

            else:
                can_buy = self.coins >= td["price"]
                draw_rounded_rect(self.screen,
                                  (35,100,40) if can_buy else (42,42,42),
                                  (bx2,by2,bw,bh), radius=6,
                                  border_color=(70,180,70) if can_buy else (62,62,62),
                                  border_width=1)
                bl = self.font_med.render(
                    f"Buy  {td['price']}c", True,
                    (200,255,200) if can_buy else (85,85,85))
                self.screen.blit(bl, (bx2+(bw-bl.get_width())//2,
                                      by2+(bh-bl.get_height())//2))
                if mouse_clicked and can_buy:
                    mx, my = mouse_pos
                    if bx2 <= mx <= bx2+bw and by2 <= my <= by2+bh:
                        if self._buy(td["price"], f"{td['label']} purchased!"):
                            self.owned_tools[tool_key] = td["base_durability"]
                            self.active_tool = tool_key

    def _draw_skins_tab(self, area, mouse_pos, mouse_clicked):
        sx, sy = area.x + 30, area.y + 20

        card = pygame.Rect(sx, sy, area.width - 60, 160)
        draw_rounded_rect(self.screen, (38, 40, 50), card,
                          radius=10, border_color=(58, 60, 74), border_width=1)

        # Preview image
        preview_size = 100
        preview_img = self.player_img_santa if self.player_img_santa else self.player_img_default
        preview = pygame.transform.scale(preview_img, (preview_size, preview_size))
        self.screen.blit(preview, (sx + 20, sy + 30))

        name_s  = self.font_large.render("Santa Skin", True, (220, 220, 230))
        price_s = self.font_med.render("10,000 coins", True, (255, 215, 0))
        self.screen.blit(name_s,  (sx + 140, sy + 20))
        self.screen.blit(price_s, (sx + 140, sy + 58))

        owned = "santa" in self.owned_skins
        bw, bh = 140, 38
        bx2 = card.right - bw - 20
        by2 = sy + (card.height - bh) // 2

        if not owned:
            can_buy = self.coins >= 10000
            draw_rounded_rect(self.screen,
                              (35, 100, 40) if can_buy else (42, 42, 42),
                              (bx2, by2, bw, bh), radius=6,
                              border_color=(70, 180, 70) if can_buy else (62, 62, 62),
                              border_width=1)
            bl = self.font_med.render("Buy 10,000c", True,
                                      (200, 255, 200) if can_buy else (85, 85, 85))
            self.screen.blit(bl, (bx2 + (bw - bl.get_width()) // 2,
                                  by2 + (bh - bl.get_height()) // 2))
            if mouse_clicked and can_buy:
                mx, my = mouse_pos
                if bx2 <= mx <= bx2 + bw and by2 <= my <= by2 + bh:
                    if self._buy(10000, "Santa skin unlocked! Ho ho ho!"):
                        self.owned_skins.add("santa")
        else:
            is_equipped = self.equipped_skin == "santa"
            draw_rounded_rect(self.screen,
                              (50, 50, 130) if is_equipped else (38, 80, 100),
                              (bx2, by2, bw, bh), radius=6,
                              border_color=(100, 100, 230) if is_equipped else (60, 130, 160),
                              border_width=1)
            lbl_txt = "Unequip" if is_equipped else "Equip"
            bl = self.font_med.render(lbl_txt, True,
                                      (160, 160, 255) if is_equipped else (160, 210, 230))
            self.screen.blit(bl, (bx2 + (bw - bl.get_width()) // 2,
                                  by2 + (bh - bl.get_height()) // 2))
            if mouse_clicked:
                mx, my = mouse_pos
                if bx2 <= mx <= bx2 + bw and by2 <= my <= by2 + bh:
                    if is_equipped:
                        self.equipped_skin = None
                        self.player_img = self.player_img_default
                    else:
                        self.equipped_skin = "santa"
                        self.player_img = self.player_img_santa or self.player_img_default

            status_s = self.font.render(
                "Equipped" if is_equipped else "Owned", True,
                (100, 200, 100) if is_equipped else (160, 160, 160))
            self.screen.blit(status_s, (sx + 140, sy + 95))

    async def main(self):
        pygame.mixer.init()
        sound_effect = pygame.mixer.Sound("assets/audio/dip_backgroundmusic.ogg")
        sound_effect.set_volume(0.5)
        sound_effect.play()

        # initial player position: place above the first solid block at x=400
        # (previously we hardcoded a block offset which could land the
        # player inside terrain if the constants changed). use the helper
        # so that the spawn height always sits on top of the ground.
        player_pos    = pygame.math.Vector2(400, 0)
        # y will be fixed once the grid has been created
        player_pos.y  = self.find_ground_y(player_pos.x) - PLAYER_HEIGHT

        speed         = 300
        vvel          = 0.0
        on_ground     = True  # we're already on the ground at start
        ground_y      = SKY_HEIGHT + GRID_ROWS * BLOCK_SIZE
        hovered_block = None

        # start the game teleported right next to the shop trigger
        # (just a few pixels left of it) while remaining in the game state.
        # also position the player on the ground instead of sky level.
        player_pos.x = float(SHOP_TRIGGER_X - PLAYER_WIDTH - 8)
        player_pos.y = self.find_ground_y(player_pos.x) - PLAYER_HEIGHT
        on_ground = True
        # state remains "game"; do not call enter_shop

        while True:
            dt = self.clock.tick(60) / 1000
            mouse_pos     = pygame.mouse.get_pos()
            mouse_clicked = False

            # FOSSIL COMPLETE SCREEN
            if self.state == "fossil":
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit(); sys.exit()
                self.draw_fossil_complete()
                pygame.display.flip()
                await asyncio.sleep(0)
                continue

            # SHOP
            if self.state == "shop":
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit(); sys.exit()
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        player_pos, vvel, on_ground = self.exit_shop(player_pos, vvel)
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        mouse_clicked = True
                self.draw_shop(dt, mouse_pos, mouse_clicked)
                pygame.display.flip()
                await asyncio.sleep(0)
                continue

            # GAME
            player_pos, vvel, on_ground, hovered_block, self.facing, draw_img = movement(
                player_pos, vvel, on_ground, speed, dt, ground_y, self.player_img,
                self.facing,
                gravity=GRAVITY, jump_force=JUMP_FORCE,
                block_size=BLOCK_SIZE, sky_height=SKY_HEIGHT,
                max_x=WORLD_RIGHT, min_x=WORLD_LEFT
            )
            player_pos, vvel, on_ground = self.snap_player_to_ground(
                player_pos, vvel, on_ground)
            if vvel < 0:
                player_pos, vvel = self.snap_player_to_ceiling(player_pos, vvel)
            player_pos = self.resolve_horizontal_block_collision(player_pos)
            player_pos = self.clamp_to_walls(player_pos)

            if (player_pos.x >= SHOP_TRIGGER_X and
                    player_pos.y <= SKY_HEIGHT - PLAYER_HEIGHT + 8):
                vvel = self.enter_shop(player_pos, vvel)
                continue

            camera_y = int(player_pos.y - SCREEN_HEIGHT // 2)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_e and hovered_block:
                        vvel, on_ground = self.do_mine(
                            hovered_block, player_pos, vvel, on_ground)
                    if event.key == pygame.K_t:
                        player_pos.x = float(SHOP_TRIGGER_X - 200)
                        player_pos.y = float(SKY_HEIGHT - PLAYER_HEIGHT)
                        vvel = 0.0
                        on_ground = True

            self.draw_world(camera_y)
            self.draw_fog(player_pos, camera_y)

            if hovered_block:
                bx, by = hovered_block
                block = self.get_block_at_world(bx, by)
                if block and block.block_type != "air":
                    pygame.draw.rect(
                        self.screen, (255, 255, 0),
                        (bx, by - camera_y, BLOCK_SIZE, BLOCK_SIZE), 3)
                    bar_w   = BLOCK_SIZE - 8
                    bar_h   = 8
                    bar_x   = bx + 4
                    bar_y   = by - camera_y - 14
                    hp_frac = block.hp / block.max_hp
                    pygame.draw.rect(self.screen, (40, 40, 40),
                                     (bar_x, bar_y, bar_w, bar_h), border_radius=3)
                    bar_col = ((80,220,80) if hp_frac > 0.5 else
                               (220,180,40) if hp_frac > 0.25 else (220,60,60))
                    pygame.draw.rect(self.screen, bar_col,
                                     (bar_x, bar_y, int(bar_w * hp_frac), bar_h),
                                     border_radius=3)
                    hp_txt = self.font.render(f"{block.hp}/{block.max_hp}", True, (220,220,220))
                    txt_x  = min(bar_x, SCREEN_WIDTH - hp_txt.get_width() - 4)
                    self.screen.blit(hp_txt, (txt_x, bar_y - hp_txt.get_height() - 2))

            self.screen.blit(draw_img,
                             (int(player_pos.x), int(player_pos.y) - camera_y))
            self.draw_hud(dt)
            pygame.display.flip()
            await asyncio.sleep(0)


if __name__ == "__main__":
    game = digging()
    asyncio.run(game.main())