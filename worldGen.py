import pygame, sys, random
from enum import Enum, auto

# =========================
# Setup
# =========================
pygame.init()
screenWidth, screenHeight = 800, 600
screen = pygame.display.set_mode((screenWidth, screenHeight))
pygame.display.set_caption("M.U.P.S — Loading Dimension")
clock = pygame.time.Clock()
uiFont = pygame.font.Font(None, 28)
titleFont = pygame.font.Font(None, 48)
smallFont = pygame.font.Font(None, 22)

# =========================
# World parameters
# =========================
roofHeight = 380
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

# =========================
# Progression / contracts
# =========================
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
    {
        "key": "premium_routes",
        "name": "Premium Routes License",
        "description": "+20% contract payouts.",
        "cost": 250,
        "type": "mission_bonus",
        "value": 1.2,
        "max_stacks": 1,
    },
    {
        "key": "extra_life",
        "name": "Auxiliary Drone",
        "description": "+1 life on every mission.",
        "cost": 200,
        "type": "extra_life",
        "value": 1,
        "max_stacks": 1,
    },
    {
        "key": "color_mint",
        "name": "Suit Paint - Neon Mint",
        "description": "Fresh mint glow for your suit.",
        "cost": 120,
        "type": "player_color",
        "value": (120, 255, 200),
        "max_stacks": 1,
    },
    {
        "key": "color_violet",
        "name": "Suit Paint - Royal Violet",
        "description": "Stand out with deep royal hues.",
        "cost": 120,
        "type": "player_color",
        "value": (190, 120, 255),
        "max_stacks": 1,
    },
    {
        "key": "decor_plant",
        "name": "Office Hanging Planter",
        "description": "Adds greenery to the office.",
        "cost": 90,
        "type": "decor",
        "value": "plant",
        "max_stacks": 1,
    },
    {
        "key": "decor_poster",
        "name": "Skyline Poster",
        "description": "Add a skyline view to the wall.",
        "cost": 110,
        "type": "decor",
        "value": "poster",
        "max_stacks": 1,
    },
]

namePrefixes = [
    "Aurora", "Nova", "Echo", "Titan", "Quantum", "Lumen",
    "Vortex", "Atlas", "Stellar", "Gale", "Eclipse", "Oracle"
]
nameSuffixes = [
    "Run", "Circuit", "Relay", "Shift", "Route", "Track",
    "Dash", "Spiral", "Passage", "Traverse", "Vector", "Expedition"
]
hazardDescriptors = [
    "charged dust lanes",
    "volatile thermal vents",
    "graviton storms",
    "magnetic shear pockets",
    "nebula acid rain",
    "rogue drone fields",
    "unstable warp echoes",
    "fractured bridgework",
]
difficultyScale = [
    (0.45, "Routine Route"),
    (0.7, "Risky Run"),
    (0.95, "Hazard Sweep"),
    (1.2, "Critical Gauntlet"),
    (10.0, "Impossible Route"),
]

def pickDifficultyLabel(score):
    for threshold, label in difficultyScale:
        if score <= threshold:
            return label
    return "Unknown Route"


def generateContract():
    base_diff = random.uniform(0.35, 1.05)
    gravity_val = round(min(max(0.45 + base_diff * 0.35 + random.uniform(-0.02, 0.02), 0.45), 0.85), 3)

    target_jump_height = random.uniform(220 - base_diff * 60, 320 - base_diff * 20)
    target_jump_height = max(160, target_jump_height)
    jump_strength = round((target_jump_height * 2 * gravity_val) ** 0.5, 3)

    gap_min_val = int(round(60 + base_diff * 55 + random.uniform(-8, 8)))
    gap_min_val = max(50, gap_min_val)
    gap_spread = int(round(50 + base_diff * 80 + random.uniform(-12, 12)))
    gap_max_val = gap_min_val + max(30, gap_spread)

    width_max_val = int(round(260 - base_diff * 110 + random.uniform(-12, 12)))
    width_max_val = max(150, width_max_val)
    width_min_val = width_max_val - int(round(40 + base_diff * 45))
    width_min_val = max(90, width_min_val)
    if width_min_val >= width_max_val:
        width_min_val = max(80, width_max_val - 20)

    base_lives = max(2, 5 - int(base_diff * 3 + random.random()))

    difficulty_score = base_diff
    difficulty_score += max(0, (gap_min_val - 70) / 140)
    difficulty_score += max(0, (200 - width_max_val) / 200)
    difficulty_score += (5 - base_lives) * 0.08
    difficulty_score = max(0.35, min(difficulty_score, 1.4))

    payment = int(round(140 + difficulty_score * 340 + random.uniform(-10, 10)))
    xp_reward = int(round(80 + difficulty_score * 240))

    contract_name = f"{random.choice(namePrefixes)} {random.choice(nameSuffixes)}"
    descriptor = pickDifficultyLabel(difficulty_score)
    description = f"{descriptor} through {random.choice(hazardDescriptors)}."

    return {
        "name": contract_name,
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
        "label": descriptor,
    }


