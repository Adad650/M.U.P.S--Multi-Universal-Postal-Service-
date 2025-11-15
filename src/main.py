import io
import urllib.request

import os
import pygame, sys, random
from enum import Enum, auto

pygame.init()
screenWidth, screenHeight = 800, 600
screen = pygame.display.set_mode((screenWidth, screenHeight))
pygame.display.set_caption("M.U.P.S — Loading Dimension")
clock = pygame.time.Clock()
uiFont = pygame.font.Font(None, 28)
titleFont = pygame.font.Font(None, 48)
smallFont = pygame.font.Font(None, 22)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PLAYER_SPRITE_CDN = (
    "https://hc-cdn.hel1.your-objectstorage.com/s/v3/"
    "7c71df3b1e06cbc3381153d807734c44a07b9a91_postman_walk_pixel_sheet.png"
)
PLAYER_SPRITE_FRAME_COUNT = 16
PLAYER_SPRITE_SCALE = 0.7
PLAYER_ANIM_FRAME_TIME = 90
PLAYER_SPRINT_MULTIPLIER = 1.7


def _slice_frames(sheet):
    frame_width = sheet.get_width() // PLAYER_SPRITE_FRAME_COUNT
    frame_height = sheet.get_height()
    draw_width = max(1, int(round(frame_width * PLAYER_SPRITE_SCALE)))
    draw_height = max(1, int(round(frame_height * PLAYER_SPRITE_SCALE)))
    scale_x = draw_width / frame_width
    frames = []
    offsets = []
    for frame_index in range(PLAYER_SPRITE_FRAME_COUNT):
        frame_surface = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
        frame_surface.blit(
            sheet,
            (0, 0),
            pygame.Rect(frame_index * frame_width, 0, frame_width, frame_height),
        )
        bbox = frame_surface.get_bounding_rect()
        offset_center = 0.0
        if bbox.width and bbox.height:
            art_center = bbox.x + bbox.width / 2
            offset_center = art_center - (frame_width / 2)
        offsets.append(int(round(offset_center * scale_x)))
        scaled = pygame.transform.scale(frame_surface, (draw_width, draw_height))
        frames.append(scaled)
    return frames, offsets


def _load_sheet_from_url(url):
    try:
        with urllib.request.urlopen(url, timeout=6) as response:
            data = response.read()
        return pygame.image.load(io.BytesIO(data)).convert_alpha()
    except Exception:
        return None


def _load_sheet_from_local():
    path = os.path.join(BASE_DIR, "assets", "walking", "postman_walk_pixel_sheet.png")
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        return None


def load_player_walk_frames():
    sheet = _load_sheet_from_url(PLAYER_SPRITE_CDN)
    if sheet is None:
        sheet = _load_sheet_from_local()
    if sheet is None:
        return [], []
    return _slice_frames(sheet)


player_walk_frames_right, player_walk_offsets_right = load_player_walk_frames()
player_walk_frames_left = [
    pygame.transform.flip(frame, True, False) for frame in player_walk_frames_right
]
player_walk_offsets_left = [-offset for offset in player_walk_offsets_right]
player_anim_index = 0
player_anim_timer = 0
player_facing = 1

roofHeight = 0
floorY = 520
hallLength = 4000
platformWidthMin = 140
platformWidthMax = 240
platformGapMin = 70
platformGapMax = 160
platformThickness = 18
spawnBuffer = 240
doorClearBuffer = 320
playerSpeed = 5
jumpStrength = 9.0
gravity = 0.6
minCeilRoom = 60
minFloorRoom = 80
lastJumpHeight = (jumpStrength * jumpStrength) / (2.0 * max(1e-6, abs(gravity)))


class GameState(Enum):
    HUB = auto()
    CONTRACT_MENU = auto()
    SHOP = auto()
    LEVEL = auto()
    WIN = auto()
    GAME_OVER = auto()


CONTRACT_OPTION_COUNT = 3
contracts = []

shopItems = [
    {"key": "premium_routes", "name": "Premium Routes License", "description": "+20% contract payouts.", "cost": 250, "type": "mission_bonus", "value": 1.2, "max_stacks": 1},
    {"key": "extra_life", "name": "Auxiliary Drone", "description": "+1 life on every mission.", "cost": 200, "type": "extra_life", "value": 1, "max_stacks": 1},
    {"key": "color_mint", "name": "Suit Paint - Neon Mint", "description": "Fresh mint glow for your suit.", "cost": 120, "type": "player_color", "value": (120, 255, 200), "max_stacks": 1},
    {"key": "color_violet", "name": "Suit Paint - Royal Violet", "description": "Stand out with deep royal hues.", "cost": 120, "type": "player_color", "value": (190, 120, 255), "max_stacks": 1},
    {"key": "decor_plant", "name": "Office Hanging Planter", "description": "Adds greenery to the office.", "cost": 90, "type": "decor", "value": "plant", "max_stacks": 1},
    {"key": "decor_poster", "name": "Skyline Poster", "description": "Add a skyline view to the wall.", "cost": 110, "type": "decor", "value": "poster", "max_stacks": 1},
]

