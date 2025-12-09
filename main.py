import pygame
import math
import random

pygame.init()

# ---------------------------------------
# CONSTANTS
# ---------------------------------------
TILE = 32

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 576   # 18 tiles * 32 px = 576
FPS = 60

PLAYER_SPEED = 2.0
PLAYER_MAX_HEARTS = 5
PLAYER_IFRAME_MS = 800

SWORD_RANGE_PIXELS = 110
SWORD_DAMAGE = 2
SWORD_ARC_DEG = 90
SWORD_SWING_MS = 160

ENEMY_STATS = {
    "spider":   {"hp": 3, "speed": 1.4, "contact_damage": 2},
    "skeleton": {"hp": 5, "speed": 1.1, "contact_damage": 2},
    "ghost":    {"hp": 4, "speed": 0.9, "contact_damage": 1},
    "eye":      {"hp": 4, "speed": 0.8, "contact_damage": 0},
}

FIREBALL_SPEED = 3.0
FIREBALL_DAMAGE = 1
FIREBALL_RANGE = 260
FIREBALL_COOLDOWN_MS = 1200

ROOM_COUNT = 10
FINAL_ROOM_INDEX = ROOM_COUNT - 1

ROOM_W = SCREEN_WIDTH // TILE
ROOM_H = SCREEN_HEIGHT // TILE

# ---------------------------------------
# PYGAME SETUP
# ---------------------------------------
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Dungeon Explorer")
clock = pygame.time.Clock()

pygame.font.init()
title_font = pygame.font.SysFont(None, 72)
info_font = pygame.font.SysFont(None, 32)
hud_font = pygame.font.SysFont(None, 24)

game_state = "title"

# ---------------------------------------
# IMAGE LOADING
# ---------------------------------------
def load_masked(path):
    img = pygame.image.load(path).convert_alpha()
    return img, pygame.mask.from_surface(img)

def load_image(path):
    return pygame.image.load(path).convert_alpha()

player_img, player_mask = load_masked("images/player.png")
floor_img, _ = load_masked("images/floor.png")
wall_img, wall_mask = load_masked("images/wall.png")
library_wall_img, _ = load_masked("images/library.png")

spider_img, spider_mask = load_masked("images/spider.png")
skeleton_img, skeleton_mask = load_masked("images/skeleton.png")
ghost_img, ghost_mask = load_masked("images/ghost.png")
eye_img, eye_mask = load_masked("images/eye.png")

chest_img, chest_mask = load_masked("images/chest.png")
chest_open_img = load_image("images/chest_open.png")

heart_full = load_image("images/heart_full.png")
heart_half = load_image("images/heart_half.png")
heart_empty = load_image("images/heart_empty.png")

apple_img = load_image("images/apple.png")
bread_img = load_image("images/bread.png")
meat_img = load_image("images/meat.png")
chicken_img = load_image("images/chicken.png")

sword_img = load_image("images/sword.png")
fireball_img = load_image("images/fireball.png")

enemy_images = {
    "spider": spider_img,
    "skeleton": skeleton_img,
    "ghost": ghost_img,
    "eye": eye_img,
}
enemy_masks = {
    "spider": spider_mask,
    "skeleton": skeleton_mask,
    "ghost": ghost_mask,
    "eye": eye_mask,
}

ITEM_ORDER = ["apple", "bread", "meat", "chicken"]
item_images = {
    "apple": apple_img,
    "bread": bread_img,
    "meat": meat_img,
    "chicken": chicken_img,
}
item_heal = {"apple": 1, "bread": 2, "meat": 3, "chicken": 4}

# ---------------------------------------
# COLLISION HELPERS
# ---------------------------------------
def pixel_collision(obj, tx, ty, tmask):
    offset = (int(tx - obj.x), int(ty - obj.y))
    return obj.mask.overlap(tmask, offset) is not None

def angle_between(dx, dy):
    return math.degrees(math.atan2(dy, dx))

def angle_diff(a, b):
    return (a - b + 180) % 360 - 180