def refreshContracts():
    global contracts, selectedContractIndex
    contracts = [generateContract() for _ in range(CONTRACT_OPTION_COUNT)]
    selectedContractIndex = 0

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

# =========================
# Geometry / colors
# =========================
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

# Player
playerRect = pygame.Rect(100, 500, 30, 30)
velX = 0.0
velY = 0.0
onGround = False
lastGroundedMs = -10_000
lastJumpPressMs = -10_000
cameraX = 0
dimensionIndex = 0

# Colors for level space
platformColor = (210, 210, 230)
hazardOptions = [
    ("ACID", (80, 200, 80)),
    ("LAVA", (220, 60, 40)),
]
bgColor = (30, 30, 38)
ceilingColor = (60, 60, 100)
floorColor = (70, 55, 40)
floorHazardName = "ACID"

# Platform caches
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
}
gameOverSummary = {
    "contract": "",
    "reason": "Out of lives",
}

jumpBufferMs = 140
coyoteTimeMs = 120

# =========================
# Helpers
# =========================
def computeJumpHeight(jump_strength, gravity_val):
    g = max(1e-6, abs(gravity_val))
    return (jump_strength * jump_strength) / (2.0 * g)


def calculateRoofHeight(jump_strength, gravity_val):
    jump_height = computeJumpHeight(jump_strength, gravity_val)
    min_corridor = minCeilRoom + minFloorRoom + 180
    base_corridor = min_corridor + int(jump_height * 0.6)
    variation = max(24, int(jump_height * 0.35))
    corridor_height = base_corridor + random.randint(-variation, variation)
    corridor_height = max(min_corridor, min(corridor_height, floorY - 80))
    return max(40, floorY - corridor_height)


