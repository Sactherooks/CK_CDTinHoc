"""Simple "evade falling projectiles" game using pygame.

- Theme: Ancient China (you can replace colors and art with your own images)
- Controls: Arrow keys (left/right) to dodge falling projectiles
- Goal: Survive as long as possible (score increases over time)

Place optional images next to this file:
- background.png
- player.png
- projectile.png

If those are missing, the game will render simple shapes instead.
""" 

import random
import sys
import pygame

# ---- Config ----
# Feel free to adjust these for a bigger / smaller window.
# Tip: keeping the same aspect ratio (e.g., 16:9) makes layout easier.
SCREEN_WIDTH = 1860
SCREEN_HEIGHT = 960
FPS = 60

PLAYER_SPEED = 6
JUMP_SPEED = 10
GRAVITY = 0.35
PARRY_DURATION = 250  # ms the parry stays active
PARRY_COOLDOWN = 700  # ms before you can parry again

PROJECTILE_SPEED_START = 2.5
PROJECTILE_ACCELERATION = 0.05  # increases over time (speed only)
PROJECTILE_SPAWN_TIME = 1100  # ms (fixed - fewer projectiles, easier)

ITEM_SPAWN_TIME = 10000  # ms xuất hiện item (10 giây)
ITEM_DURATION = 3000     # ms bất tử sau khi nhặt
ANIM_FRAME_SPEED = 100   # ms mỗi frame animation

# ---- Helpers ----

def try_load_image(path, size=None):
    """Load an image and scale it if size is provided."""
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.scale(img, size)
        return img
    except Exception:
        return None