# ---------------------------------------
# DUNGEON GRAPH
# ---------------------------------------
NEIGHBORS = {
    0: {"N": None, "E": 1, "S": 2, "W": None},
    1: {"N": None, "E": 3, "S": 4, "W": 0},
    2: {"N": 0,    "E": 4, "S": None, "W": None},
    3: {"N": None, "E": None, "S": 6, "W": 1},
    4: {"N": 1,    "E": 7, "S": 5, "W": 2},
    5: {"N": 4,    "E": 8, "S": None, "W": None},
    6: {"N": 3,    "E": None, "S": None, "W": None},
    7: {"N": None, "E": 9, "S": None, "W": 4},
    8: {"N": 5,    "E": None, "S": None, "W": None},
    9: {"N": None, "E": None, "S": None, "W": None},
}

ROOM_CONFIG = {
    i: {
        "theme": "final" if i == 9 else ("library" if i in (3,5) else "normal"),
        "enemy_min": 10 if i == 9 else 8,
        "enemy_max": 12 if i == 9 else 12,
        "enemy_types": ["skeleton", "ghost", "eye"] if i >= 3 else ["spider", "skeleton", "ghost"],
        "no_chests": (i == 9)
    }
    for i in range(ROOM_COUNT)
}

EXTRA_WALLS = {
    0: [],
    1: [(5, 4), (14, 4), (5, 9), (14, 9)],
    2: [(8, 5), (11, 5), (8, 8), (11, 8)],
    3: [(4, 4), (15, 4), (4, 9), (15, 9)],
    4: [(6, 6), (13, 6), (6, 7), (13, 7)],
    5: [(3, 5), (16, 5), (9, 3), (9, 10)],
    6: [(7, 4), (12, 4), (7, 9), (12, 9)],
    7: [(4, 6), (15, 6), (9, 4), (9, 9)],
    8: [(6, 4), (13, 4), (6, 9), (13, 9)],
    9: [(8, 6), (11, 6), (8, 7), (11, 7)],
}

rooms = []
room_themes = []
room_doors = []
room_data = []

# ---------------------------------------
# ROOM GENERATION
# ---------------------------------------
def make_static_room(room_index):
    grid = [[1]*ROOM_W for _ in range(ROOM_H)]

    for y in range(1, ROOM_H-1):
        for x in range(1, ROOM_W-1):
            grid[y][x] = 0

    for (x,y) in EXTRA_WALLS.get(room_index, []):
        if 1 <= x < ROOM_W-1 and 1 <= y < ROOM_H-1:
            grid[y][x] = 1

    mid_x = ROOM_W//2
    mid_y = ROOM_H//2

    doors = {}
    n = NEIGHBORS[room_index]

    if n["N"] is not None:
        grid[0][mid_x-1] = 0
        grid[0][mid_x] = 0
        doors["N"] = pygame.Rect((mid_x-1)*TILE, 0, 2*TILE, TILE)

    if n["S"] is not None:
        grid[ROOM_H-1][mid_x-1] = 0
        grid[ROOM_H-1][mid_x] = 0
        doors["S"] = pygame.Rect((mid_x-1)*TILE, (ROOM_H-1)*TILE, 2*TILE, TILE)

    if n["E"] is not None:
        grid[mid_y-1][ROOM_W-1] = 0
        grid[mid_y][ROOM_W-1] = 0
        doors["E"] = pygame.Rect((ROOM_W-1)*TILE, (mid_y-1)*TILE, TILE, 2*TILE)

    if n["W"] is not None:
        grid[mid_y-1][0] = 0
        grid[mid_y][0] = 0
        doors["W"] = pygame.Rect(0, (mid_y-1)*TILE, TILE, 2*TILE)

    return grid, doors

def list_walls(grid):
    return [(x*TILE, y*TILE)
            for y in range(ROOM_H)
            for x in range(ROOM_W)
            if grid[y][x] == 1]