def applyDimensionPalette(index):
    shift = (index * 18) % 120

    def clamp_channel(value):
        return max(0, min(255, value))

    return (
        (
            clamp_channel(30 + shift // 2),
            clamp_channel(30 + shift // 3),
            clamp_channel(38 + shift // 2),
        ),
        (
            clamp_channel(60 + shift // 2),
            clamp_channel(60 + shift // 4),
            clamp_channel(100 + shift // 2),
        ),
        (
            clamp_channel(70 + shift // 3),
            clamp_channel(55 + shift // 3),
            clamp_channel(40 + shift // 4),
        ),
    )


def generatePlatforms():
    jump_height = computeJumpHeight(jumpStrength, gravity)
    vertical_step = max(28, int(jump_height * 0.6))
    horizontal_step = max(platformGapMin, min(platformGapMax, int(jump_height * 1.2)))

    start_y = floorY - minFloorRoom - 40
    min_platform_y = roofHeight + minCeilRoom
    max_platform_y = floorY - minFloorRoom
    door_start = hallLength - doorClearBuffer

    start_platform = pygame.Rect(60, start_y, 220, platformThickness)
    platforms = [start_platform]
    current_x = start_platform.right + random.randint(platformGapMin, horizontal_step)
    current_y = start_platform.y

    while current_x < door_start - platformWidthMin - platformGapMin:
        width = random.randint(platformWidthMin, platformWidthMax)
        current_y += random.randint(-vertical_step, vertical_step)
        current_y = max(min_platform_y, min(current_y, max_platform_y))
        platforms.append(pygame.Rect(current_x, current_y, width, platformThickness))
        current_x += width + random.randint(platformGapMin, horizontal_step)

    end_width = max(200, platformWidthMax)
    end_x = max(door_start - end_width - 40, current_x - 80)
    end_y = max(min_platform_y, min(current_y, max_platform_y))
    end_platform = pygame.Rect(end_x, end_y, end_width, platformThickness)
    platforms.append(end_platform)

    return platforms, start_platform, end_platform


def applyContractSettings(contract):
    global gravity, jumpStrength, platformGapMin, platformGapMax
    global platformWidthMin, platformWidthMax, livesRemaining, maxLives
    gravity = contract["gravity"]
    jumpStrength = contract["jump"]
    platformGapMin = contract["gap_min"]
    platformGapMax = contract["gap_max"]
    platformWidthMin = contract["width_min"]
    platformWidthMax = contract["width_max"]
    lives = contract["lives"] + extraLifeBonus
    livesRemaining = max(1, lives)
    maxLives = livesRemaining


def addXP(amount):
    global playerXP, playerLevel, xpForNextLevel
    playerXP += amount
    leveled = False
    while playerXP >= xpForNextLevel:
        playerXP -= xpForNextLevel
        playerLevel += 1
        xpForNextLevel = max(xpForNextLevel + 80, int(xpForNextLevel * 1.2))
        leveled = True
    return leveled


def prepareContract(contract):
    global currentContract, portalActive, levelNeedsBuild
    currentContract = contract
    applyContractSettings(contract)
    portalActive = True
    levelNeedsBuild = True


def startLevelRun():
    global levelNeedsBuild, dimensionIndex
    if not levelNeedsBuild or currentContract is None:
        return
    dimensionIndex += 1
    rebuildWorld()
    levelNeedsBuild = False


def recordWin():
    global playerMoney, portalActive, currentContract, levelNeedsBuild
    global winSummary, gameState
    if currentContract is None:
        return
    payout = int(round(currentContract["payment"] * missionPayMultiplier))
    playerMoney += payout
    addXP(currentContract["xp"])
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


def recordFailure(reason="Out of lives"):
    global portalActive, currentContract, levelNeedsBuild, gameState, gameOverSummary
    if currentContract:
        gameOverSummary.update({"contract": currentContract["name"], "reason": reason})
    else:
        gameOverSummary.update({"contract": "Unknown", "reason": reason})
    portalActive = False
    currentContract = None
    levelNeedsBuild = False
    gameState = GameState.GAME_OVER


def ownedCount(key):
    return ownedUpgrades.get(key, 0)


def updateShopScroll():
    global shopScrollOffset
    if shopSelectionIndex < shopScrollOffset:
        shopScrollOffset = shopSelectionIndex
    elif shopSelectionIndex >= shopScrollOffset + SHOP_VISIBLE_ROWS:
        shopScrollOffset = shopSelectionIndex - SHOP_VISIBLE_ROWS + 1
    max_offset = max(0, len(shopItems) - SHOP_VISIBLE_ROWS)
    shopScrollOffset = max(0, min(shopScrollOffset, max_offset))


def purchaseShopItem(item):
    global playerMoney, missionPayMultiplier, extraLifeBonus
    global playerColor, officeDecorStyle, shopMessage
    key = item["key"]
    stacks = ownedCount(key)
    if stacks >= item.get("max_stacks", 1):
        shopMessage = "Already owned."
        return
    cost = item["cost"]
    if playerMoney < cost:
        shopMessage = "Insufficient funds."
        return
    playerMoney -= cost
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


def rebuildWorld():
    global roofHeight, platformRects, startPlatformRect, endPlatformRect
    global bgColor, ceilingColor, floorColor, floorHazardName, spawnPoint
    global velX, velY, onGround, lastGroundedMs, lastJumpPressMs, cameraX

    bg_base, ceiling_base, _ = applyDimensionPalette(dimensionIndex)
    roofHeight = calculateRoofHeight(jumpStrength, gravity)
    platformRects, startPlatformRect, endPlatformRect = generatePlatforms()

    hazard_name, hazard_color = random.choice(hazardOptions)
    floorHazardName = hazard_name
    bgColor = bg_base
    ceilingColor = ceiling_base
    floorColor = hazard_color

    door_left = max(endPlatformRect.centerx - doorWidth // 2, endPlatformRect.left + 10)
    door_left = min(door_left, endPlatformRect.right - doorWidth - 10)
    door_top_desired = endPlatformRect.top - doorHeight
    min_door_top = roofHeight + 20
    door_top = max(min_door_top, door_top_desired)
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


def resolveHorizontal(rect, dx, solids):
    rect.x += int(dx)
    for solid in solids:
        if rect.colliderect(solid):
            if dx > 0:
                rect.right = solid.left
            elif dx < 0:
                rect.left = solid.right
    return rect


def resolveVertical(rect, dy, solids):
    rect.y += int(dy)
    grounded = False
    for solid in solids:
        if rect.colliderect(solid):
            if dy > 0:
                rect.bottom = solid.top
                dy = 0
                grounded = True
            elif dy < 0:
                rect.top = solid.bottom
                dy = 0
    return rect, grounded, dy


def respawnPlayer(now, loseLife=False):
    global velX, velY, onGround, lastGroundedMs, lastJumpPressMs, cameraX, livesRemaining
    if loseLife and gameState == GameState.LEVEL:
        livesRemaining = max(0, livesRemaining - 1)
    playerRect.midbottom = (spawnPoint.x, spawnPoint.y)
    velX = 0.0
    velY = 0.0
    onGround = True
    lastGroundedMs = now
    lastJumpPressMs = -10_000
    cameraX = 0


def returnToHub():
    global gameState, portalActive, levelNeedsBuild, gravity, jumpStrength
    global platformGapMin, platformGapMax, platformWidthMin, platformWidthMax
    global livesRemaining, maxLives, shopSelectionIndex, shopScrollOffset, shopMessage
    refreshContracts()
    spawnPoint.update(hubSpawnPoint.x, hubSpawnPoint.y)
    livesRemaining = 0
    maxLives = 0
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
    gameState = GameState.HUB
    respawnPlayer(pygame.time.get_ticks())


# =========================
# Main loop
# =========================
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
        if menuUp:
            selectedContractIndex = (selectedContractIndex - 1) % len(contracts)
        if menuDown:
            selectedContractIndex = (selectedContractIndex + 1) % len(contracts)
        if confirmPressed or interactPressed:
            prepareContract(contracts[selectedContractIndex])
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
            updateShopScroll()
        if menuDown:
            shopSelectionIndex = (shopSelectionIndex + 1) % len(shopItems)
            updateShopScroll()
        if confirmPressed or interactPressed:
            purchaseShopItem(shopItems[shopSelectionIndex])
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
        if gameState == GameState.LEVEL and levelNeedsBuild:
            startLevelRun()

        velX = (
            -playerSpeed
            if keys[pygame.K_a]
            else playerSpeed
            if keys[pygame.K_d]
            else 0
        )
        velY += gravity

        solids = platformRects if gameState == GameState.LEVEL else []

        playerRect = resolveHorizontal(playerRect, velX, solids)
        groundedNow = False
        playerRect, landed, velY = resolveVertical(playerRect, velY, solids)
        groundedNow = groundedNow or landed

        if playerRect.bottom >= floorY:
            if gameState == GameState.LEVEL:
                respawnPlayer(now, loseLife=True)
                if livesRemaining <= 0:
                    recordFailure("Ran out of lives")
                continue
            playerRect.bottom = floorY
            if velY > 0:
                velY = 0
            groundedNow = True

        if gameState == GameState.LEVEL and playerRect.top <= roofHeight:
            playerRect.top = roofHeight
            if velY < 0:
                velY = 0

        if groundedNow:
            lastGroundedMs = now
        onGround = groundedNow

        pressedRecently = (now - lastJumpPressMs) <= jumpBufferMs
        hasCoyote = (now - lastGroundedMs) <= coyoteTimeMs
        if (jumpPressedThisFrame or pressedRecently) and (onGround or hasCoyote):
            velY = -jumpStrength
            onGround = False
            lastJumpPressMs = -10_000

        if gameState == GameState.LEVEL and playerRect.colliderect(doorRect):
            recordWin()
            continue

        if gameState == GameState.HUB:
            if playerRect.left < 0:
                playerRect.left = 0
            if playerRect.right > screenWidth:
                playerRect.right = screenWidth
            if interactPressed:
                if playerRect.colliderect(shopInteractRect):
                    shopMessage = "Browse our latest upgrades."
                    updateShopScroll()
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

        cameraX = (
            0
            if gameState != GameState.LEVEL
            else max(0, min(playerRect.centerx - screenWidth // 2, hallLength - screenWidth))
        )

    # =========================
    # Draw
    # =========================
    if gameState == GameState.LEVEL:
        screen.fill(bgColor)
        pygame.draw.rect(screen, ceilingColor, (-cameraX, 0, hallLength, roofHeight))
        pygame.draw.rect(
            screen,
            floorColor,
            (-cameraX, floorY, hallLength, screenHeight - floorY),
        )
        for plat in platformRects:
            pygame.draw.rect(
                screen, platformColor, (plat.x - cameraX, plat.y, plat.width, plat.height)
            )
        pygame.draw.rect(
            screen,
            doorColor,
            (doorRect.x - cameraX, doorRect.y, doorRect.width, doorRect.height),
        )
    else:
        screen.fill(hubBackgroundColor)
        pygame.draw.rect(screen, hubCeilingColor, (0, 0, screenWidth, 160))
        pygame.draw.rect(
            screen, hubFloorColor, (0, floorY, screenWidth, screenHeight - floorY)
        )

        tableColor = (110, 90, 120)
        legWidth = 16
        pygame.draw.rect(screen, tableColor, deskRect)
        pygame.draw.rect(
            screen, tableColor, (deskRect.left + 8, deskRect.bottom, legWidth, 50)
        )
        pygame.draw.rect(
            screen,
            tableColor,
            (deskRect.right - legWidth - 8, deskRect.bottom, legWidth, 50),
        )
        pygame.draw.rect(screen, (15, 15, 20), computerBodyRect)
        screenRect = computerBodyRect.inflate(-14, -18)
        pygame.draw.rect(screen, computerScreenColor, screenRect)
        keyboardRect = pygame.Rect(
            computerBodyRect.left - 20,
            computerBodyRect.bottom,
            computerBodyRect.width + 40,
            14,
        )
        pygame.draw.rect(screen, (160, 160, 175), keyboardRect)

        counterColor = (90, 100, 150)
        pygame.draw.rect(screen, counterColor, shopCounterRect)
        pygame.draw.rect(
            screen, counterColor, (shopCounterRect.left + 10, shopCounterRect.bottom, 16, 46)
        )
        pygame.draw.rect(
            screen,
            counterColor,
            (shopCounterRect.right - 26, shopCounterRect.bottom, 16, 46),
        )
        sign = uiFont.render("Shop", True, (230, 230, 255))
        signPos = (shopCounterRect.centerx - sign.get_width() // 2, shopCounterRect.y - 32)
        pygame.draw.rect(
            screen,
            (32, 32, 48),
            (signPos[0], signPos[1], sign.get_width() + 16, sign.get_height() + 8),
        )
        screen.blit(sign, (signPos[0] + 8, signPos[1] + 4))

        portalColor = portalActiveColor if portalActive else portalInactiveColor
        pygame.draw.rect(screen, (40, 40, 60), portalRect.inflate(12, 12))
        pygame.draw.rect(screen, portalColor, portalRect)
        pygame.draw.rect(screen, (255, 255, 255), portalRect.inflate(-40, -120), 2)

        if officeDecorStyle == "plant":
            plantPot = pygame.Rect(deskRect.right + 20, deskRect.top - 24, 20, 24)
            pygame.draw.rect(screen, (120, 70, 40), plantPot)
            pygame.draw.circle(
                screen, (80, 200, 90), (plantPot.centerx, plantPot.top - 10), 18
            )
        elif officeDecorStyle == "poster":
            posterRect = pygame.Rect(screenWidth - 260, 60, 140, 90)
            pygame.draw.rect(screen, (30, 45, 80), posterRect)
            pygame.draw.rect(screen, (190, 210, 255), posterRect.inflate(-12, -12))
            pygame.draw.line(
                screen,
                (60, 90, 150),
                posterRect.midbottom,
                (posterRect.centerx, posterRect.top + 10),
                2,
            )

    playerDrawRect = pygame.Rect(
        playerRect.x - cameraX, playerRect.y, playerRect.width, playerRect.height
    )
    pygame.draw.rect(screen, playerColor, playerDrawRect)

    # HUD
    if gameState == GameState.LEVEL:
        contract_name = currentContract["name"] if currentContract else "Contract"
        base_payment = currentContract["payment"] if currentContract else 0
        payment = int(round(base_payment * missionPayMultiplier))
        hud_lines = [
            contract_name,
            f"Lives: {livesRemaining}",
            f"Payment: ${payment}",
            f"Hazard: {floorHazardName}",
            f"Jump Height: {int(computeJumpHeight(jumpStrength, gravity))} px",
            f"XP: {playerXP}/{xpForNextLevel} (Lv {playerLevel})",
        ]
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

    # Menus / overlays
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
            if isSelected:
                highlight = pygame.Rect(panelRect.x + 15, itemY - 6, panelRect.width - 30, 48)
                pygame.draw.rect(screen, (70, 90, 140), highlight, border_radius=6)
            nameText = uiFont.render(
                f"{contract['name']} — ${effectivePay}", True, nameColor
            )
            screen.blit(nameText, (panelRect.x + 24, itemY))
            descText = uiFont.render(contract["description"], True, descColor)
            screen.blit(descText, (panelRect.x + 24, itemY + 22))
            extraText = uiFont.render(
                f"XP {contract['xp']} | Lives {contract['lives']} | {contract['label']} ({contract['difficulty']:.2f})",
                True,
                extraColor,
            )
            screen.blit(extraText, (panelRect.x + 24, itemY + 42))
            itemY += 70
        instructions = uiFont.render(
            "Enter/E to accept • Esc to cancel • W/S to navigate", True, (230, 230, 240)
        )
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
            ownedTimes = ownedCount(item["key"])
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
