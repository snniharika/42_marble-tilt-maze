import pygame
from game.game_engine import GameEngine

pygame.init()

WIDTH, HEIGHT = 600, 500
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Marble Tilt Maze - Pygame Version")

clock = pygame.time.Clock()
FPS = 60

engine = GameEngine(WIDTH, HEIGHT)

def main():
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            engine.handle_event(event)

        engine.handle_input()
        engine.update()
        engine.render(SCREEN)

        if engine.exit_requested:
            running = False

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