namePrefixes = ["Aurora", "Nova", "Echo", "Titan", "Quantum", "Lumen", "Vortex", "Atlas", "Stellar", "Gale", "Eclipse", "Oracle"]
nameSuffixes = ["Run", "Circuit", "Relay", "Shift", "Route", "Track", "Dash", "Spiral", "Passage", "Traverse", "Vector", "Expedition"]
hazardDescriptors = ["charged dust lanes", "volatile thermal vents", "graviton storms", "magnetic shear pockets", "nebula acid rain", "rogue drone fields", "unstable warp echoes", "fractured bridgework"]
difficultyScale = [(0.45, "Routine Route"), (0.7, "Risky Run"), (0.95, "Hazard Sweep"), (1.2, "Critical Gauntlet"), (10.0, "Impossible Route")]
CONTRACT_TIER_ORDER = ["easy", "medium", "hard"]
CONTRACT_ARCHETYPES = [
    {
        "key": "courier_cruise",
        "tier": "easy",
        "tagline": "Courier Cruise",
        "summary": "Training loop with generous landing pads.",
        "difficulty_range": (0.35, 0.5),
        "gap_mul": (0.75, 0.9),
        "width_mul": (1.2, 1.35),
        "life_bonus": 1,
        "gravity_offset": -0.02,
        "traits": ["+1 support drone", "Wide landing pads"],
    },
    {
        "key": "express_dash",
        "tier": "medium",
        "tagline": "Express Relay",
        "summary": "Rush contracts with long sprints and bonus pay.",
        "difficulty_range": (0.55, 0.85),
        "gap_mul": (1.05, 1.2),
        "width_mul": (0.9, 1.0),
        "horizontal_bias": 1.25,
        "payout_bonus": 0.15,
        "traits": ["+15% payout", "Long sprint sections"],
    },
    {
        "key": "precision_shift",
        "tier": "medium",
        "tagline": "Precision Shift",
        "summary": "Compact pads that reward careful jumps.",
        "difficulty_range": (0.65, 0.95),
        "gap_mul": (1.0, 1.15),
        "width_mul": (0.75, 0.9),
        "xp_bonus": 0.15,
        "traits": ["Compact pads", "+15% XP bounty"],
    },
    {
        "key": "spireline_gauntlet",
        "tier": "hard",
        "tagline": "Spireline Contract",
        "summary": "Vertical shafts carved between floating towers.",
        "difficulty_range": (0.9, 1.2),
        "gap_mul": (0.95, 1.05),
        "width_mul": (0.8, 0.9),
        "vertical_bias": 1.35,
        "wall_jump": True,
        "traits": ["Wall-jump thrusters online", "Vertical shaft routing"],
    },
    {
        "key": "hazard_sweep",
        "tier": "hard",
        "tagline": "Hazard Sweep",
        "summary": "Toxic fields with premium payout for precision.",
        "difficulty_range": (1.0, 1.3),
        "gap_mul": (1.2, 1.35),
        "width_mul": (0.65, 0.8),
        "gravity_offset": 0.04,
        "life_bonus": -1,
        "payout_bonus": 0.25,
        "xp_bonus": 0.1,
        "traits": ["Tiny pads", "+25% hazard pay", "-1 drone"],
    },
]

gameState = GameState.HUB
portalActive = False
levelNeedsBuild = False
currentContract = None
selectedContractIndex = 0
shopSelectionIndex = 0
shopScrollOffset = 0
SHOP_VISIBLE_ROWS = 4

playerLevel = 1
playerXP = 0
playerMoney = 0
xpForNextLevel = 120

livesRemaining = 0
maxLives = 0
missionPayMultiplier = 1.0
extraLifeBonus = 0
playerColor = (255, 255, 255)
officeDecorStyle = "standard"
ownedUpgrades = {}
shopMessage = "Welcome to the Supply Depot."

