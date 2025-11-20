import io
import urllib.request

import os
import math
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
    NPC_DIALOG = auto()
    CODEX = auto()


CONTRACT_OPTION_COUNT = 3
contracts = []
dimensionCodex = {}
codexSelectionIndex = 0
codexScrollOffset = 0
CODEX_VISIBLE_ROWS = 5

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

DIMENSION_THEMES = [
    {
        "key": "aurora_shelf",
        "name": "Aurora Shelf",
        "description": "Frozen freighters channel aurora currents between jumps.",
        "sky_top": (110, 190, 255),
        "sky_bottom": (16, 36, 92),
        "ceiling_color": (70, 120, 200),
        "platform_color": (225, 240, 255),
        "hazard_name": "Ion Tide",
        "hazard_color": (80, 190, 255),
        "glow_color": (150, 220, 255),
        "orb_palette": [(255, 255, 220), (160, 220, 255), (255, 196, 220)],
        "orb_count": 28,
    },
    {
        "key": "ember_wastes",
        "name": "Ember Wastes",
        "description": "Charred mesas belch ember fire beneath courier routes.",
        "sky_top": (255, 170, 90),
        "sky_bottom": (60, 24, 18),
        "ceiling_color": (150, 80, 50),
        "platform_color": (240, 200, 150),
        "hazard_name": "Volcanic Slurry",
        "hazard_color": (220, 70, 32),
        "glow_color": (255, 120, 70),
        "orb_palette": [(255, 200, 90), (220, 120, 80), (255, 255, 180)],
        "orb_count": 20,
    },
    {
        "key": "mist_cascades",
        "name": "Mist Cascades",
        "description": "Waterfalls drift upside down among mossy pylons.",
        "sky_top": (120, 220, 200),
        "sky_bottom": (28, 70, 60),
        "ceiling_color": (60, 150, 120),
        "platform_color": (220, 255, 220),
        "hazard_name": "Mycelium Bloom",
        "hazard_color": (120, 220, 150),
        "glow_color": (90, 200, 160),
        "orb_palette": [(180, 255, 210), (90, 210, 140), (210, 255, 230)],
        "orb_count": 24,
    },
    {
        "key": "obsidian_verge",
        "name": "Obsidian Verge",
        "description": "Blackstone towers scrape storms of magnetized glass.",
        "sky_top": (80, 50, 110),
        "sky_bottom": (12, 8, 20),
        "ceiling_color": (55, 40, 90),
        "platform_color": (200, 180, 255),
        "hazard_name": "Shard Mist",
        "hazard_color": (150, 90, 200),
        "glow_color": (200, 120, 255),
        "orb_palette": [(220, 180, 255), (140, 120, 200), (255, 130, 190)],
        "orb_count": 32,
    },
    {
        "key": "sunken_grotto",
        "name": "Sunken Grotto",
        "description": "Coral ruins hide crosstide delivery gates.",
        "sky_top": (70, 150, 200),
        "sky_bottom": (10, 40, 70),
        "ceiling_color": (40, 90, 140),
        "platform_color": (210, 240, 230),
        "hazard_name": "Brine Surge",
        "hazard_color": (40, 150, 200),
        "glow_color": (100, 200, 220),
        "orb_palette": [(160, 220, 255), (120, 200, 180), (255, 240, 220)],
        "orb_count": 22,
    },
    {
        "key": "prism_belt",
        "name": "Prism Belt",
        "description": "Refraction fields split every shadow.",
        "sky_top": (255, 220, 180),
        "sky_bottom": (40, 30, 50),
        "ceiling_color": (120, 80, 160),
        "platform_color": (255, 255, 255),
        "hazard_name": "Spectral Flux",
        "hazard_color": (180, 80, 255),
        "glow_color": (255, 180, 230),
        "orb_palette": [(255, 200, 230), (200, 220, 255), (255, 250, 180)],
        "orb_count": 36,
    },
]


def pick_dimension_theme():
    return random.choice(DIMENSION_THEMES)


def ensure_codex_entry(theme):
    entry = dimensionCodex.setdefault(
        theme["key"],
        {
            "key": theme["key"],
            "name": theme.get("name", "Unknown"),
            "description": theme.get("description", ""),
            "hazard": theme.get("hazard_name", "Hazard"),
            "times_seen": 0,
            "completions": 0,
            "failures": 0,
            "best_time_ms": None,
            "best_beacons": 0,
        },
    )
    return entry


def register_dimension_discovery(theme):
    entry = ensure_codex_entry(theme)
    entry["times_seen"] += 1
    if entry["times_seen"] == 1:
        push_progress_toast(f"Logged new dimension: {entry['name']}")


def record_codex_completion(theme_key, mission_time_ms, beacons_found, success=True):
    if not theme_key:
        return
    entry = dimensionCodex.get(theme_key)
    if not entry:
        return
    if success:
        entry["completions"] += 1
        if mission_time_ms is not None:
            best = entry.get("best_time_ms")
            if best is None or mission_time_ms < best:
                entry["best_time_ms"] = mission_time_ms
        if beacons_found:
            entry["best_beacons"] = max(entry.get("best_beacons", 0), beacons_found)
    else:
        entry["failures"] += 1