class Player:
    def __init__(self, screen_rect):
        self.width = 250
        self.height = 250
        
        self.rect = pygame.Rect(
            screen_rect.centerx - self.width // 2,
            screen_rect.bottom - self.height - 120,
            self.width,
            self.height,
        )
        self.speed = PLAYER_SPEED
        self.vy = 0
        self.on_ground = True
        self.ground_y = self.rect.y

        self.parry_active = False
        self.parry_timer = 0
        self.parry_cooldown = 0

        # fallback surface (phải tạo trước khi load ảnh)
        fallback = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(fallback, (20, 120, 20), (0, 0, self.width, self.height), border_radius=10)

        self.image_idle = try_load_image("C:/Users/TBL/Documents/GitHub/App-trung-dong/mc_normal.png", (self.width, self.height))
        self.frames = [
            try_load_image("C:/Users/TBL/Documents/GitHub/App-trung-dong/Không Có Tiêu Đề9_20260402131643.png", (self.width, self.height)),
            try_load_image("C:/Users/TBL/Documents/GitHub/App-trung-dong/Không Có Tiêu Đề9_20260402131649.png", (self.width, self.height)),
        ]
        self.image_parry = try_load_image("C:/Users/TBL/Documents/GitHub/App-trung-dong/Không Có Tiêu Đề51_20260402134240.png", (self.width, self.height))
        if self.image_parry is None:
            self.image_parry = fallback
        if self.image_idle is None:
            self.image_idle = fallback
        for i in range(len(self.frames)):
            if self.frames[i] is None:
                self.frames[i] = fallback

        self.image = self.image_idle
        self.anim_index = 0
        self.anim_timer = 0
        self.anim_speed = 150  # ms mỗi frame
        

    def update(self, keys, screen_rect, dt):
        dx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += self.speed

        self.rect.x += dx
        self.rect.x = max(screen_rect.left, min(self.rect.x, screen_rect.right - self.rect.width))

        # Jump
        if (keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vy = -JUMP_SPEED
            self.on_ground = False

        # Gravity and vertical movement
        self.vy += GRAVITY
        self.rect.y += self.vy

        if self.rect.y >= self.ground_y:
            self.rect.y = self.ground_y
            self.vy = 0
            self.on_ground = True
        else:
            self.on_ground = False

        # Parry logic (space only)
        if self.parry_cooldown > 0:
            self.parry_cooldown = max(0, self.parry_cooldown - dt)

        if self.parry_active:
            self.parry_timer = max(0, self.parry_timer - dt)
            if self.parry_timer <= 0:
                self.parry_active = False

        if keys[pygame.K_f] and self.parry_cooldown <= 0 and not self.parry_active:
            self.parry_active = True
            self.parry_timer = PARRY_DURATION
            self.parry_cooldown = PARRY_COOLDOWN
            
        is_moving = keys[pygame.K_LEFT] or keys[pygame.K_a] or keys[pygame.K_RIGHT] or keys[pygame.K_d]

        if self.parry_active:
            self.image = self.image_parry
        elif is_moving:
            self.anim_timer += dt
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0
                self.anim_index = (self.anim_index + 1) % len(self.frames)
            self.image = self.frames[self.anim_index]
        else:
            self.anim_index = 0
            self.anim_timer = 0
            self.image = self.image_idle
        

    def draw(self, surf):
        if self.parry_active:
            glow = pygame.Surface((self.width + 14, self.height + 14), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (120, 200, 255, 140), glow.get_rect())
            surf.blit(glow, (self.rect.x - 7, self.rect.y - 7))
        surf.blit(self.image, self.rect)


class Projectile:
    def __init__(self, screen_rect, speed):
        self.width = 150
        self.height = 150
        self.speed = speed

        # Decide which edge this projectile comes from
        # More likely to come from above, but occasionally from sides/below.
        self.direction = random.choices(
            ["top", "left", "right", "bottom"],
            weights=[80, 8, 8, 4],
            k=1,
        )[0]

        if self.direction == "top":
            self.x = random.randint(screen_rect.left + 16, screen_rect.right - 16 - self.width)
            self.y = screen_rect.top - self.height - 10
            self.vx = 0
            self.vy = self.speed
            self.angle = 0
        elif self.direction == "bottom":
            self.x = random.randint(screen_rect.left + 16, screen_rect.right - 16 - self.width)
            self.y = screen_rect.bottom + 10
            self.vx = 0
            self.vy = -self.speed
            self.angle = 180
        elif self.direction == "left":
            self.x = screen_rect.left - self.width - 10
            self.y = random.randint(screen_rect.top + 16, screen_rect.bottom - 16 - self.height)
            self.vx = self.speed
            self.vy = 0
            self.angle = 90
        else:  # right
            self.x = screen_rect.right + 10
            self.y = random.randint(screen_rect.top + 16, screen_rect.bottom - 16 - self.height)
            self.vx = -self.speed
            self.vy = 0
            self.angle = 270

        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        # Flag to mark when the projectile has entered the visible play area.
        # While False, we show a warning arrow at the screen edge.
        self.entered = False

        self.image = try_load_image("C:/Users/TBL/Documents/GitHub/App-trung-dong/Fiery katana with ethereal aura.png", (self.width, self.height))
        if self.image is None:
            self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.polygon(
                self.image,
                (100, 10, 10),
                [
                    (self.width / 2, 0),
                    (self.width, self.height),
                    (0, self.height),
                ],
            )

    def update(self, screen_rect):
        # Move the projectile in its arrival direction
        self.rect.x += self.vx
        self.rect.y += self.vy

        # Once the projectile enters the screen, it is no longer a warning
        if not self.entered and self.rect.colliderect(screen_rect):
            self.entered = True

    def is_offscreen(self, screen_rect):
        return (
            self.rect.top > screen_rect.bottom + 50
            or self.rect.bottom < screen_rect.top - 50
            or self.rect.left > screen_rect.right + 50
            or self.rect.right < screen_rect.left - 50
        )

    def draw(self, surf):
        rotated = pygame.transform.rotate(self.image, self.angle)
        rect = rotated.get_rect(center=self.rect.center)
        surf.blit(rotated, rect)

class Item:
    def __init__(self, screen_rect):
        self.width = 100
        self.height = 100
        self.rect = pygame.Rect(
            random.randint(100, screen_rect.right - 100),
            screen_rect.bottom - self.height - 150,
            self.width,
            self.height,
        )
        self.image = try_load_image("C:/Users/TBL/Documents/GitHub/App-trung-dong/baogay.png", (self.width, self.height))
        if self.image is None:
            self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.circle(self.image, (255, 220, 0), (self.width//2, self.height//2), self.width//2)
        # Hiệu ứng nháy
        self.blink_timer = 0

    def draw(self, surf):
        self.blink_timer += 1
        if (self.blink_timer // 15) % 2 == 0:
            surf.blit(self.image, self.rect)

def draw_text(surf, text, size, x, y, color=(255, 255, 255)):
    font = pygame.font.SysFont("arial", size, bold=True)
    surf.blit(font.render(text, True, color), (x, y))


def clamp(value, minimum, maximum):
    """Clamp a value between minimum and maximum."""
    return max(minimum, min(value, maximum))


def draw_warning(surf, direction, screen_rect, pos):
    """Draw a warning arrow at the edge of the screen at the given position.

    `pos` is the coordinate along the edge where the projectile will enter.
    - For top/bottom warnings: pos is the x-coordinate
    - For left/right warnings: pos is the y-coordinate
    """
    size = 40
    padding = 30
    color = (255, 200, 80)

    if direction == "top":
        x = clamp(pos, padding + size, screen_rect.right - padding - size)
        pts = [
            (x, padding),
            (x - size, padding + size),
            (x + size, padding + size),
        ]
    elif direction == "bottom":
        x = clamp(pos, padding + size, screen_rect.right - padding - size)
        pts = [
            (x, screen_rect.bottom - padding),
            (x - size, screen_rect.bottom - padding - size),
            (x + size, screen_rect.bottom - padding - size),
        ]
    elif direction == "left":
        y = clamp(pos, padding + size, screen_rect.bottom - padding - size)
        pts = [
            (padding, y),
            (padding + size, y - size),
            (padding + size, y + size),
        ]
    else:  # right
        y = clamp(pos, padding + size, screen_rect.bottom - padding - size)
        pts = [
            (screen_rect.right - padding, y),
            (screen_rect.right - padding - size, y - size),
            (screen_rect.right - padding - size, y + size),
        ]

    pygame.draw.polygon(surf, color, pts)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Ancient China Evade")
    clock = pygame.time.Clock()
    
    # Background
    bg_image = try_load_image("C:/Users/TBL/Documents/GitHub/App-trung-dong/Không-Có-Tiêu-Đề244.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
    if bg_image is None:
        # fallback to a gradient background
        bg_image = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        bg_image.fill((20, 30, 40))
        for i in range(SCREEN_HEIGHT // 3):
            alpha = int(80 * (1 - i / (SCREEN_HEIGHT // 3)))
            overlay = pygame.Surface((SCREEN_WIDTH, 1), pygame.SRCALPHA)
            overlay.fill((80, 50, 20, alpha))
            bg_image.blit(overlay, (0, i))

    screen_rect = screen.get_rect()
    player = Player(screen_rect)

    projectiles = []
    score = 0
    running = True
    game_over = False

    projectile_speed = PROJECTILE_SPEED_START
    spawn_timer = 0
    spawn_interval = PROJECTILE_SPAWN_TIME
    
    item_timer = 0
    current_item = None
    invincible = False
    invincible_timer = 0
    anim_frames = [
        try_load_image(f"C:/Users/TBL/Documents/GitHub/App-trung-dong/Không Có Tiêu Đề48_20260402131904.png", (SCREEN_WIDTH, SCREEN_HEIGHT)),
        try_load_image(f"C:/Users/TBL/Documents/GitHub/App-trung-dong/Không Có Tiêu Đề48_20260402131946.png", (SCREEN_WIDTH, SCREEN_HEIGHT)),
        try_load_image(f"C:/Users/TBL/Documents/GitHub/App-trung-dong/Không Có Tiêu Đề48_20260402131950.png", (SCREEN_WIDTH, SCREEN_HEIGHT)),
        try_load_image(f"C:/Users/TBL/Documents/GitHub/App-trung-dong/Không Có Tiêu Đề48_20260402131954.png", (SCREEN_WIDTH, SCREEN_HEIGHT)),
        try_load_image(f"C:/Users/TBL/Documents/GitHub/App-trung-dong/Không Có Tiêu Đề48_20260402131958.png", (SCREEN_WIDTH, SCREEN_HEIGHT)),
        try_load_image(f"C:/Users/TBL/Documents/GitHub/App-trung-dong/Không Có Tiêu Đề48_20260402132001.png", (SCREEN_WIDTH, SCREEN_HEIGHT)),
        try_load_image(f"C:/Users/TBL/Documents/GitHub/App-trung-dong/Không Có Tiêu Đề48_20260402132004.png", (SCREEN_WIDTH, SCREEN_HEIGHT)),
        try_load_image(f"C:/Users/TBL/Documents/GitHub/App-trung-dong/Không Có Tiêu Đề48_20260402132007.png", (SCREEN_WIDTH, SCREEN_HEIGHT)),
        try_load_image(f"C:/Users/TBL/Documents/GitHub/App-trung-dong/Không Có Tiêu Đề48_20260402132010.png", (SCREEN_WIDTH, SCREEN_HEIGHT)),
    ]
    anim_index = 0
    anim_timer = 0
    playing_anim = False
    
    # Main game loop
    # - process input
    # - update game state (player, projectiles, score)
    # - render the scene
    while running:
        dt = clock.tick(FPS)
        spawn_timer += dt

        if not game_over:
            score += dt / 1000
            projectile_speed += PROJECTILE_ACCELERATION * (dt / 1000)
            # Spawn item
            item_timer += dt
            if item_timer >= ITEM_SPAWN_TIME and current_item is None and not invincible:
                item_timer = 0
                current_item = Item(screen_rect)

            # Bất tử timer
            if invincible:
                invincible_timer -= dt
                anim_timer += dt
                if anim_timer >= ANIM_FRAME_SPEED:
                    anim_timer = 0
                    anim_index = (anim_index + 1) % len(anim_frames)
                if invincible_timer <= 0:
                    invincible = False
                    playing_anim = False

            # Nhặt item
            if current_item and player.rect.colliderect(current_item.rect):
                current_item = None
                invincible = True
                invincible_timer = ITEM_DURATION
                playing_anim = True
                anim_index = 0
                anim_timer = 0
            # Keep spawn timing fixed; difficulty comes only from speed.

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if game_over and event.key == pygame.K_r:
                    # restart
                    projectiles.clear()
                    score = 0
                    projectile_speed = PROJECTILE_SPEED_START
                    spawn_timer = 0
                    game_over = False
                    player.rect.centerx = screen_rect.centerx
                    item_timer = 0         
                    current_item = None    
                    invincible = False     
                    invincible_timer = 0   
                    playing_anim = False   

        keys = pygame.key.get_pressed()
        
        screen.blit(bg_image, (0, 0))
        
        if not game_over:
            player.update(keys, screen_rect, dt)

            if spawn_timer >= spawn_interval:
                spawn_timer = 0
                projectiles.append(Projectile(screen_rect, projectile_speed))
            
            for p in projectiles:
                p.update(screen_rect)

            # remove off-screen projectiles
            projectiles = [p for p in projectiles if not p.is_offscreen(screen_rect)]

            # collision + parry
            for p in projectiles[:]:
                player_center = pygame.Rect(
                    player.rect.centerx - 5,
                    player.rect.centery - 80,
                    10,
                    160
                )
                if p.rect.colliderect(player_center):
                    if player.parry_active or invincible:  # ← thêm invincible
                        projectiles.remove(p)
                        score += 1
                        continue
                    game_over = True
                    break
                
        # indicate incoming threats at the point where they will enter
        for p in projectiles:
            if not p.entered:
                if p.direction in ("top", "bottom"):
                    draw_warning(screen, p.direction, screen_rect, p.rect.centerx)
                else:
                    draw_warning(screen, p.direction, screen_rect, p.rect.centery)

        for p in projectiles:
            p.draw(screen)

        if not playing_anim:
            player.draw(screen)
        
        # Animation toàn màn hình khi bất tử
        if playing_anim and anim_frames[anim_index]:
            screen.blit(anim_frames[anim_index], (0, 0))

        # Vẽ item
        if current_item:
            current_item.draw(screen)

        draw_text(screen, f"Score: {int(score)}", 26, screen_rect.centerx - 60, 10)
        if not game_over:
            if player.parry_cooldown > 0:
                draw_text(screen, f"Parry CD: {int(player.parry_cooldown)}ms", 22, 12, 40)
            else:
                draw_text(screen, "Parry: f", 22, 12, 40)
            draw_text(screen, "Jump: UP / W", 22, 12, 64)

        if game_over:
            draw_text(screen, f"Score: {int(score)}", 36, screen_rect.centerx - 70, screen_rect.centery + 50,(255, 220, 0))
            draw_text(screen, "GAME OVER", 64, screen_rect.centerx - 160, screen_rect.centery - 70, (230, 50, 50))
            draw_text(screen, "Press R to restart", 28, screen_rect.centerx - 110, screen_rect.centery + 10, (240, 240, 240))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

from pygame.locals import *
pygame.init()
screen_width = 1000
screen_height = 1000
screen = pygame.display.set_mode((screen_width,screen_height))
pygame.display.set_caption('ehehhehehh')
title_size = 50
bg_image = pygame.image.load('')

