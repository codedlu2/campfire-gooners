import pygame
import sys

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

GRASS_TILE_HEIGHT = 243  # height of the grass tile
GRASS_ROWS = 2           # how many rows of grass tiles to show at ground level
GRASS_VISIBLE_HEIGHT = GRASS_TILE_HEIGHT  # one row of grass visible at the transition


def init():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Game")

    assets = {}
    assets["background"] = pygame.image.load("dip_background.png").convert()
    assets["soil"] = pygame.image.load("dip_soil.png").convert()
    assets["grass"] = pygame.image.load("dip_grass.png").convert_alpha()

    return screen, assets

 
def main():
    screen, assets = init()
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        draw_background(screen, assets, SCREEN_WIDTH, SCREEN_HEIGHT)
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()