def format_time_ms(ms):
    if ms is None or ms <= 0:
        return "--"
    seconds = ms / 1000.0
    minutes = int(seconds // 60)
    remaining = seconds - minutes * 60
    return f"{minutes:02d}:{remaining:04.1f}s"


def get_codex_entries():
    return sorted(dimensionCodex.values(), key=lambda entry: entry["name"].lower())


POSTAL_RANKS = [
    {"deliveries": 0, "title": "Probation Courier"},
    {"deliveries": 3, "title": "Horizon Runner"},
    {"deliveries": 7, "title": "Nebula Specialist"},
    {"deliveries": 12, "title": "Fracture Lead"},
    {"deliveries": 18, "title": "Constellation Marshal"},
    {"deliveries": 25, "title": "Mythic Dispatcher"},
]

PROGRESSION_MILESTONES = [
    {"deliveries": 1, "type": "message", "text": "First official route logged. Dispatcher noticed."},
    {"deliveries": 3, "type": "pay_bonus", "value": 0.05, "text": "+5% command stipend applied."},
    {"deliveries": 5, "type": "life_bonus", "value": 1, "text": "Support drone adds +1 life to missions."},
    {"deliveries": 8, "type": "cash", "value": 150, "text": "Express bonus: 150 credits wired."},
    {"deliveries": 12, "type": "pay_bonus", "value": 0.08, "text": "Hazard stipend upgraded (+8%)."},
    {"deliveries": 15, "type": "color_unlock", "value": (255, 196, 120), "text": "Awarded Solar Courier suit tint."},
    {"deliveries": 20, "type": "life_bonus", "value": 1, "text": "Emergency drone joins (+1 life)."},
]

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
contractsCompleted = 0
deliveryStreak = 0
bestDeliveryStreak = 0
progressionLifeBonus = 0
progressionPayBonusMultiplier = 1.0
unlockedMilestones = set()

livesRemaining = 0
maxLives = 0
missionPayMultiplier = 1.0
extraLifeBonus = 0
playerColor = (255, 255, 255)
officeDecorStyle = "standard"
ownedUpgrades = {}
shopMessage = "Welcome to the Supply Depot."
codexMessage = "Scan new dimensions to expand this log."

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


def dispatcher_dynamic_lines():
    current_rank, next_rank = get_postal_rank(contractsCompleted)
    lines = [
        f"You're level {playerLevel}. Keep cashing in XP to reach new payouts.",
        f"Rank: {current_rank['title']}  Streak: {deliveryStreak}",
    ]
    if next_rank:
        lines.append(f"{max(0, next_rank['deliveries'] - contractsCompleted)} deliveries away from {next_rank['title']}.")
    if portalActive:
        lines.append("Portal's charged—step through whenever you're prepped.")
    else:
        lines.append("Take a contract from the console so I can spool your gate.")
    return lines


def archivist_dynamic_lines():
    lines = []
    if currentContract:
        lines.append(f"Current manifest: {currentContract['name']} heading to {currentContract.get('environment', 'an unknown field')}.")
    elif contracts:
        lines.append("I've logged three fresh routes on the console.")
    else:
        lines.append("Give me a cycle to scout new routes.")
    if dimensionLoreText:
        lines.append(dimensionLoreText)
    else:
        lines.append("Each dimension paints its own sky—log the colors when you return.")
    lines.append(f"Deliveries logged: {contractsCompleted} (best streak {bestDeliveryStreak}).")
    return lines


npc_characters = []
dispatcher_rect = pygame.Rect(deskRect.right + 70, floorY - 96, 44, 80)
npc_characters.append(
    {
        "key": "dispatcher_rae",
        "name": "Dispatcher Rae",
        "rect": dispatcher_rect,
        "color": (255, 208, 140),
        "accent": (60, 140, 235),
        "lines": [
            "Routes keep shifting; I keep the gate tuned to your sprint.",
            "Tap the console whenever you're ready for a fresh stack of jobs.",
        ],
        "dynamic_lines": dispatcher_dynamic_lines,
    }
)
archivist_rect = pygame.Rect(portalRect.left - 100, floorY - 94, 40, 78)
npc_characters.append(
    {
        "key": "archivist_zell",
        "name": "Archivist Zell",
        "rect": archivist_rect,
        "color": (200, 180, 255),
        "accent": (120, 70, 160),
        "lines": [
            "I chart the storms you hop across. Bring back interesting data.",
            "Talk to me if you want lore on the next dimension.",
        ],
        "dynamic_lines": archivist_dynamic_lines,
    }
)
for npc in npc_characters:
    npc["talk_rect"] = npc["rect"].inflate(90, 30)

activeNpc = None
activeNpcLines = []
activeNpcIndex = 0


def build_npc_dialogue(npc):
    lines = list(npc.get("lines", []))
    dynamic_builder = npc.get("dynamic_lines")
    if callable(dynamic_builder):
        dynamic_lines = dynamic_builder()
        if dynamic_lines:
            lines.extend(dynamic_lines)
    return lines or ["..."]


def open_npc_dialog(npc):
    global activeNpc, activeNpcLines, activeNpcIndex, gameState
    activeNpc = npc
    activeNpcLines = build_npc_dialogue(npc)
    activeNpcIndex = 0
    gameState = GameState.NPC_DIALOG


def advance_npc_dialog():
    global activeNpcIndex
    if not activeNpcLines:
        close_npc_dialog()
        return
    activeNpcIndex += 1
    if activeNpcIndex >= len(activeNpcLines):
        close_npc_dialog()


def close_npc_dialog():
    global activeNpc, activeNpcLines, activeNpcIndex, gameState
    activeNpc = None
    activeNpcLines = []
    activeNpcIndex = 0
    gameState = GameState.HUB

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
levelBeacons = []
beaconsCollected = 0
levelStartTimeMs = 0
levelVerticalBias = 1.0
levelHorizontalBias = 1.0
wallJumpUnlocked = False
wallContactDir = 0
lastWallJumpMs = -10_000
wallJumpCooldownMs = 220
dimensionLoreText = ""

platformRects = []
startPlatformRect = pygame.Rect(0, 0, 0, 0)
endPlatformRect = pygame.Rect(0, 0, 0, 0)
hubSpawnPoint = pygame.Vector2(deskRect.centerx + 20, deskRect.top)
spawnPoint = hubSpawnPoint.copy()

winSummary = {
    "payment": 0,
    "xp": 0,
    "contract": "",
    "moneyTotal": 0,
    "xpTotal": 0,
    "level": 1,
    "deliveries": 0,
    "streak": 0,
    "rank": "Probation Courier",
    "nextRank": None,
    "nextRankDelta": 0,
    "milestones": [],
    "payBonus": 0,
    "beacons": 0,
    "beaconTotal": 0,
    "beaconCash": 0,
    "beaconXp": 0,
    "time": None,
}
gameOverSummary = {"contract": "", "reason": "Out of lives", "streak_note": "", "best": 0}

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


def wrap_text(text, font, max_width):
    if not text:
        return []
    words = text.split()
    lines = []
    current = ""
    for word in words:
        attempt = word if not current else f"{current} {word}"
        if font.size(attempt)[0] <= max_width:
            current = attempt
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def get_postal_rank(deliveries):
    current = POSTAL_RANKS[0]
    next_rank = None
    for rank in POSTAL_RANKS:
        if deliveries >= rank["deliveries"]:
            current = rank
        elif deliveries < rank["deliveries"] and next_rank is None:
            next_rank = rank
            break
    return current, next_rank


PROGRESS_TOAST_DURATION_MS = 5200
progressToasts = []


def push_progress_toast(message):
    expire_at = pygame.time.get_ticks() + PROGRESS_TOAST_DURATION_MS
    progressToasts.append({"text": message, "expires": expire_at})


def apply_progress_milestones():
    global progressionPayBonusMultiplier, progressionLifeBonus, playerMoney, playerColor, unlockedMilestones
    unlocked_messages = []
    for milestone in PROGRESSION_MILESTONES:
        key = milestone["deliveries"]
        if contractsCompleted >= key and key not in unlockedMilestones:
            unlockedMilestones.add(key)
            reward_type = milestone.get("type")
            if reward_type == "pay_bonus":
                progressionPayBonusMultiplier = round(
                    progressionPayBonusMultiplier * (1.0 + float(milestone.get("value", 0.0))), 3
                )
            elif reward_type == "life_bonus":
                progressionLifeBonus += int(milestone.get("value", 0))
            elif reward_type == "cash":
                playerMoney += int(milestone.get("value", 0))
            elif reward_type == "color_unlock":
                playerColor = milestone.get("value", playerColor)
            message = milestone.get("text", "Milestone reached!")
            unlocked_messages.append(message)
            push_progress_toast(message)
        elif contractsCompleted < key:
            continue
    return unlocked_messages


def record_delivery_success():
    global contractsCompleted, deliveryStreak, bestDeliveryStreak
    contractsCompleted += 1
    deliveryStreak += 1
    if deliveryStreak > bestDeliveryStreak:
        bestDeliveryStreak = deliveryStreak
    unlocked = apply_progress_milestones()
    current_rank, next_rank = get_postal_rank(contractsCompleted)
    return unlocked, current_rank, next_rank


def record_delivery_failure(reason="Mission aborted"):
    global deliveryStreak
    note = ""
    if deliveryStreak:
        note = f"Streak reset at {deliveryStreak} deliveries."
        push_progress_toast(note)
    deliveryStreak = 0
    return note or reason


def get_effective_pay_multiplier():
    return missionPayMultiplier * progressionPayBonusMultiplier


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
    theme = pick_dimension_theme()
    theme_context = theme.get("description") or f"Look for landmarks in {theme['name']}."
    if summary:
        description = f"{tagline} — {summary} {theme_context} Expect {hazard_text}."
    else:
        description = f"{tagline} — {theme_context} Expect {hazard_text}."
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
        "theme": theme,
        "theme_key": theme.get("key"),
        "environment": theme["name"],
        "hazard_label": theme.get("hazard_name", hazard_text),
        "theme_context": theme_context,
    }
    return contract