def random_free(grid, placed):
    while True:
        gx = random.randint(1, ROOM_W-2)
        gy = random.randint(1, ROOM_H-2)
        if grid[gy][gx] == 1:
            continue
        r = pygame.Rect(gx*TILE, gy*TILE, TILE, TILE)
        if any(r.colliderect(p) for p in placed):
            continue
        return gx*TILE, gy*TILE

def generate_static_dungeon():
    rooms.clear()
    room_data.clear()
    room_doors.clear()
    room_themes.clear()

    for i in range(ROOM_COUNT):
        g, d = make_static_room(i)
        rooms.append(g)
        room_doors.append(d)
        room_themes.append(ROOM_CONFIG[i]["theme"])

    for i in range(ROOM_COUNT):
        g = rooms[i]
        cfg = ROOM_CONFIG[i]

        walls = list_walls(g)
        placed = [pygame.Rect(wx, wy, TILE, TILE) for wx, wy in walls]

        enemies = []
        chests = []

        for _ in range(random.randint(cfg["enemy_min"], cfg["enemy_max"])):
            x, y = random_free(g, placed)
            kind = random.choice(cfg["enemy_types"])
            e = Enemy(x, y, kind)
            enemies.append(e)
            placed.append(e.rect)

        if not cfg["no_chests"]:
            for _ in range(random.randint(1,3)):
                x, y = random_free(g, placed)
                items = [random.choice(ITEM_ORDER) for _ in range(random.randint(1,3))]
                c = Chest(x, y, items)
                chests.append(c)
                placed.append(c.rect)

        room_data.append((walls, enemies, chests))

# ---------------------------------------
# ENTITY CLASSES
# ---------------------------------------
class Player:
    def __init__(self):
        self.x = TILE*2
        self.y = TILE*2
        self.speed = PLAYER_SPEED
        self.mask = player_mask
        self.width = player_img.get_width()
        self.height = player_img.get_height()
        self.max_health = PLAYER_MAX_HEARTS*2
        self.health = self.max_health
        self.invuln_until = 0
        self.alive = True
        self.attacking = False
        self.attack_angle = 0
        self.attack_end_time = 0

    @property
    def center(self):
        r = self.rect
        return r.centerx, r.centery

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def move(self, dx, dy, walls, grid):
        if dx==0 and dy==0 or not self.alive:
            return
        l = math.hypot(dx,dy)
        dx/=l
        dy/=l
        ox, oy = self.x, self.y
        self.x += dx*self.speed
        self.y += dy*self.speed

        for wx,wy in walls:
            if pixel_collision(self, wx,wy, wall_mask):
                self.x, self.y = ox, oy
                break

    def start_attack(self, mpos):
        if not self.alive:
            return
        px, py = self.center
        mx, my = mpos
        dx = mx-px
        dy = my-py
        d = math.hypot(dx,dy)
        if d==0 or d>SWORD_RANGE_PIXELS:
            return
        self.attacking = True
        self.attack_angle = angle_between(dx,dy)
        self.attack_end_time = pygame.time.get_ticks()+SWORD_SWING_MS

    def update_attack(self):
        if self.attacking and pygame.time.get_ticks()>=self.attack_end_time:
            self.attacking = False

    def can_hit(self, e):
        if not self.attacking:
            return False
        px, py = self.center
        ex, ey = e.center
        dx = ex-px
        dy = ey-py
        d = math.hypot(dx,dy)
        if d>SWORD_RANGE_PIXELS:
            return False
        diff = abs(angle_diff(angle_between(dx,dy), self.attack_angle))
        return diff<=SWORD_ARC_DEG/2

    def take_damage(self, dmg):
        now = pygame.time.get_ticks()
        if now<self.invuln_until:
            return
        self.health -= dmg
        if self.health<0:
            self.health=0
        self.invuln_until = now+PLAYER_IFRAME_MS
        if self.health==0:
            self.alive=False

    def heal(self, amt):
        self.health = min(self.health+amt, self.max_health)

    def draw(self,s):
        s.blit(player_img, (int(self.x), int(self.y)))
        if self.attacking:
            px,py = self.center
            angle = -self.attack_angle
            rot = pygame.transform.rotate(sword_img, angle)
            rad = math.radians(self.attack_angle)
            ox = px + math.cos(rad)*28 - rot.get_width()/2
            oy = py + math.sin(rad)*28 - rot.get_height()/2
            s.blit(rot, (ox,oy))