doorWidth, doorHeight = 52, 150
doorColor = (60, 200, 90)
doorRect = pygame.Rect(0, 0, doorWidth, doorHeight)
portalRect = pygame.Rect(screenWidth - 180, floorY - 160, 90, 160)
portalInactiveColor = (80, 80, 120)
portalActiveColor = (120, 220, 200)
deskRect = pygame.Rect(60, floorY - 40, 200, 40)
computerBodyRect = pygame.Rect(deskRect.left + 40, deskRect.top - 50, 80, 50)
computerScreenColor = (40, 180, 110)
computerInteractRect = computerBodyRect.inflate(80, 80)
hubBackgroundColor = (26, 26, 32)
hubCeilingColor = (44, 44, 66)
hubFloorColor = (60, 60, 90)
shopCounterRect = pygame.Rect(screenWidth // 2 - 90, floorY - 40, 180, 40)
shopInteractRect = shopCounterRect.inflate(80, 80)

playerRect = pygame.Rect(100, 500, 30, 30)
velX = 0.0
velY = 0.0
onGround = False
lastGroundedMs = -10_000
lastJumpPressMs = -10_000
cameraX = 0
dimensionIndex = 0

platformColor = (210, 210, 230)
hazardOptions = [("ACID", (80, 200, 80)), ("LAVA", (220, 60, 40))]
bgColor = (30, 30, 38)
ceilingColor = (60, 60, 100)
floorColor = (70, 55, 40)
floorHazardName = "ACID"
levelSkyTop = 80
levelBackgroundSurface = None
levelGlowSurface = None
backdropOrbs = []
levelVerticalBias = 1.0
levelHorizontalBias = 1.0
wallJumpUnlocked = False
wallContactDir = 0
lastWallJumpMs = -10_000
wallJumpCooldownMs = 220

platformRects = []
startPlatformRect = pygame.Rect(0, 0, 0, 0)
endPlatformRect = pygame.Rect(0, 0, 0, 0)
hubSpawnPoint = pygame.Vector2(deskRect.centerx + 20, deskRect.top)
spawnPoint = hubSpawnPoint.copy()

winSummary = {"payment": 0, "xp": 0, "contract": "", "moneyTotal": 0, "xpTotal": 0, "level": 1}
gameOverSummary = {"contract": "", "reason": "Out of lives"}

jumpBufferMs = 140
coyoteTimeMs = 120


def mix_colors(color_a, color_b, t):
    return tuple(int(color_a[i] + (color_b[i] - color_a[i]) * t) for i in range(3))


def create_vertical_gradient(width, height, top_color, bottom_color, top_alpha=255, bottom_alpha=255):
    height = max(1, int(height))
    surface = pygame.Surface((int(width), height), pygame.SRCALPHA)
    if height == 1:
        color = (*top_color, int(top_alpha))
        surface.fill(color)
        return surface.convert_alpha()
    for y in range(height):
        t = y / (height - 1)
        color = mix_colors(top_color, bottom_color, t)
        alpha = int(top_alpha + (bottom_alpha - top_alpha) * t)
        surface.fill((*color, alpha), rect=pygame.Rect(0, y, width, 1))
    return surface.convert_alpha()


def _clampf(value, low, high):
    return max(low, min(high, value))


def _sample_range(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, (list, tuple)):
        if not value:
            return fallback
        if len(value) == 1:
            return value[0]
        return random.uniform(value[0], value[1])
    return value


def pick_contract_profiles(count):
    selected = []
    used_keys = set()
    for tier in CONTRACT_TIER_ORDER:
        if len(selected) >= count:
            break
        options = [arch for arch in CONTRACT_ARCHETYPES if arch["tier"] == tier and arch["key"] not in used_keys]
        if not options:
            continue
        choice = random.choice(options)
        selected.append(choice)
        used_keys.add(choice["key"])
    remaining_needed = count - len(selected)
    remaining_pool = [arch for arch in CONTRACT_ARCHETYPES if arch["key"] not in used_keys]
    random.shuffle(remaining_pool)
    while remaining_needed > 0 and remaining_pool:
        choice = remaining_pool.pop()
        selected.append(choice)
        used_keys.add(choice["key"])
        remaining_needed -= 1
    while len(selected) < count:
        selected.append(random.choice(CONTRACT_ARCHETYPES))
    random.shuffle(selected)
    return selected[:count]


def build_contract_from_archetype(archetype):
    diff_range = archetype.get("difficulty_range", (0.35, 1.05))
    if isinstance(diff_range, (list, tuple)) and len(diff_range) == 2:
        base_diff = random.uniform(diff_range[0], diff_range[1])
    else:
        base_diff = random.uniform(0.35, 1.05)
    gravity_val = round(
        _clampf(
            0.45 + base_diff * 0.35 + random.uniform(-0.02, 0.02) + float(archetype.get("gravity_offset", 0.0)),
            0.45,
            0.9,
        ),
        3,
    )
    target_jump_height = random.uniform(220 - base_diff * 60, 320 - base_diff * 20)
    target_jump_height = max(160, target_jump_height)
    jump_strength = round((target_jump_height * 2 * gravity_val) ** 0.5, 3)
    gap_min_val = int(round(60 + base_diff * 55 + random.uniform(-8, 8)))
    gap_min_val = max(50, gap_min_val)
    gap_spread = int(round(50 + base_diff * 80 + random.uniform(-12, 12)))
    gap_max_val = gap_min_val + max(30, gap_spread)
    gap_mul = float(_sample_range(archetype.get("gap_mul"), 1.0))
    gap_min_val = int(round(gap_min_val * gap_mul))
    gap_max_val = int(round(gap_max_val * gap_mul))
    gap_min_val = max(40, gap_min_val)
    gap_max_val = max(gap_min_val + 20, gap_max_val)
    width_max_val = int(round(260 - base_diff * 110 + random.uniform(-12, 12)))
    width_max_val = max(140, width_max_val)
    width_min_val = width_max_val - int(round(40 + base_diff * 45))
    width_min_val = max(80, width_min_val)
    width_mul = float(_sample_range(archetype.get("width_mul"), 1.0))
    width_min_val = int(round(width_min_val * width_mul))
    width_max_val = int(round(width_max_val * width_mul))
    if width_min_val >= width_max_val:
        width_min_val = max(70, width_max_val - 20)
    base_lives = max(2, 5 - int(base_diff * 3 + random.random()))
    base_lives += int(archetype.get("life_bonus", 0))
    base_lives = max(1, base_lives)
    difficulty_score = base_diff
    difficulty_score += max(0, (gap_min_val - 70) / 140)
    difficulty_score += max(0, (200 - width_max_val) / 200)
    difficulty_score += (5 - base_lives) * 0.08
    difficulty_score = _clampf(difficulty_score, 0.35, 1.6)
    payment = int(round(140 + difficulty_score * 340 + random.uniform(-10, 10)))
    xp_reward = int(round(80 + difficulty_score * 240))
    payout_bonus = float(archetype.get("payout_bonus", 0.0))
    xp_bonus = float(archetype.get("xp_bonus", 0.0))
    if payout_bonus:
        payment = int(round(payment * (1.0 + payout_bonus)))
    if xp_bonus:
        xp_reward = int(round(xp_reward * (1.0 + xp_bonus)))
    label = "Unknown Route"
    for threshold, tag in difficultyScale:
        if difficulty_score <= threshold:
            label = tag
            break
    hazard_text = random.choice(hazardDescriptors)
    tagline = archetype.get("tagline", label)
    summary = archetype.get("summary", "")
    if summary:
        description = f"{tagline} — {summary} {label} through {hazard_text}."
    else:
        description = f"{tagline} — {label} through {hazard_text}."
    traits = list(archetype.get("traits", ()))
    contract = {
        "name": f"{random.choice(namePrefixes)} {random.choice(nameSuffixes)}",
        "description": description,
        "payment": payment,
        "xp": xp_reward,
        "gravity": gravity_val,
        "jump": jump_strength,
        "gap_min": gap_min_val,
        "gap_max": gap_max_val,
        "width_min": width_min_val,
        "width_max": width_max_val,
        "lives": base_lives,
        "difficulty": round(difficulty_score, 2),
        "label": label,
        "modifiers": traits,
        "archetype": archetype.get("key", "unknown"),
        "vertical_bias": float(_sample_range(archetype.get("vertical_bias"), 1.0)),
        "horizontal_bias": float(_sample_range(archetype.get("horizontal_bias"), 1.0)),
        "wall_jump": bool(archetype.get("wall_jump", False)),
    }
    return contract


def returnToHub():
    global gameState, portalActive, levelNeedsBuild, gravity, jumpStrength, platformGapMin, platformGapMax, platformWidthMin, platformWidthMax
    global livesRemaining, maxLives, shopSelectionIndex, shopScrollOffset, shopMessage, spawnPoint, lastJumpPressMs, lastGroundedMs, velX, velY, onGround, cameraX, lastJumpHeight, currentContract, contracts, selectedContractIndex
    global levelVerticalBias, levelHorizontalBias, wallJumpUnlocked, wallContactDir, lastWallJumpMs
    contracts.clear()
    for archetype in pick_contract_profiles(CONTRACT_OPTION_COUNT):
        contracts.append(build_contract_from_archetype(archetype))
    selectedContractIndex = 0
    if len(contracts) > 1 and random.random() > 0.4:
        random.shuffle(contracts)
    levelVerticalBias = 1.0
    levelHorizontalBias = 1.0
    wallJumpUnlocked = False
    wallContactDir = 0
    lastWallJumpMs = -10_000
    spawnPoint.update(hubSpawnPoint.x, hubSpawnPoint.y)
    livesRemaining = 0
    maxLives = 0
    portalActive = False
    if portalActive:
        portalActive = False
    levelNeedsBuild = False
    gravity = 0.6
    jumpStrength = 9.0
    platformGapMin = 70
    platformGapMax = 160
    platformWidthMin = 140
    platformWidthMax = 240
    shopSelectionIndex = 0
    shopScrollOffset = 0
    shopMessage = "Welcome back to the Supply Depot."
    shopMessage = shopMessage
    gameState = GameState.HUB
    currentContract = None
    lastJumpHeight = (jumpStrength * jumpStrength) / (2.0 * max(1e-6, abs(gravity)))
    playerRect.midbottom = (spawnPoint.x, spawnPoint.y)
    velX = 0.0
    velY = 0.0
    onGround = True
    now = pygame.time.get_ticks()
    lastGroundedMs = now
    lastJumpPressMs = -10_000
    cameraX = 0


returnToHub()

while True:
    dt = clock.tick(60)
    now = pygame.time.get_ticks()

    jumpPressedThisFrame = False
    interactPressed = False
    confirmPressed = False
    backPressed = False
    menuUp = False
    menuDown = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                jumpPressedThisFrame = True
                lastJumpPressMs = now
            elif event.key == pygame.K_e:
                interactPressed = True
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                confirmPressed = True
            elif event.key == pygame.K_ESCAPE:
                backPressed = True
            elif event.key in (pygame.K_UP, pygame.K_w):
                menuUp = True
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                menuDown = True

    keys = pygame.key.get_pressed()

    if gameState == GameState.CONTRACT_MENU:
        if contracts:
            if menuUp:
                selectedContractIndex = (selectedContractIndex - 1) % len(contracts)
            if menuDown:
                selectedContractIndex = (selectedContractIndex + 1) % len(contracts)
            if confirmPressed or interactPressed:
                currentContract = dict(contracts[selectedContractIndex])
                contracts[selectedContractIndex] = currentContract
                gravity = currentContract["gravity"]
                jumpStrength = currentContract["jump"]
                platformGapMin = currentContract["gap_min"]
                platformGapMax = currentContract["gap_max"]
                platformWidthMin = currentContract["width_min"]
                platformWidthMax = currentContract["width_max"]
                livesRemaining = max(1, currentContract["lives"] + extraLifeBonus)
                maxLives = livesRemaining
                levelVerticalBias = currentContract.get("vertical_bias", 1.0)
                levelHorizontalBias = currentContract.get("horizontal_bias", 1.0)
                wallJumpUnlocked = currentContract.get("wall_jump", False)
                wallContactDir = 0
                lastWallJumpMs = -10_000
                portalActive = True
                levelNeedsBuild = True
                lastJumpHeight = (jumpStrength * jumpStrength) / (2.0 * max(1e-6, abs(gravity)))
                print("ok fine we're doing", currentContract["name"])
                gameState = GameState.HUB
        if backPressed:
            gameState = GameState.HUB
        velX = 0.0
        velY = 0.0
        onGround = True
        cameraX = 0
    elif gameState == GameState.SHOP:
        if menuUp:
            shopSelectionIndex = (shopSelectionIndex - 1) % len(shopItems)
        if menuDown:
            shopSelectionIndex = (shopSelectionIndex + 1) % len(shopItems)
        if menuUp or menuDown:
            if shopSelectionIndex < shopScrollOffset:
                shopScrollOffset = shopSelectionIndex
            elif shopSelectionIndex >= shopScrollOffset + SHOP_VISIBLE_ROWS:
                shopScrollOffset = shopSelectionIndex - SHOP_VISIBLE_ROWS + 1
            max_offset = max(0, len(shopItems) - SHOP_VISIBLE_ROWS)
            shopScrollOffset = max(0, min(shopScrollOffset, max_offset))
        if confirmPressed or interactPressed:
            item = shopItems[shopSelectionIndex]
            key = item["key"]
            stacks = ownedUpgrades.get(key, 0)
            maxStacks = item.get("max_stacks", 1)
            if stacks >= maxStacks:
                shopMessage = "Already owned."
            elif playerMoney < item["cost"]:
                shopMessage = "Insufficient funds."
            else:
                playerMoney -= item["cost"]
                if item["type"] == "mission_bonus":
                    missionPayMultiplier = round(missionPayMultiplier * item["value"], 2)
                    shopMessage = "Mission payouts increased!"
                elif item["type"] == "extra_life":
                    extraLifeBonus += int(item["value"])
                    shopMessage = "Received additional mission life."
                elif item["type"] == "player_color":
                    playerColor = item["value"]
                    shopMessage = "Suit color updated."
                elif item["type"] == "decor":
                    officeDecorStyle = item["value"]
                    shopMessage = "Office decor refreshed."
                else:
                    shopMessage = "Upgrade applied."
                ownedUpgrades[key] = stacks + 1
                print("bought", item["name"])
        if backPressed:
            shopMessage = "Come again soon."
            gameState = GameState.HUB
        velX = 0.0
        velY = 0.0
        onGround = True
        cameraX = 0
    elif gameState == GameState.WIN:
        if confirmPressed or interactPressed or backPressed:
            returnToHub()
        velX = 0.0
        velY = 0.0
    elif gameState == GameState.GAME_OVER:
        if confirmPressed or interactPressed or backPressed:
            returnToHub()
        velX = 0.0
        velY = 0.0
    else:
        if gameState == GameState.LEVEL and levelNeedsBuild and currentContract is not None:
            dimensionIndex += 1
            shift = (dimensionIndex * 18) % 120

            def clamp_channel(v):
                if v < 0:
                    return 0
                if v > 255:
                    return 255
                return v

            bgColor = (clamp_channel(30 + shift // 2), clamp_channel(30 + shift // 3), clamp_channel(38 + shift // 2))
            ceilingColor = (clamp_channel(60 + shift // 2), clamp_channel(60 + shift // 4), clamp_channel(100 + shift // 2))
            hazard_name, hazard_color = random.choice(hazardOptions)
            floorHazardName = hazard_name
            floorColor = hazard_color
            platformColor = (
                clamp_channel(190 + shift // 3),
                clamp_channel(200 + shift // 4),
                clamp_channel(235 + shift // 5),
            )
            jumpHeight = (jumpStrength * jumpStrength) / (2.0 * max(1e-6, abs(gravity)))
            lastJumpHeight = jumpHeight
            min_corridor = minCeilRoom + minFloorRoom + 180
            base_corridor = min_corridor + int(jumpHeight * 0.6)
            variation = max(24, int(jumpHeight * 0.35))
            corridor_height = base_corridor + random.randint(-variation, variation)
            if corridor_height < min_corridor:
                corridor_height = min_corridor
            if corridor_height > floorY - 80:
                corridor_height = floorY - 80
            levelSkyTop = max(40, floorY - corridor_height)
            roofHeight = 0
            sky_top_color = (
                clamp_channel(ceilingColor[0] + 40),
                clamp_channel(ceilingColor[1] + 30),
                clamp_channel(ceilingColor[2] + 60),
            )
            sky_bottom_color = (
                clamp_channel(bgColor[0] - 12),
                clamp_channel(bgColor[1] - 6),
                clamp_channel(bgColor[2] + 40),
            )
            glow_target_color = (
                clamp_channel(floorColor[0] + 60),
                clamp_channel(floorColor[1] + 50),
                clamp_channel(floorColor[2] + 40),
            )
            # Pre-render sky gradient and parallax glow for a cleaner backdrop.
            levelBackgroundSurface = create_vertical_gradient(screenWidth, screenHeight, sky_top_color, sky_bottom_color)
            levelGlowSurface = create_vertical_gradient(screenWidth, 180, sky_top_color, glow_target_color, 0, 170)
            backdropOrbs = []
            # Build a handful of parallax lights to float behind the action.
            for _ in range(24):
                orb_x = random.randint(0, hallLength)
                orb_y = random.randint(int(max(20, levelSkyTop * 0.6)), int(floorY * 0.65))
                radius = random.randint(6, 18)
                tint_amount = random.uniform(0.25, 0.75)
                orb_color = mix_colors(sky_top_color, glow_target_color, tint_amount)
                orb_alpha = int(random.uniform(120, 210))
                orb_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(orb_surface, (*orb_color, orb_alpha), (radius, radius), radius)
                backdropOrbs.append(
                    {
                        "x": orb_x,
                        "y": orb_y,
                        "radius": radius,
                        "parallax": random.uniform(0.18, 0.42),
                        "surface": orb_surface.convert_alpha(),
                    }
                )
            vertical_step = max(28, int(jumpHeight * 0.6 * levelVerticalBias))
            horizontal_step = max(
                platformGapMin,
                min(platformGapMax, int(jumpHeight * 1.2 * levelHorizontalBias)),
            )
            start_y = floorY - minFloorRoom - 40
            min_platform_y = max(100, levelSkyTop + minCeilRoom)
            max_platform_y = floorY - minFloorRoom
            door_start = hallLength - doorClearBuffer
            start_platform = pygame.Rect(60, start_y, 220, platformThickness)
            platforms = [start_platform]
            current_x = start_platform.right + random.randint(platformGapMin, horizontal_step)
            current_y = start_platform.y
            while current_x < door_start - platformWidthMin - platformGapMin:
                width = random.randint(platformWidthMin, platformWidthMax)
                current_y += random.randint(-vertical_step, vertical_step)
                if current_y < min_platform_y:
                    current_y = min_platform_y
                if current_y > max_platform_y:
                    current_y = max_platform_y
                platforms.append(pygame.Rect(current_x, current_y, width, platformThickness))
                current_x += width + random.randint(platformGapMin, horizontal_step)
            end_width = max(200, platformWidthMax)
            end_x = max(door_start - end_width - 40, current_x - 80)
            end_y = max(min_platform_y, min(current_y, max_platform_y))
            end_platform = pygame.Rect(end_x, end_y, end_width, platformThickness)
            platforms.append(end_platform)
            platformRects = platforms
            startPlatformRect = start_platform
            endPlatformRect = end_platform
            door_left = max(endPlatformRect.centerx - doorWidth // 2, endPlatformRect.left + 10)
            if door_left > endPlatformRect.right - doorWidth - 10:
                door_left = endPlatformRect.right - doorWidth - 10
            door_top_desired = endPlatformRect.top - doorHeight
            min_door_top = max(80, levelSkyTop + 20)
            door_top = door_top_desired if door_top_desired > min_door_top else min_door_top
            door_height_actual = max(60, endPlatformRect.top - door_top)
            doorRect.update(door_left, door_top, doorWidth, door_height_actual)
            spawnPoint.update(startPlatformRect.centerx, startPlatformRect.top)
            playerRect.midbottom = (spawnPoint.x, spawnPoint.y)
            velX = 0.0
            velY = 0.0
            onGround = True
            lastGroundedMs = pygame.time.get_ticks()
            lastJumpPressMs = -10_000
            cameraX = 0
            pygame.display.set_caption(f"M.U.P.S — Dimension {dimensionIndex + 1}")
            levelNeedsBuild = False

        sprint_active = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        move_speed = playerSpeed * (PLAYER_SPRINT_MULTIPLIER if sprint_active else 1)
        left = keys[pygame.K_a]
        right = keys[pygame.K_d]
        if left and not right:
            velX = -move_speed
        elif right and not left:
            velX = move_speed
        else:
            velX = 0
        velY += gravity

        solids = platformRects if gameState == GameState.LEVEL else []
        playerRect.x += int(velX)
        if solids:
            collided_horizontally = False
            if velX != 0:
                for solid in solids:
                    if playerRect.colliderect(solid):
                        if velX > 0:
                            playerRect.right = solid.left
                            wallContactDir = 1
                            collided_horizontally = True
                        elif velX < 0:
                            playerRect.left = solid.right
                            wallContactDir = -1
                            collided_horizontally = True
            if not collided_horizontally:
                contact_dir = 0
                for solid in solids:
                    if solid.top < playerRect.bottom and solid.bottom > playerRect.top:
                        if playerRect.right == solid.left:
                            contact_dir = 1
                            break
                        if playerRect.left == solid.right:
                            contact_dir = -1
                            break
                wallContactDir = contact_dir
        else:
            wallContactDir = 0

        playerRect.y += int(velY)
        groundedNow = False
        if solids:
            for solid in solids:
                if playerRect.colliderect(solid):
                    if velY > 0:
                        playerRect.bottom = solid.top
                        velY = 0
                        groundedNow = True
                    elif velY < 0:
                        playerRect.top = solid.bottom
                        velY = 0

        if playerRect.bottom >= floorY:
            if gameState == GameState.LEVEL:
                livesRemaining = max(0, livesRemaining - 1)
                playerRect.midbottom = (spawnPoint.x, spawnPoint.y)
                velX = 0.0
                velY = 0.0
                onGround = True
                lastGroundedMs = now
                lastJumpPressMs = -10_000
                cameraX = 0
                if livesRemaining <= 0:
                    if currentContract:
                        gameOverSummary.update({"contract": currentContract["name"], "reason": "Ran out of lives"})
                    else:
                        gameOverSummary.update({"contract": "Unknown", "reason": "Ran out of lives"})
                    print("rip mission lol")
                    portalActive = False
                    currentContract = None
                    levelNeedsBuild = False
                    gameState = GameState.GAME_OVER
                continue
            playerRect.bottom = floorY
            if velY > 0:
                velY = 0
            groundedNow = True

        if groundedNow:
            lastGroundedMs = now
        onGround = groundedNow

        pressedRecently = (now - lastJumpPressMs) <= jumpBufferMs
        hasCoyote = (now - lastGroundedMs) <= coyoteTimeMs
        wantsJump = jumpPressedThisFrame or pressedRecently
        canWallJump = (
            wantsJump
            and wallJumpUnlocked
            and wallContactDir != 0
            and not onGround
            and gameState == GameState.LEVEL
            and (now - lastWallJumpMs) >= wallJumpCooldownMs
        )
        if canWallJump:
            velY = -jumpStrength
            lastWallJumpMs = now
            onGround = False
            lastJumpPressMs = -10_000
            push = -wallContactDir * 6
            if push != 0:
                playerRect.x += push
                if solids:
                    for solid in solids:
                        if playerRect.colliderect(solid):
                            if push > 0:
                                playerRect.right = solid.left
                            else:
                                playerRect.left = solid.right
            wallContactDir = 0
            lastGroundedMs = now - coyoteTimeMs - 5
        elif wantsJump and (onGround or hasCoyote):
            velY = -jumpStrength
            onGround = False
            lastJumpPressMs = -10_000

        if gameState == GameState.LEVEL and playerRect.colliderect(doorRect):
            payout = int(round(currentContract["payment"] * missionPayMultiplier)) if currentContract else 0
            if currentContract:
                playerMoney += payout
                playerXP += currentContract["xp"]
                while playerXP >= xpForNextLevel:
                    playerXP -= xpForNextLevel
                    playerLevel += 1
                    xpForNextLevel = max(xpForNextLevel + 80, int(xpForNextLevel * 1.2))
                winSummary.update(
                    {
                        "payment": payout,
                        "xp": currentContract["xp"],
                        "contract": currentContract["name"],
                        "moneyTotal": playerMoney,
                        "xpTotal": playerXP,
                        "level": playerLevel,
                    }
                )
            portalActive = False
            levelNeedsBuild = False
            currentContract = None
            gameState = GameState.WIN
            print("ez win, next")
            continue

        if gameState == GameState.HUB:
            if playerRect.left < 0:
                playerRect.left = 0
            if playerRect.right > screenWidth:
                playerRect.right = screenWidth
            if interactPressed:
                if playerRect.colliderect(shopInteractRect):
                    shopMessage = "Browse our latest upgrades."
                    max_offset = max(0, len(shopItems) - SHOP_VISIBLE_ROWS)
                    if shopSelectionIndex < shopScrollOffset:
                        shopScrollOffset = shopSelectionIndex
                    elif shopSelectionIndex >= shopScrollOffset + SHOP_VISIBLE_ROWS:
                        shopScrollOffset = max(0, min(shopSelectionIndex - SHOP_VISIBLE_ROWS + 1, max_offset))
                    else:
                        shopScrollOffset = max(0, min(shopScrollOffset, max_offset))
                    gameState = GameState.SHOP
                elif playerRect.colliderect(computerInteractRect):
                    gameState = GameState.CONTRACT_MENU
            if portalActive and playerRect.colliderect(portalRect):
                gameState = GameState.LEVEL
                levelNeedsBuild = True
        else:
            if playerRect.left < 0:
                playerRect.left = 0
            if playerRect.right > hallLength:
                playerRect.right = hallLength

        cameraX = 0 if gameState != GameState.LEVEL else max(0, min(playerRect.centerx - screenWidth // 2, hallLength - screenWidth))

    is_walking = abs(velX) > 0.1
    if velX > 0:
        player_facing = 1
    elif velX < 0:
        player_facing = -1

    if player_walk_frames_right:
        if is_walking:
            player_anim_timer += dt
            frame_count = len(player_walk_frames_right)
            if player_anim_timer >= PLAYER_ANIM_FRAME_TIME:
                player_anim_timer %= PLAYER_ANIM_FRAME_TIME
                player_anim_index = (player_anim_index + 1) % frame_count
        else:
            player_anim_index = 0
            player_anim_timer = 0

    if gameState == GameState.LEVEL:
        if levelBackgroundSurface:
            screen.blit(levelBackgroundSurface, (0, 0))
        else:
            screen.fill(bgColor)
        if backdropOrbs:
            for orb in backdropOrbs:
                draw_x = orb["x"] - cameraX * orb["parallax"] - orb["radius"]
                if draw_x > screenWidth or draw_x < -orb["radius"] * 2:
                    continue
                draw_y = orb["y"] - orb["radius"]
                screen.blit(orb["surface"], (draw_x, draw_y))
        pygame.draw.rect(screen, floorColor, (-cameraX, floorY, hallLength, screenHeight - floorY))
        if levelGlowSurface:
            glow_y = floorY - levelGlowSurface.get_height()
            screen.blit(levelGlowSurface, (0, glow_y))
        for plat in platformRects:
            pygame.draw.rect(screen, platformColor, (plat.x - cameraX, plat.y, plat.width, plat.height))
        pygame.draw.rect(screen, doorColor, (doorRect.x - cameraX, doorRect.y, doorRect.width, doorRect.height))
    else:
        screen.fill(hubBackgroundColor)
        pygame.draw.rect(screen, hubCeilingColor, (0, 0, screenWidth, 160))
        pygame.draw.rect(screen, hubFloorColor, (0, floorY, screenWidth, screenHeight - floorY))

        tableColor = (110, 90, 120)
        legWidth = 16
        pygame.draw.rect(screen, tableColor, deskRect)
        pygame.draw.rect(screen, tableColor, (deskRect.left + 8, deskRect.bottom, legWidth, 50))
        pygame.draw.rect(screen, tableColor, (deskRect.right - legWidth - 8, deskRect.bottom, legWidth, 50))
        pygame.draw.rect(screen, (15, 15, 20), computerBodyRect)
        screenRect = computerBodyRect.inflate(-14, -18)
        pygame.draw.rect(screen, computerScreenColor, screenRect)
        keyboardRect = pygame.Rect(computerBodyRect.left - 20, computerBodyRect.bottom, computerBodyRect.width + 40, 14)
        pygame.draw.rect(screen, (160, 160, 175), keyboardRect)

        counterColor = (90, 100, 150)
        pygame.draw.rect(screen, counterColor, shopCounterRect)
        pygame.draw.rect(screen, counterColor, (shopCounterRect.left + 10, shopCounterRect.bottom, 16, 46))
        pygame.draw.rect(screen, counterColor, (shopCounterRect.right - 26, shopCounterRect.bottom, 16, 46))
        sign = uiFont.render("Shop", True, (230, 230, 255))
        signPos = (shopCounterRect.centerx - sign.get_width() // 2, shopCounterRect.y - 32)
        pygame.draw.rect(screen, (32, 32, 48), (signPos[0], signPos[1], sign.get_width() + 16, sign.get_height() + 8))
        screen.blit(sign, (signPos[0] + 8, signPos[1] + 4))

        portalColor = portalActiveColor if portalActive else portalInactiveColor
        pygame.draw.rect(screen, (40, 40, 60), portalRect.inflate(12, 12))
        pygame.draw.rect(screen, portalColor, portalRect)
        pygame.draw.rect(screen, (255, 255, 255), portalRect.inflate(-40, -120), 2)

        if officeDecorStyle == "plant":
            plantPot = pygame.Rect(deskRect.right + 20, deskRect.top - 24, 20, 24)
            pygame.draw.rect(screen, (120, 70, 40), plantPot)
            pygame.draw.circle(screen, (80, 200, 90), (plantPot.centerx, plantPot.top - 10), 18)
        elif officeDecorStyle == "poster":
            posterRect = pygame.Rect(screenWidth - 260, 60, 140, 90)
            pygame.draw.rect(screen, (30, 45, 80), posterRect)
            pygame.draw.rect(screen, (190, 210, 255), posterRect.inflate(-12, -12))
            pygame.draw.line(screen, (60, 90, 150), posterRect.midbottom, (posterRect.centerx, posterRect.top + 10), 2)

    if player_walk_frames_right:
        sprites = player_walk_frames_right if player_facing >= 0 else player_walk_frames_left
        offsets = player_walk_offsets_right if player_facing >= 0 else player_walk_offsets_left
        frame_index = player_anim_index % len(sprites) if sprites else 0
        sprite = sprites[frame_index]
        offset_x = offsets[frame_index] if offsets else 0
        sprite_x = playerRect.centerx - cameraX - sprite.get_width() // 2 - offset_x
        sprite_y = playerRect.bottom - sprite.get_height()
        screen.blit(sprite, (sprite_x, sprite_y))
    else:
        playerDrawRect = pygame.Rect(playerRect.x - cameraX, playerRect.y, playerRect.width, playerRect.height)
        pygame.draw.rect(screen, playerColor, playerDrawRect)

    if gameState == GameState.LEVEL:
        contract_name = currentContract["name"] if currentContract else "Contract"
        base_payment = currentContract["payment"] if currentContract else 0
        payment = int(round(base_payment * missionPayMultiplier))
        hud_lines = [
            contract_name,
            f"Lives: {livesRemaining}",
            f"Payment: ${payment}",
            f"Hazard: {floorHazardName}",
        ]
        if currentContract:
            modifiers = currentContract.get("modifiers") or []
            if modifiers:
                summary = " · ".join(modifiers[:2])
                if len(modifiers) > 2:
                    summary += " · ..."
                hud_lines.append(f"Mods: {summary}")
            if currentContract.get("wall_jump"):
                hud_lines.append("Ability: Wall jump thrusters online")
        hud_lines.extend(
            [
                f"Jump Height: {int(lastJumpHeight)} px",
                f"XP: {playerXP}/{xpForNextLevel} (Lv {playerLevel})",
            ]
        )
    elif gameState == GameState.HUB:
        hud_lines = [
            f"Level {playerLevel}    XP: {playerXP}/{xpForNextLevel}",
            f"Money: ${playerMoney}",
            "A/D to move  SPACE to jump",
            "Press E at the computer for contracts",
            "Press E at the counter for upgrades",
            f"Portal: {'ONLINE' if portalActive else 'offline'}",
        ]
    else:
        hud_lines = [
            f"Level {playerLevel}    XP: {playerXP}/{xpForNextLevel}",
            f"Money: ${playerMoney}",
        ]

    for idx, line in enumerate(hud_lines):
        screen.blit(uiFont.render(line, True, (255, 255, 255)), (20, 20 + idx * 24))

    if gameState == GameState.CONTRACT_MENU:
        panelRect = pygame.Rect(140, 120, screenWidth - 280, screenHeight - 240)
        pygame.draw.rect(screen, (28, 28, 42), panelRect)
        pygame.draw.rect(screen, (180, 180, 210), panelRect, 2)
        title = titleFont.render("Select Contract", True, (245, 245, 255))
        screen.blit(title, (panelRect.x + 20, panelRect.y + 20))
        itemY = panelRect.y + 80
        for idx, contract in enumerate(contracts):
            isSelected = idx == selectedContractIndex
            effectivePay = int(round(contract["payment"] * missionPayMultiplier))
            nameColor = (255, 255, 255) if isSelected else (200, 200, 220)
            descColor = (190, 190, 210) if isSelected else (120, 120, 150)
            extraColor = (220, 220, 240) if isSelected else (130, 130, 150)
            modifiers = contract.get("modifiers") or []
            blockHeight = 60 + (18 if modifiers else 0)
            if isSelected:
                highlight = pygame.Rect(panelRect.x + 15, itemY - 6, panelRect.width - 30, blockHeight + 20)
                pygame.draw.rect(screen, (70, 90, 140), highlight, border_radius=6)
            nameText = uiFont.render(f"{contract['name']} — ${effectivePay}", True, nameColor)
            screen.blit(nameText, (panelRect.x + 24, itemY))
            descText = uiFont.render(contract["description"], True, descColor)
            screen.blit(descText, (panelRect.x + 24, itemY + 22))
            extraText = uiFont.render(
                f"XP {contract['xp']} | Lives {contract['lives']} | {contract['label']} ({contract['difficulty']:.2f})",
                True,
                extraColor,
            )
            screen.blit(extraText, (panelRect.x + 24, itemY + 42))
            if modifiers:
                modsColor = (205, 235, 255) if isSelected else (145, 160, 190)
                modsText = smallFont.render(" · ".join(modifiers), True, modsColor)
                screen.blit(modsText, (panelRect.x + 24, itemY + 62))
                itemY += 78
            else:
                itemY += 66
            itemY += 10
        instructions = uiFont.render("Enter/E to accept • Esc to cancel • W/S to navigate", True, (230, 230, 240))
        screen.blit(instructions, (panelRect.x + 20, panelRect.bottom - 40))

    elif gameState == GameState.SHOP:
        panelRect = pygame.Rect(120, 110, screenWidth - 240, screenHeight - 220)
        pygame.draw.rect(screen, (30, 26, 42), panelRect)
        pygame.draw.rect(screen, (186, 190, 220), panelRect, 2, border_radius=10)
        title = titleFont.render("Supply Depot", True, (245, 245, 255))
        screen.blit(title, (panelRect.x + 28, panelRect.y + 24))

        fundsText = uiFont.render(f"Credits: ${playerMoney}", True, (220, 220, 255))
        screen.blit(fundsText, (panelRect.x + panelRect.width - fundsText.get_width() - 28, panelRect.y + 30))

        listTop = panelRect.y + 100
        rowHeight = 68
        visibleStart = shopScrollOffset
        visibleEnd = min(len(shopItems), shopScrollOffset + SHOP_VISIBLE_ROWS)
        for idx in range(visibleStart, visibleEnd):
            item = shopItems[idx]
            ownedTimes = ownedUpgrades.get(item["key"], 0)
            maxStacks = item.get("max_stacks", 1)
            available = ownedTimes < maxStacks
            isSelected = idx == shopSelectionIndex

            rowRect = pygame.Rect(panelRect.x + 24, listTop - 6, panelRect.width - 48, rowHeight - 12)
            baseColor = (48, 44, 68) if idx % 2 == 0 else (54, 50, 74)
            pygame.draw.rect(screen, baseColor, rowRect, border_radius=10)
            if isSelected:
                pygame.draw.rect(screen, (140, 120, 200), rowRect, 3, border_radius=10)

            titleColor = (255, 255, 255) if available else (160, 155, 170)
            descColor = (200, 200, 215)
            statusColor = (200, 235, 255) if available else (255, 150, 150)

            nameSurf = uiFont.render(item["name"], True, titleColor)
            screen.blit(nameSurf, (rowRect.x + 16, rowRect.y + 10))

            costSurf = uiFont.render(f"${item['cost']}", True, statusColor if available else (200, 140, 160))
            screen.blit(costSurf, (rowRect.right - costSurf.get_width() - 16, rowRect.y + 10))

            detailParts = [item["description"]]
            if maxStacks > 1:
                detailParts.append(f"{ownedTimes}/{maxStacks} owned")
            elif ownedTimes:
                detailParts.append("already owned")
            detailText = " · ".join(detailParts)
            descSurf = smallFont.render(detailText, True, descColor)
            screen.blit(descSurf, (rowRect.x + 16, rowRect.y + 36))

            status = "Press Enter to purchase" if (available and isSelected) else ("Owned" if ownedTimes else "Available")
            statusSurf = smallFont.render(status, True, statusColor)
            screen.blit(statusSurf, (rowRect.right - statusSurf.get_width() - 16, rowRect.y + 38))

            listTop += rowHeight

        if shopScrollOffset > 0:
            upIndicator = smallFont.render("▲ more", True, (210, 210, 235))
            screen.blit(upIndicator, (panelRect.centerx - upIndicator.get_width() // 2, panelRect.y + 72))
        if visibleEnd < len(shopItems):
            downIndicator = smallFont.render("▼ more", True, (210, 210, 235))
            screen.blit(downIndicator, (panelRect.centerx - downIndicator.get_width() // 2, panelRect.bottom - 120))

        infoBarRect = pygame.Rect(panelRect.x + 24, panelRect.bottom - 70, panelRect.width - 48, 48)
        pygame.draw.rect(screen, (44, 40, 62), infoBarRect, border_radius=10)
        pygame.draw.rect(screen, (96, 94, 140), infoBarRect, 1, border_radius=10)
        instructions = smallFont.render("Enter/E to purchase   •   Esc to exit   •   W/S to browse", True, (215, 215, 235))
        screen.blit(instructions, (infoBarRect.x + 12, infoBarRect.y + 8))
        messageText = smallFont.render(shopMessage, True, (200, 220, 255))
        screen.blit(messageText, (infoBarRect.x + 12, infoBarRect.y + 24))

    elif gameState == GameState.WIN:
        panelRect = pygame.Rect(180, 160, screenWidth - 360, screenHeight - 320)
        pygame.draw.rect(screen, (24, 50, 32), panelRect)
        pygame.draw.rect(screen, (90, 200, 120), panelRect, 3)
        title = titleFont.render("Delivery Complete!", True, (200, 255, 210))
        screen.blit(title, (panelRect.centerx - title.get_width() // 2, panelRect.y + 28))
        lines = [
            f"Contract: {winSummary['contract']}",
            f"Earnings: ${winSummary['payment']}",
            f"XP Gained: {winSummary['xp']}",
            f"Total Funds: ${winSummary['moneyTotal']}",
            f"Level {winSummary['level']}  XP: {playerXP}/{xpForNextLevel}",
            "Press Enter/E to return to the office.",
        ]
        for idx, text in enumerate(lines):
            render = uiFont.render(text, True, (220, 255, 230))
            screen.blit(render, (panelRect.x + 30, panelRect.y + 110 + idx * 30))

    elif gameState == GameState.GAME_OVER:
        panelRect = pygame.Rect(180, 160, screenWidth - 360, screenHeight - 320)
        pygame.draw.rect(screen, (60, 25, 25), panelRect)
        pygame.draw.rect(screen, (200, 80, 80), panelRect, 3)
        title = titleFont.render("Mission Failed", True, (255, 210, 210))
        screen.blit(title, (panelRect.centerx - title.get_width() // 2, panelRect.y + 28))
        lines = [
            f"Contract: {gameOverSummary['contract']}",
            f"Reason: {gameOverSummary['reason']}",
            "Press Enter/E to return to the office.",
        ]
        for idx, text in enumerate(lines):
            render = uiFont.render(text, True, (255, 220, 220))
            screen.blit(render, (panelRect.x + 30, panelRect.y + 120 + idx * 32))

    pygame.display.flip()