def returnToHub():
    global gameState, portalActive, levelNeedsBuild, gravity, jumpStrength, platformGapMin, platformGapMax, platformWidthMin, platformWidthMax
    global livesRemaining, maxLives, shopSelectionIndex, shopScrollOffset, shopMessage, spawnPoint, lastJumpPressMs, lastGroundedMs, velX, velY, onGround, cameraX, lastJumpHeight, currentContract, contracts, selectedContractIndex
    global levelVerticalBias, levelHorizontalBias, wallJumpUnlocked, wallContactDir, lastWallJumpMs, dimensionLoreText, activeNpc, activeNpcLines, activeNpcIndex
    global levelBeacons, beaconsCollected, levelStartTimeMs
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
    dimensionLoreText = ""
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
    activeNpc = None
    activeNpcLines = []
    activeNpcIndex = 0
    levelBeacons = []
    beaconsCollected = 0
    levelStartTimeMs = 0
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
    progressToasts[:] = [toast for toast in progressToasts if toast["expires"] > now]

    jumpPressedThisFrame = False
    interactPressed = False
    confirmPressed = False
    backPressed = False
    menuUp = False
    menuDown = False
    codexPressed = False

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
            elif event.key == pygame.K_c:
                codexPressed = True

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
                theme = currentContract.get("theme")
                if theme:
                    register_dimension_discovery(theme)
                gravity = currentContract["gravity"]
                jumpStrength = currentContract["jump"]
                platformGapMin = currentContract["gap_min"]
                platformGapMax = currentContract["gap_max"]
                platformWidthMin = currentContract["width_min"]
                platformWidthMax = currentContract["width_max"]
                bonus_lives = extraLifeBonus + progressionLifeBonus
                livesRemaining = max(1, currentContract["lives"] + bonus_lives)
                maxLives = livesRemaining
                levelVerticalBias = currentContract.get("vertical_bias", 1.0)
                levelHorizontalBias = currentContract.get("horizontal_bias", 1.0)
                wallJumpUnlocked = currentContract.get("wall_jump", False)
                wallContactDir = 0
                lastWallJumpMs = -10_000
                dimensionLoreText = currentContract.get("theme_context", "")
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
    elif gameState == GameState.NPC_DIALOG:
        velX = 0.0
        velY = 0.0
        if confirmPressed or interactPressed:
            advance_npc_dialog()
        elif backPressed:
            close_npc_dialog()
    elif gameState == GameState.CODEX:
        velX = 0.0
        velY = 0.0
        entries = get_codex_entries()
        if entries:
            if menuUp:
                codexSelectionIndex = (codexSelectionIndex - 1) % len(entries)
            if menuDown:
                codexSelectionIndex = (codexSelectionIndex + 1) % len(entries)
            max_offset = max(0, len(entries) - CODEX_VISIBLE_ROWS)
            if codexSelectionIndex < codexScrollOffset:
                codexScrollOffset = codexSelectionIndex
            elif codexSelectionIndex >= codexScrollOffset + CODEX_VISIBLE_ROWS:
                codexScrollOffset = min(codexSelectionIndex - CODEX_VISIBLE_ROWS + 1, max_offset)
            codexScrollOffset = max(0, min(codexScrollOffset, max_offset))
        if backPressed or confirmPressed or interactPressed:
            gameState = GameState.HUB
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

            def clamp_channel(v):
                if v < 0:
                    return 0
                if v > 255:
                    return 255
                return v

            hazard_name, hazard_color = random.choice(hazardOptions)
            orb_palette = None
            orb_count = 26
            theme = currentContract.get("theme")
            if theme:
                sky_top_color = theme.get("sky_top", (80, 80, 140))
                sky_bottom_color = theme.get("sky_bottom", (30, 30, 38))
                ceilingColor = theme.get("ceiling_color", sky_top_color)
                platformColor = theme.get("platform_color", (210, 210, 230))
                hazard_name = theme.get("hazard_name", hazard_name)
                hazard_color = theme.get("hazard_color", hazard_color)
                glow_target_color = theme.get("glow_color", hazard_color)
                orb_palette = theme.get("orb_palette")
                orb_count = theme.get("orb_count", orb_count)
            else:
                shift = (dimensionIndex * 18) % 120
                bgColor = (
                    clamp_channel(30 + shift // 2),
                    clamp_channel(30 + shift // 3),
                    clamp_channel(38 + shift // 2),
                )
                ceilingColor = (
                    clamp_channel(60 + shift // 2),
                    clamp_channel(60 + shift // 4),
                    clamp_channel(100 + shift // 2),
                )
                platformColor = (
                    clamp_channel(190 + shift // 3),
                    clamp_channel(200 + shift // 4),
                    clamp_channel(235 + shift // 5),
                )
                glow_target_color = (
                    clamp_channel(hazard_color[0] + 60),
                    clamp_channel(hazard_color[1] + 50),
                    clamp_channel(hazard_color[2] + 40),
                )
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
            floorHazardName = hazard_name
            floorColor = hazard_color
            bgColor = sky_bottom_color
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
            if not theme:
                glow_target_color = (
                    clamp_channel(floorColor[0] + 60),
                    clamp_channel(floorColor[1] + 50),
                    clamp_channel(floorColor[2] + 40),
                )
            # Pre-render sky gradient and parallax glow for a cleaner backdrop.
            levelBackgroundSurface = create_vertical_gradient(screenWidth, screenHeight, sky_top_color, sky_bottom_color)
            if theme:
                accent_alpha = 55
                for _ in range(10):
                    height = random.randint(80, 220)
                    width = random.randint(60, 160)
                    x = random.randint(0, screenWidth)
                    y = random.randint(int(levelSkyTop * 0.6), floorY - 220)
                    accent_color = mix_colors(sky_top_color, glow_target_color, random.uniform(0.2, 0.8))
                    pygame.draw.rect(
                        levelBackgroundSurface,
                        (*accent_color, accent_alpha),
                        pygame.Rect(x, y, width, height),
                        border_radius=18,
                    )
            levelGlowSurface = create_vertical_gradient(screenWidth, 180, sky_top_color, glow_target_color, 0, 170)
            backdropOrbs = []
            # Build a handful of parallax lights to float behind the action.
            orb_total = max(12, int(orb_count))
            for _ in range(orb_total):
                orb_x = random.randint(0, hallLength)
                orb_y = random.randint(int(max(20, levelSkyTop * 0.6)), int(floorY * 0.65))
                radius = random.randint(6, 18)
                tint_amount = random.uniform(0.25, 0.75)
                if orb_palette:
                    palette_color = random.choice(orb_palette)
                    orb_color = mix_colors(palette_color, glow_target_color, tint_amount)
                else:
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
            levelBeacons = []
            beaconsCollected = 0
            candidate_platforms = [plat for plat in platforms[1:-1]]
            random.shuffle(candidate_platforms)
            beacon_target = min(len(candidate_platforms), random.randint(2, 4))
            for idx in range(beacon_target):
                plat = candidate_platforms[idx]
                if plat.width <= 40:
                    continue
                spawn_x = random.randint(plat.left + 20, plat.right - 20)
                spawn_y = plat.top - 18
                beacon_rect = pygame.Rect(spawn_x - 8, spawn_y - 8, 16, 16)
                levelBeacons.append(
                    {
                        "rect": beacon_rect,
                        "pulse": random.uniform(0.2, 1.0),
                        "collected": False,
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
            levelStartTimeMs = pygame.time.get_ticks()

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

        if levelBeacons and gameState == GameState.LEVEL:
            for beacon in levelBeacons:
                if beacon.get("collected"):
                    continue
                if playerRect.colliderect(beacon["rect"].inflate(6, 6)):
                    beacon["collected"] = True
                    beaconsCollected += 1
                    push_progress_toast(
                        f"Beacon {beaconsCollected}/{len(levelBeacons)} secured"
                    )

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
                    failure_note = record_delivery_failure("Ran out of lives")
                    if currentContract:
                        record_codex_completion(currentContract.get("theme_key"), None, beaconsCollected, success=False)
                    if currentContract:
                        gameOverSummary.update(
                            {
                                "contract": currentContract["name"],
                                "reason": "Ran out of lives",
                                "streak_note": failure_note,
                                "best": bestDeliveryStreak,
                            }
                        )
                    else:
                        gameOverSummary.update(
                            {
                                "contract": "Unknown",
                                "reason": "Ran out of lives",
                                "streak_note": failure_note,
                                "best": bestDeliveryStreak,
                            }
                        )
                    print("rip mission lol")
                    portalActive = False
                    currentContract = None
                    levelNeedsBuild = False
                    gameState = GameState.GAME_OVER
                    levelBeacons = []
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
            pay_multiplier = get_effective_pay_multiplier()
            payout = int(round(currentContract["payment"] * pay_multiplier)) if currentContract else 0
            beacon_cash_bonus = beaconsCollected * 30
            beacon_xp_bonus = beaconsCollected * 15
            mission_time_ms = now - levelStartTimeMs if levelStartTimeMs else None
            if currentContract:
                playerMoney += payout + beacon_cash_bonus
                playerXP += currentContract["xp"] + beacon_xp_bonus
                while playerXP >= xpForNextLevel:
                    playerXP -= xpForNextLevel
                    playerLevel += 1
                    xpForNextLevel = max(xpForNextLevel + 80, int(xpForNextLevel * 1.2))
                milestone_messages, rank_info, next_rank = record_delivery_success()
                next_delta = next_rank["deliveries"] - contractsCompleted if next_rank else 0
                pay_bonus_percent = int(round((progressionPayBonusMultiplier - 1.0) * 100))
                record_codex_completion(currentContract.get("theme_key"), mission_time_ms, beaconsCollected, success=True)
                winSummary.update(
                    {
                        "payment": payout + beacon_cash_bonus,
                        "xp": currentContract["xp"] + beacon_xp_bonus,
                        "contract": currentContract["name"],
                        "moneyTotal": playerMoney,
                        "xpTotal": playerXP,
                        "level": playerLevel,
                        "environment": currentContract.get("environment", ""),
                        "hazard": currentContract.get("hazard_label", floorHazardName),
                        "deliveries": contractsCompleted,
                        "streak": deliveryStreak,
                        "rank": rank_info["title"],
                        "nextRank": next_rank["title"] if next_rank else None,
                        "nextRankDelta": next_delta,
                        "milestones": milestone_messages,
                        "payBonus": pay_bonus_percent,
                        "beacons": beaconsCollected,
                        "beaconTotal": len(levelBeacons),
                        "beaconCash": beacon_cash_bonus,
                        "beaconXp": beacon_xp_bonus,
                        "time": mission_time_ms,
                    }
                )
            portalActive = False
            levelNeedsBuild = False
            currentContract = None
            gameState = GameState.WIN
            levelBeacons = []
            print("ez win, next")
            continue

        if gameState == GameState.HUB:
            if playerRect.left < 0:
                playerRect.left = 0
            if playerRect.right > screenWidth:
                playerRect.right = screenWidth
            near_shop = playerRect.colliderect(shopInteractRect)
            near_computer = playerRect.colliderect(computerInteractRect)
            if interactPressed:
                talked = False
                for npc in npc_characters:
                    if playerRect.colliderect(npc["talk_rect"]):
                        open_npc_dialog(npc)
                        talked = True
                        break
                if not talked:
                    if near_shop:
                        shopMessage = "Browse our latest upgrades."
                        max_offset = max(0, len(shopItems) - SHOP_VISIBLE_ROWS)
                        if shopSelectionIndex < shopScrollOffset:
                            shopScrollOffset = shopSelectionIndex
                        elif shopSelectionIndex >= shopScrollOffset + SHOP_VISIBLE_ROWS:
                            shopScrollOffset = max(0, min(shopSelectionIndex - SHOP_VISIBLE_ROWS + 1, max_offset))
                        else:
                            shopScrollOffset = max(0, min(shopScrollOffset, max_offset))
                        gameState = GameState.SHOP
                    elif near_computer:
                        gameState = GameState.CONTRACT_MENU
            elif codexPressed and near_computer:
                entries = get_codex_entries()
                if entries:
                    codexSelectionIndex = max(0, min(codexSelectionIndex, len(entries) - 1))
                else:
                    codexSelectionIndex = 0
                codexScrollOffset = max(0, min(codexScrollOffset, max(0, len(entries) - CODEX_VISIBLE_ROWS)))
                gameState = GameState.CODEX
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
        if levelBeacons:
            time_pulse = pygame.time.get_ticks() / 400.0
            for beacon in levelBeacons:
                if beacon.get("collected"):
                    continue
                rect = beacon["rect"]
                bob = math.sin(time_pulse + beacon["pulse"]) * 3
                draw_x = rect.centerx - cameraX
                draw_y = rect.centery + bob
                pygame.draw.circle(screen, (255, 240, 160), (draw_x, draw_y), 8)
                pygame.draw.circle(screen, (60, 200, 255), (draw_x, draw_y), 13, 2)
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
        comp_hint = smallFont.render("E: Contracts", True, (210, 240, 255))
        screen.blit(comp_hint, (computerBodyRect.left - 8, computerBodyRect.top - 50))
        codex_hint = smallFont.render("C: Codex", True, (190, 220, 255))
        screen.blit(codex_hint, (computerBodyRect.left - 8, computerBodyRect.top - 30))

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

        for npc in npc_characters:
            body_rect = npc["rect"]
            pygame.draw.rect(screen, npc["color"], body_rect, border_radius=6)
            pygame.draw.circle(screen, npc["accent"], (body_rect.centerx, body_rect.top - 12), 16)
            pygame.draw.rect(screen, (25, 25, 38), body_rect.inflate(6, 6), 2, border_radius=8)
            if activeNpc and npc["key"] == activeNpc.get("key"):
                pygame.draw.rect(screen, (255, 245, 180), body_rect.inflate(10, 10), 2, border_radius=10)
            nameSurf = smallFont.render(npc["name"], True, (220, 220, 255))
            screen.blit(nameSurf, (body_rect.centerx - nameSurf.get_width() // 2, body_rect.top - 38))
            if gameState == GameState.HUB and playerRect.colliderect(npc["talk_rect"]):
                prompt = smallFont.render("E - Talk", True, (200, 245, 255))
                screen.blit(prompt, (body_rect.centerx - prompt.get_width() // 2, body_rect.bottom + 6))

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

    current_rank_info, next_rank_info = get_postal_rank(contractsCompleted)
    if gameState == GameState.LEVEL:
        contract_name = currentContract["name"] if currentContract else "Contract"
        base_payment = currentContract["payment"] if currentContract else 0
        payment = int(round(base_payment * get_effective_pay_multiplier()))
        hud_lines = [
            contract_name,
            f"Lives: {livesRemaining}",
            f"Payment: ${payment}",
            f"Hazard: {floorHazardName}",
        ]
        if currentContract:
            envLine = currentContract.get("environment")
            if envLine:
                hud_lines.append(f"Dimension: {envLine}")
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
        if levelBeacons:
            hud_lines.append(f"Beacons: {beaconsCollected}/{len(levelBeacons)}")
        hud_lines.append(f"Deliveries: {contractsCompleted}  Streak: {deliveryStreak}")
        rank_line = f"Rank: {current_rank_info['title']}"
        if next_rank_info:
            rank_line += f"  Next: {max(0, next_rank_info['deliveries'] - contractsCompleted)}"
        hud_lines.append(rank_line)
        perk_line = f"Perks: pay x{get_effective_pay_multiplier():.2f}"
        bonus_lives = extraLifeBonus + progressionLifeBonus
        if bonus_lives > 0:
            perk_line += f"  +{bonus_lives} life(s)"
        hud_lines.append(perk_line)
    elif gameState in (GameState.HUB, GameState.NPC_DIALOG, GameState.CODEX):
        hud_lines = [
            f"Level {playerLevel}    XP: {playerXP}/{xpForNextLevel}",
            f"Money: ${playerMoney}",
            "A/D to move  SPACE to jump",
            "Press E at the computer for contracts",
            "Press C at the computer for codex",
            "Press E at the counter for upgrades",
            "Press E near crew to chat",
            f"Portal: {'ONLINE' if portalActive else 'offline'}",
        ]
        if gameState == GameState.NPC_DIALOG and activeNpc:
            hud_lines.append(f"Chatting with {activeNpc['name']}")
        hud_lines.append(f"Deliveries: {contractsCompleted}  Streak: {deliveryStreak}")
        next_rank_delta = next_rank_info['deliveries'] - contractsCompleted if next_rank_info else 0
        if next_rank_delta > 0:
            hud_lines.append(f"Rank: {current_rank_info['title']}  Next in {next_rank_delta}")
        else:
            hud_lines.append(f"Rank: {current_rank_info['title']}")
        perk_line = f"Perks: pay x{get_effective_pay_multiplier():.2f}"
        bonus_lives = extraLifeBonus + progressionLifeBonus
        if bonus_lives > 0:
            perk_line += f"  +{bonus_lives} life(s)"
        hud_lines.append(perk_line)
    else:
        hud_lines = [
            f"Level {playerLevel}    XP: {playerXP}/{xpForNextLevel}",
            f"Money: ${playerMoney}",
        ]

    for idx, line in enumerate(hud_lines):
        screen.blit(uiFont.render(line, True, (255, 255, 255)), (20, 20 + idx * 24))
    if gameState == GameState.LEVEL and dimensionLoreText:
        lore_lines = wrap_text(dimensionLoreText, smallFont, 360)
        for idx, lore in enumerate(lore_lines[:2]):
            screen.blit(smallFont.render(lore, True, (210, 220, 255)), (20, screenHeight - 60 + idx * 18))
    if progressToasts:
        for idx, toast in enumerate(progressToasts[:3]):
            textSurf = smallFont.render(toast["text"], True, (255, 235, 205))
            bgRect = textSurf.get_rect()
            bgRect.top = 20 + idx * 26
            bgRect.right = screenWidth - 20
            pygame.draw.rect(screen, (30, 32, 52), bgRect.inflate(14, 8), border_radius=8)
            screen.blit(textSurf, (bgRect.x + 7, bgRect.y + 4))

    if gameState == GameState.CONTRACT_MENU:
        panelRect = pygame.Rect(140, 120, screenWidth - 280, screenHeight - 240)
        pygame.draw.rect(screen, (28, 28, 42), panelRect)
        pygame.draw.rect(screen, (180, 180, 210), panelRect, 2)
        title = titleFont.render("Select Contract", True, (245, 245, 255))
        screen.blit(title, (panelRect.x + 20, panelRect.y + 20))
        itemY = panelRect.y + 80
        for idx, contract in enumerate(contracts):
            isSelected = idx == selectedContractIndex
            effectivePay = int(round(contract["payment"] * get_effective_pay_multiplier()))
            nameColor = (255, 255, 255) if isSelected else (200, 200, 220)
            descColor = (190, 190, 210) if isSelected else (120, 120, 150)
            extraColor = (220, 220, 240) if isSelected else (130, 130, 150)
            modifiers = contract.get("modifiers") or []
            envParts = [part for part in (contract.get("environment"), contract.get("hazard_label")) if part]
            blockHeight = 70
            if envParts:
                blockHeight += 16
            if modifiers:
                blockHeight += 18
            if isSelected:
                highlight = pygame.Rect(panelRect.x + 15, itemY - 6, panelRect.width - 30, blockHeight + 12)
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
            info_y = itemY + 42
            screen.blit(extraText, (panelRect.x + 24, info_y))
            env_y = info_y + 18
            if envParts:
                envColor = (170, 220, 255) if isSelected else (115, 145, 185)
                envText = smallFont.render(" · ".join(envParts), True, envColor)
                screen.blit(envText, (panelRect.x + 24, env_y))
            mods_y = env_y + (18 if envParts else 0)
            if modifiers:
                modsColor = (205, 235, 255) if isSelected else (145, 160, 190)
                modsText = smallFont.render(" · ".join(modifiers), True, modsColor)
                screen.blit(modsText, (panelRect.x + 24, mods_y))
            itemY += blockHeight
            itemY += 12
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

    elif gameState == GameState.CODEX:
        panelRect = pygame.Rect(130, 110, screenWidth - 260, screenHeight - 220)
        pygame.draw.rect(screen, (20, 22, 36), panelRect)
        pygame.draw.rect(screen, (170, 190, 230), panelRect, 2, border_radius=10)
        title = titleFont.render("Dimension Codex", True, (235, 240, 255))
        screen.blit(title, (panelRect.x + 24, panelRect.y + 24))
        entries = get_codex_entries()
        if entries:
            listTop = panelRect.y + 90
            rowHeight = 86
            visibleStart = codexScrollOffset
            visibleEnd = min(len(entries), codexScrollOffset + CODEX_VISIBLE_ROWS)
            for idx in range(visibleStart, visibleEnd):
                entry = entries[idx]
                isSelected = idx == codexSelectionIndex
                rowRect = pygame.Rect(panelRect.x + 20, listTop, panelRect.width - 40, rowHeight)
                pygame.draw.rect(screen, (32, 34, 54), rowRect, border_radius=8)
                if isSelected:
                    pygame.draw.rect(screen, (110, 160, 255), rowRect, 2, border_radius=8)
                nameSurf = uiFont.render(entry["name"], True, (235, 235, 255))
                screen.blit(nameSurf, (rowRect.x + 12, rowRect.y + 8))
                descSurf = smallFont.render(entry["description"], True, (195, 205, 230))
                screen.blit(descSurf, (rowRect.x + 12, rowRect.y + 36))
                stats = f"Seen {entry['times_seen']}x | Completions {entry['completions']} | Failures {entry['failures']}"
                statsSurf = smallFont.render(stats, True, (180, 210, 245))
                screen.blit(statsSurf, (rowRect.x + 12, rowRect.y + 58))
                extra = f"Best Time {format_time_ms(entry.get('best_time_ms'))} | Best Beacons {entry.get('best_beacons', 0)}"
                extraSurf = smallFont.render(extra, True, (160, 195, 235))
                screen.blit(extraSurf, (rowRect.x + 12, rowRect.y + 72))
                listTop += rowHeight + 12
            if codexScrollOffset > 0:
                upIndicator = smallFont.render("▲ more", True, (210, 210, 235))
                screen.blit(upIndicator, (panelRect.centerx - upIndicator.get_width() // 2, panelRect.y + 60))
            if visibleEnd < len(entries):
                downIndicator = smallFont.render("▼ more", True, (210, 210, 235))
                screen.blit(downIndicator, (panelRect.centerx - downIndicator.get_width() // 2, panelRect.bottom - 90))
        else:
            message = smallFont.render(codexMessage, True, (210, 220, 240))
            screen.blit(message, (panelRect.x + 30, panelRect.y + 110))
        instructions = smallFont.render("W/S to scroll   •   Enter/E or Esc to close", True, (215, 215, 230))
        screen.blit(instructions, (panelRect.x + 24, panelRect.bottom - 40))

    elif gameState == GameState.NPC_DIALOG and activeNpc:
        panelRect = pygame.Rect(120, screenHeight - 240, screenWidth - 240, 190)
        pygame.draw.rect(screen, (32, 34, 58), panelRect, border_radius=14)
        pygame.draw.rect(screen, (205, 210, 255), panelRect, 2, border_radius=14)
        title_text = f"{activeNpc['name']}  —  {activeNpcIndex + 1}/{max(1, len(activeNpcLines))}"
        titleSurf = uiFont.render(title_text, True, (235, 235, 255))
        screen.blit(titleSurf, (panelRect.x + 20, panelRect.y + 16))
        dialog_line = activeNpcLines[activeNpcIndex] if activeNpcLines else "..."
        wrapped = wrap_text(dialog_line, uiFont, panelRect.width - 40)
        if not wrapped:
            wrapped = [dialog_line]
        for idx, text in enumerate(wrapped[:4]):
            render = uiFont.render(text, True, (215, 225, 255))
            screen.blit(render, (panelRect.x + 20, panelRect.y + 60 + idx * 28))
        prompt = smallFont.render("Enter/E to continue   •   Esc to exit", True, (215, 220, 240))
        screen.blit(prompt, (panelRect.x + 20, panelRect.bottom - 36))

    elif gameState == GameState.WIN:
        panelRect = pygame.Rect(180, 160, screenWidth - 360, screenHeight - 320)
        pygame.draw.rect(screen, (24, 50, 32), panelRect)
        pygame.draw.rect(screen, (90, 200, 120), panelRect, 3)
        title = titleFont.render("Delivery Complete!", True, (200, 255, 210))
        screen.blit(title, (panelRect.centerx - title.get_width() // 2, panelRect.y + 28))
        lines = [
            f"Contract: {winSummary['contract']}",
            f"Zone: {winSummary.get('environment', '???')} | Hazard: {winSummary.get('hazard', '???')}",
            f"Earnings: ${winSummary['payment']}",
            f"XP Gained: {winSummary['xp']}",
            f"Total Funds: ${winSummary['moneyTotal']}",
            f"Level {winSummary['level']}  XP: {playerXP}/{xpForNextLevel}",
            f"Deliveries: {winSummary.get('deliveries', 0)}  Streak: {winSummary.get('streak', 0)}",
        ]
        rank_line = f"Rank: {winSummary.get('rank', 'Courier')}"
        if winSummary.get("nextRank") and winSummary.get("nextRankDelta", 0) > 0:
            rank_line += f"  Next: {winSummary['nextRank']} in {winSummary['nextRankDelta']}"
        lines.append(rank_line)
        pay_bonus = winSummary.get("payBonus", 0)
        if pay_bonus > 0:
            lines.append(f"Reputation bonus: +{pay_bonus}% pay")
        beacon_line = f"Beacons: {winSummary.get('beacons', 0)}/{winSummary.get('beaconTotal', 0)}"
        bonus_cash = winSummary.get("beaconCash", 0)
        bonus_xp = winSummary.get("beaconXp", 0)
        if bonus_cash or bonus_xp:
            beacon_line += f"  (+${bonus_cash} / +{bonus_xp} XP)"
        lines.append(beacon_line)
        mission_time = format_time_ms(winSummary.get("time"))
        lines.append(f"Mission Time: {mission_time}")
        lines.append(f"Best Streak: {bestDeliveryStreak}")
        for msg in (winSummary.get("milestones") or [])[:2]:
            lines.append(f"Milestone: {msg}")
        lines.append("Press Enter/E to return to the office.")
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
            f"Best Streak: {gameOverSummary.get('best', 0)}",
        ]
        note = gameOverSummary.get("streak_note")
        if note:
            lines.append(note)
        lines.append("Press Enter/E to return to the office.")
        for idx, text in enumerate(lines):
            render = uiFont.render(text, True, (255, 220, 220))
            screen.blit(render, (panelRect.x + 30, panelRect.y + 120 + idx * 32))

    pygame.display.flip()