class Enemy:
    def __init__(self,x,y,kind):
        self.x=float(x)
        self.y=float(y)
        self.kind=kind
        self.img=enemy_images[kind]
        self.mask=enemy_masks[kind]
        s=ENEMY_STATS[kind]
        self.speed=s["speed"]
        self.hp=s["hp"]
        self.contact_damage=s["contact_damage"]
        self.width=self.img.get_width()
        self.height=self.img.get_height()
        self.next_shot=0

    @property
    def center(self):
        r=self.rect
        return r.centerx, r.centery

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width,self.height)

    def alive(self):
        return self.hp>0

    def take_damage(self,v):
        self.hp-=v

    def update(self,p, walls, grid, projectiles):
        if not self.alive() or not p.alive:
            return
        px,py=p.center
        ex,ey=self.center
        dx=px-ex
        dy=py-ey
        d=math.hypot(dx,dy)
        if d==0:
            return

        if self.kind=="eye":
            minr,maxr=160,260
            mx=my=0
            if d>maxr:
                mx=dx/d
                my=dy/d
            elif d<minr:
                mx=-dx/d
                my=-dy/d
            ox,oy=self.x,self.y
            self.x+=mx*self.speed
            self.y+=my*self.speed

            for wx,wy in walls:
                if pixel_collision(self,wx,wy,wall_mask):
                    self.x,self.y=ox,oy
                    break

            now=pygame.time.get_ticks()
            if d<=FIREBALL_RANGE and now>=self.next_shot:
                self.shoot(px,py,projectiles)
                self.next_shot=now+FIREBALL_COOLDOWN_MS
        else:
            mx=dx/d
            my=dy/d
            ox,oy=self.x,self.y
            self.x+=mx*self.speed
            self.y+=my*self.speed
            if self.kind!="ghost":
                for wx,wy in walls:
                    if pixel_collision(self,wx,wy,wall_mask):
                        self.x,self.y=ox,oy
                        break

    def shoot(self,tx,ty,projectiles):
        ex,ey=self.center
        dx,dy=tx-ex,ty-ey
        d=math.hypot(dx,dy)
        dx/=d
        dy/=d
        projectiles.append(Fireball(ex,ey,dx*FIREBALL_SPEED,dy*FIREBALL_SPEED))

    def draw(self,s):
        if self.alive():
            s.blit(self.img,(int(self.x),int(self.y)))

