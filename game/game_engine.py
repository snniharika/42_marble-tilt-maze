import pygame
import io
import math
import struct
import wave

from .marble import Marble
from .wall import Wall

WHITE = (255, 255, 255)
DARK = (40, 40, 50)
WALL_COLOR = (90, 90, 110)
GOAL_COLOR = (60, 200, 120)


class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.marble = Marble(50, 50)

        self.difficulties = {
            "Easy": {
                "tilt_strength": 0.45,
                "friction": 0.04,
                "time_limit_ms": 60000
            },
            "Medium": {
                "tilt_strength": 0.60,
                "friction": 0.02,
                "time_limit_ms": 45000
            },
            "Hard": {
                "tilt_strength": 0.80,
                "friction": 0.01,
                "time_limit_ms": 30000
            }
        }

        self.current_difficulty = "Medium"
        self.tilt_strength = 0.6
        self.friction = 0.02
        self.max_speed = 9

        self.walls = self._build_maze()
        self.goal_x, self.goal_y, self.goal_radius = width - 60, height - 60, 22

        self.time_limit_ms = 45000
        self.start_ticks = pygame.time.get_ticks()

        self.font = pygame.font.SysFont("Arial", 26)
        self.title_font = pygame.font.SysFont("Arial", 42)
        self.result_font = pygame.font.SysFont("Arial", 30)
        self.menu_font = pygame.font.SysFont("Arial", 24)

        self.game_over = False
        self.result = None
        self.finish_time_ms = None
        self.exit_requested = False

        self._initialize_sounds()

    def _initialize_sounds(self):
        self.bounce_sound = self._create_tone(
            frequency=220,
            duration=0.08,
            volume=0.35
        )

        self.goal_sound = self._create_tone(
            frequency=880,
            duration=0.25,
            volume=0.45
        )

        self.timeout_sound = self._create_tone(
            frequency=180,
            duration=0.5,
            volume=0.45
        )

    def _create_tone(self, frequency, duration, volume):
        sample_rate = 44100
        samples = int(sample_rate * duration)

        audio_data = bytearray()

        for i in range(samples):
            time = i / sample_rate

            envelope = 1.0 - (i / samples)

            value = int(
                32767
                * volume
                * envelope
                * math.sin(2 * math.pi * frequency * time)
            )

            audio_data.extend(
                struct.pack("<h", value)
            )

        buffer = io.BytesIO()

        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)

        buffer.seek(0)

        return pygame.mixer.Sound(file=buffer)

    def _build_maze(self):
        walls = []
        t = 16

        walls.append(Wall(0, 0, self.width, t))
        walls.append(Wall(0, self.height - t, self.width, t))
        walls.append(Wall(0, 0, t, self.height))
        walls.append(Wall(self.width - t, 0, t, self.height))

        walls.append(Wall(0, 140, self.width - 140, t))
        walls.append(Wall(140, 260, self.width - 140, t))
        walls.append(Wall(0, 380, self.width - 140, t))

        return walls

    def handle_event(self, event):
        if not self.game_over:
            return

        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_1:
            self._restart_game("Easy")

        elif event.key == pygame.K_2:
            self._restart_game("Medium")

        elif event.key == pygame.K_3:
            self._restart_game("Hard")

        elif event.key in (pygame.K_ESCAPE, pygame.K_q):
            self.exit_requested = True

    def _restart_game(self, difficulty):
        settings = self.difficulties[difficulty]

        self.current_difficulty = difficulty
        self.tilt_strength = settings["tilt_strength"]
        self.friction = settings["friction"]
        self.time_limit_ms = settings["time_limit_ms"]

        self.marble.x = 50
        self.marble.y = 50
        self.marble.vx = 0
        self.marble.vy = 0

        self.start_ticks = pygame.time.get_ticks()

        self.game_over = False
        self.result = None
        self.finish_time_ms = None
        self.exit_requested = False

    def handle_input(self):
        if self.game_over:
            return

        mouse_x, mouse_y = pygame.mouse.get_pos()
        dx = mouse_x - self.width // 2
        dy = mouse_y - self.height // 2
        dist = max(1, (dx ** 2 + dy ** 2) ** 0.5)

        ax = (dx / dist) * self.tilt_strength
        ay = (dy / dist) * self.tilt_strength

        self.marble.vx += ax
        self.marble.vy += ay

    def update(self):
        if self.game_over:
            return

        elapsed = pygame.time.get_ticks() - self.start_ticks

        if elapsed >= self.time_limit_ms:
            self.game_over = True
            self.result = "timeout"
            self.timeout_sound.play()
            return

        self.marble.vx *= (1 - self.friction)
        self.marble.vy *= (1 - self.friction)

        speed = (self.marble.vx ** 2 + self.marble.vy ** 2) ** 0.5

        if speed > self.max_speed:
            scale = self.max_speed / speed
            self.marble.vx *= scale
            self.marble.vy *= scale

        self.marble.x += self.marble.vx
        self.marble.y += self.marble.vy

        self._resolve_wall_collisions()

        gx = self.goal_x - self.marble.x
        gy = self.goal_y - self.marble.y

        if (gx ** 2 + gy ** 2) ** 0.5 <= self.goal_radius:
            self.game_over = True
            self.result = "solved"
            self.finish_time_ms = elapsed
            self.goal_sound.play()

    def _resolve_wall_collisions(self):
        restitution = 0.3

        for wall in self.walls:
            wall_rect = wall.rect()

            closest_x = max(
                wall_rect.left,
                min(self.marble.x, wall_rect.right)
            )

            closest_y = max(
                wall_rect.top,
                min(self.marble.y, wall_rect.bottom)
            )

            dx = self.marble.x - closest_x
            dy = self.marble.y - closest_y

            distance_squared = dx * dx + dy * dy
            radius = self.marble.radius

            if distance_squared > radius * radius:
                continue

            if distance_squared > 0:
                distance = distance_squared ** 0.5

                normal_x = dx / distance
                normal_y = dy / distance

                penetration = radius - distance

            else:
                left_distance = abs(
                    self.marble.x - wall_rect.left
                )

                right_distance = abs(
                    wall_rect.right - self.marble.x
                )

                top_distance = abs(
                    self.marble.y - wall_rect.top
                )

                bottom_distance = abs(
                    wall_rect.bottom - self.marble.y
                )

                minimum_distance = min(
                    left_distance,
                    right_distance,
                    top_distance,
                    bottom_distance
                )

                if minimum_distance == left_distance:
                    normal_x, normal_y = -1, 0
                    penetration = radius + left_distance

                elif minimum_distance == right_distance:
                    normal_x, normal_y = 1, 0
                    penetration = radius + right_distance

                elif minimum_distance == top_distance:
                    normal_x, normal_y = 0, -1
                    penetration = radius + top_distance

                else:
                    normal_x, normal_y = 0, 1
                    penetration = radius + bottom_distance

            self.marble.x += normal_x * penetration
            self.marble.y += normal_y * penetration

            velocity_into_wall = (
                self.marble.vx * normal_x +
                self.marble.vy * normal_y
            )

            if velocity_into_wall < 0:
                self.marble.vx -= (
                    (1 + restitution)
                    * velocity_into_wall
                    * normal_x
                )

                self.marble.vy -= (
                    (1 + restitution)
                    * velocity_into_wall
                    * normal_y
                )

                self.bounce_sound.play()

    def render(self, screen):
        screen.fill(DARK)

        if self.game_over:
            self._render_game_over(screen)
            return

        for wall in self.walls:
            pygame.draw.rect(
                screen,
                WALL_COLOR,
                wall.rect()
            )

        pygame.draw.circle(
            screen,
            GOAL_COLOR,
            (self.goal_x, self.goal_y),
            self.goal_radius
        )

        pygame.draw.circle(
            screen,
            WHITE,
            (int(self.marble.x), int(self.marble.y)),
            self.marble.radius
        )

        elapsed = pygame.time.get_ticks() - self.start_ticks

        seconds_left = max(
            0,
            (self.time_limit_ms - elapsed) // 1000
        )

        timer_text = self.font.render(
            f"Time: {seconds_left}s",
            True,
            WHITE
        )

        difficulty_text = self.menu_font.render(
            f"Difficulty: {self.current_difficulty}",
            True,
            WHITE
        )

        screen.blit(timer_text, (10, 10))
        screen.blit(difficulty_text, (10, 45))

    def _render_game_over(self, screen):
        if self.result == "solved":
            title = self.title_font.render(
                "Maze Solved!",
                True,
                GOAL_COLOR
            )

            finish_seconds = self.finish_time_ms / 1000

            result_text = self.result_font.render(
                f"Finished in {finish_seconds:.1f} seconds",
                True,
                WHITE
            )

        else:
            title = self.title_font.render(
                "Time's Up!",
                True,
                WHITE
            )

            result_text = self.result_font.render(
                "Maze not solved",
                True,
                WHITE
            )

        replay_text = self.menu_font.render(
            "1 - Easy    2 - Medium    3 - Hard",
            True,
            WHITE
        )

        exit_text = self.menu_font.render(
            "Press Escape or Q to exit",
            True,
            WHITE
        )

        title_rect = title.get_rect(
            center=(
                self.width // 2,
                self.height // 2 - 100
            )
        )

        result_rect = result_text.get_rect(
            center=(
                self.width // 2,
                self.height // 2 - 30
            )
        )

        replay_rect = replay_text.get_rect(
            center=(
                self.width // 2,
                self.height // 2 + 40
            )
        )

        exit_rect = exit_text.get_rect(
            center=(
                self.width // 2,
                self.height // 2 + 90
            )
        )

        screen.blit(title, title_rect)
        screen.blit(result_text, result_rect)
        screen.blit(replay_text, replay_rect)
        screen.blit(exit_text, exit_rect)