class Fireball:
    def __init__(self,x,y,vx,vy):
        self.x=x
        self.y=y
        self.vx=vx
        self.vy=vy
        self.r=8
        self.alive=True

    @property
    def rect(self):
        return pygame.Rect(int(self.x)-self.r,int(self.y)-self.r,self.r*2,self.r*2)

    def update(self,grid,player):
        if not self.alive:
            return
        self.x+=self.vx
        self.y+=self.vy
        if not (0<=self.x<=SCREEN_WIDTH and 0<=self.y<=SCREEN_HEIGHT):
            self.alive=False
            return
        gx=int(self.x)//TILE
        gy=int(self.y)//TILE
        if 0<=gx<ROOM_W and 0<=gy<ROOM_H and grid[gy][gx]==1:
            self.alive=False
            return
        if player.alive and self.rect.colliderect(player.rect):
            player.take_damage(FIREBALL_DAMAGE)
            self.alive=False

    def draw(self,s):
        if self.alive:
            s.blit(fireball_img,(int(self.x)-fireball_img.get_width()//2,
                                 int(self.y)-fireball_img.get_height()//2))

class Chest:
    def __init__(self,x,y,items):
        self.x=x
        self.y=y
        self.items=items
        self.open=False
        self.rect=pygame.Rect(x,y,chest_img.get_width(),chest_img.get_height())

    def try_open(self,p_rect,inv):
        if self.open or not p_rect.colliderect(self.rect):
            return
        for it in self.items:
            inv[it]=min(5,inv[it]+1)
        self.open=True

    def draw(self,s):
        s.blit(chest_open_img if self.open else chest_img,(self.x,self.y))


# ---------------------------------------
# GLOBAL GAME STATE
# ---------------------------------------
player=None
current_room=0
projectiles=[]
inventory={}

def reset_run():
    global player, current_room, projectiles, inventory
    generate_static_dungeon()
    player=Player()
    current_room=0
    projectiles=[]
    inventory={n:0 for n in ITEM_ORDER}

# ---------------------------------------
# DRAW HELPERS
# ---------------------------------------
def draw_hearts(s,p):
    x=10;y=10
    sp=heart_full.get_width()+4
    for i in range(p.max_health//2):
        idx=i*2
        if p.health>=idx+2:
            img=heart_full
        elif p.health==idx+1:
            img=heart_half
        else:
            img=heart_empty
        s.blit(img,(x+i*sp,y))

def draw_inventory(s):
    x=SCREEN_WIDTH-10
    y=10
    for i,name in enumerate(ITEM_ORDER):
        img=item_images[name]
        ix=x-img.get_width()
        iy=y+i*26
        s.blit(img,(ix,iy))
        s.blit(hud_font.render(f"x{inventory[name]}",True,(255,255,255)),
               (ix-35,iy+4))

def draw_room(s,i):
    grid=rooms[i]
    theme=room_themes[i]
    tile=library_wall_img if theme=="library" else wall_img
    for y in range(ROOM_H):
        for x in range(ROOM_W):
            px=x*TILE; py=y*TILE
            if grid[y][x]==0:
                s.blit(floor_img,(px,py))
            else:
                s.blit(tile,(px,py))

# ---------------------------------------
# DAMAGE HANDLING
# ---------------------------------------
def handle_melee(p,enemies):
    if not p.alive:
        return
    for e in enemies:
        if e.alive() and e.kind!="eye" and p.rect.colliderect(e.rect):
            p.take_damage(e.contact_damage)

def handle_sword(p,enemies):
    if not p.attacking:
        return
    for e in enemies:
        if e.alive() and p.can_hit(e):
            e.take_damage(SWORD_DAMAGE)

# ---------------------------------------
# ROOM TRANSITIONS (THE FIXED VERSION)
# ---------------------------------------
def try_room_transition():
    global current_room
    r = player.rect
    doors = room_doors[current_room]

    # NORTH (center-based)
    if "N" in doors and r.colliderect(doors["N"]):
        t = NEIGHBORS[current_room]["N"]
        if t is not None:
            current_room = t
            d = room_doors[t]["S"]
            player.x = d.centerx - player.width//2
            player.y = d.top - player.height - 4
        return

    # SOUTH
    if "S" in doors and r.colliderect(doors["S"]):
        t = NEIGHBORS[current_room]["S"]
        if t is not None:
            current_room = t
            d = room_doors[t]["N"]
            player.x = d.centerx - player.width//2
            player.y = d.bottom + 4
        return

    # EAST (NO SCREEN EDGE CHECK — DOOR ONLY)
    if "E" in doors and r.colliderect(doors["E"]):
        t = NEIGHBORS[current_room]["E"]
        if t is not None:
            current_room = t

            if t == FINAL_ROOM_INDEX:
                # guaranteed safe open floor
                player.x = TILE * 3
                player.y = TILE * 3
            else:
                d = room_doors[t]["W"]
                player.x = d.right + 4
                player.y = d.centery - player.height//2
        return

    # WEST (same fix — door only)
    if "W" in doors and r.colliderect(doors["W"]):
        t = NEIGHBORS[current_room]["W"]
        if t is not None:
            current_room = t

            if t == FINAL_ROOM_INDEX:
                player.x = TILE * (ROOM_W-4)
                player.y = TILE * 3
            else:
                d = room_doors[t]["E"]
                player.x = d.left - player.width - 4
                player.y = d.centery - player.height//2
        return

# ---------------------------------------
# MAIN LOOP
# ---------------------------------------
running=True
reset_run()

while running:
    dt = clock.tick(FPS)

    for ev in pygame.event.get():
        if ev.type==pygame.QUIT:
            running=False

        if game_state=="title":
            if ev.type==pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                reset_run()
                game_state="play"

        elif game_state=="play":
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                player.start_attack(pygame.mouse.get_pos())
                _,enemy_set,_ = room_data[current_room]
                handle_sword(player, enemy_set)

            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_1 and inventory["apple"]>0:
                    inventory["apple"]-=1; player.heal(item_heal["apple"])
                if ev.key==pygame.K_2 and inventory["bread"]>0:
                    inventory["bread"]-=1; player.heal(item_heal["bread"])
                if ev.key==pygame.K_3 and inventory["meat"]>0:
                    inventory["meat"]-=1; player.heal(item_heal["meat"])
                if ev.key==pygame.K_4 and inventory["chicken"]>0:
                    inventory["chicken"]-=1; player.heal(item_heal["chicken"])

                if ev.key==pygame.K_e:
                    _,_,chs = room_data[current_room]
                    for c in chs:
                        c.try_open(player.rect, inventory)

        elif game_state in ("gameover","win"):
            if ev.type==pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                reset_run(); game_state="play"

    if game_state=="title":
        screen.fill((0,0,0))
        t = title_font.render("Dungeon Explorer",True,(255,255,255))
        i = info_font.render("Press Enter to Start",True,(200,200,200))
        screen.blit(t,(SCREEN_WIDTH//2-t.get_width()//2, SCREEN_HEIGHT//2-40))
        screen.blit(i,(SCREEN_WIDTH//2-i.get_width()//2, SCREEN_HEIGHT//2+20))
        pygame.display.flip()
        continue

    if game_state=="play":
        keys=pygame.key.get_pressed()
        dx=(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy=(keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])

        walls, enemies, chests = room_data[current_room]

        player.move(dx,dy,walls,rooms[current_room])
        try_room_transition()
        player.update_attack()

        walls, enemies, chests = room_data[current_room]
        for e in enemies:
            e.update(player,walls,rooms[current_room],projectiles)

        enemies[:] = [e for e in enemies if e.alive()]
        handle_melee(player, enemies)

        for fb in projectiles:
            fb.update(rooms[current_room],player)
        projectiles[:] = [fb for fb in projectiles if fb.alive]

        if not player.alive:
            game_state="gameover"

        if current_room==FINAL_ROOM_INDEX and all(not e.alive() for e in enemies):
            game_state="win"

    screen.fill((0,0,0))
    draw_room(screen,current_room)

    walls,enemies,chests = room_data[current_room]
    for c in chests: c.draw(screen)
    for e in enemies: e.draw(screen)
    for fb in projectiles: fb.draw(screen)
    player.draw(screen)

    draw_hearts(screen,player)
    draw_inventory(screen)

    if game_state=="gameover":
        o=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA)
        o.fill((0,0,0,180))
        screen.blit(o,(0,0))
        t=title_font.render("You Died",True,(220,50,50))
        i=info_font.render("Press Enter to Restart",True,(230,230,230))
        screen.blit(t,(SCREEN_WIDTH//2-t.get_width()//2,SCREEN_HEIGHT//2-20))
        screen.blit(i,(SCREEN_WIDTH//2-i.get_width()//2,SCREEN_HEIGHT//2+30))

    if game_state=="win":
        o=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA)
        o.fill((0,0,0,180))
        screen.blit(o,(0,0))
        t=title_font.render("You Win!",True,(50,220,80))
        i=info_font.render("Press Enter to Play Again",True,(230,230,230))
        screen.blit(t,(SCREEN_WIDTH//2-t.get_width()//2,SCREEN_HEIGHT//2-20))
        screen.blit(i,(SCREEN_WIDTH//2-i.get_width()//2,SCREEN_HEIGHT//2+30))

    pygame.display.flip()

pygame.quit()
