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
# Use positive magnitude; jump is upward, gravity is downward
jumpStrength = 9.0
gravity = 0.6

# Platform placement helpers (tuned per contract)
minCeilRoom  = 60
minFloorRoom = 80

# =========================
# Progression / contracts
# =========================

class GameState(Enum):
    HUB = auto()
    SHOP = auto()
    CONTRACT_MENU = auto()
    LEVEL = auto()
    WIN = auto()
    GAME_OVER = auto()


contracts = [


    {
        "name": "Courier Run",
        "description": "Easy glide through a calm sector.",
        "payment": 140,
        "xp": 80,
        "gravity": 0.55,
        "jump": 9.6,
        "gap_min": 70,
        "gap_max": 130,
        "width_min": 160,
        "width_max": 260,
        "lives": 5
    },
    {
        "name": "Express Freight",
        "description": "Faster lanes with trickier jumps.",
        "payment": 280,
        "xp": 160,
        "gravity": 0.68,
        "jump": 9.0,
        "gap_min": 90,
        "gap_max": 170,
        "width_min": 140,
        "width_max": 220,
        "lives": 4
    },
    {
        "name": "Hazard Sweep",
        "description": "High-risk route drenched in hazards.",
        "payment": 460,
        "xp": 280,
        "gravity": 0.78,
        "jump": 8.6,
        "gap_min": 110,
        "gap_max": 190,
        "width_min": 120,
        "width_max": 200,
        "lives": 3
    }
]

shopItems = [
    {
        "key": "premium_routes",
        "name": "Premium Routes License",
        "description": "+20% contract payouts.",
        "cost": 250,
        "type": "mission_bonus",
        "value": 1.2,
        "max_stacks": 1
    },
    {
        "key": "extra_life",
        "name": "Auxiliary Drone",
        "description": "+1 life on every mission.",
        "cost": 200,
        "type": "extra_life",
        "value": 1,
        "max_stacks": 1
    },
    {
        "key": "color_mint",
        "name": "Suit Paint - Neon Mint",
        "description": "Fresh mint glow for your suit.",
        "cost": 120,
        "type": "player_color",
        "value": (120, 255, 200),
        "max_stacks": 1
    },
    {
        "key": "color_violet",
        "name": "Suit Paint - Royal Violet",
        "description": "Stand out with deep royal hues.",
        "cost": 120,
        "type": "player_color",
        "value": (190, 120, 255),
        "max_stacks": 1
    },
    {
        "key": "decor_plant",
        "name": "Office Hanging Planter",
        "description": "Adds greenery to the office.",
        "cost": 90,
        "type": "decor",
        "value": "plant",
        "max_stacks": 1
    },
    {
        "key": "decor_poster",
        "name": "Skyline Poster",
        "description": "Add a skyline view to the wall.",
        "cost": 110,
        "type": "decor",
        "value": "poster",
        "max_stacks": 1
    }
]

gameState = GameState.HUB
portalActive = False
levelNeedsBuild = False
currentContract = None
selectedContractIndex = 0
shopSelectionIndex = 0

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

# Jump helpers
jumpBufferMs = 140          # remember pressed jump briefly
coyoteTimeMs = 120          # grace after leaving ground

# =========================
# Player
# =========================
playerRect = pygame.Rect(100, 500, 30, 30)
velX, velY = 0.0, 0.0
onGround = False
lastGroundedMs = -10_000
lastJumpPressMs = -10_000
cameraX = 0
dimensionIndex = 0
doorWidth, doorHeight = 52, 150
doorColor = (60, 200, 90)
doorRect = pygame.Rect(0, 0, doorWidth, doorHeight)
platformColor = (210, 210, 230)
hazardOptions = [
    ("ACID", (80, 200, 80)),
    ("LAVA", (220, 60, 40))
]
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

# =========================
# Colors (simple, no dimensions)
# =========================
bgColor = (30, 30, 38)
ceilingColor = (60, 60, 100)
floorColor = (70, 55, 40)

# =========================
# Helpers
# =========================
def computeJumpHeight(jumpStrengthVal, gravityVal):
    g = max(1e-6, abs(gravityVal))
    v = float(jumpStrengthVal)
    return (v*v) / (2.0*g)

def calculateRoofHeight(jumpStrengthVal, gravityVal):
    """Derive a roof height that scales with the player's jump capability."""
    jumpHeight = computeJumpHeight(jumpStrengthVal, gravityVal)
    minCorridor = minCeilRoom + minFloorRoom + 180
    baseCorridor = minCorridor + int(jumpHeight * 0.6)
    variation = max(24, int(jumpHeight * 0.35))
    corridorHeight = baseCorridor + random.randint(-variation, variation)
    corridorHeight = max(minCorridor, min(corridorHeight, floorY - 80))
    return max(40, floorY - corridorHeight)

def applyDimensionPalette(index):
    """Subtle color shift per dimension so the player feels progress."""
    shift = (index * 18) % 120
    def clamp_channel(c):
        return max(0, min(255, c))
    return (
        (clamp_channel(30 + shift // 2), clamp_channel(30 + shift // 3), clamp_channel(38 + shift // 2)),
        (clamp_channel(60 + shift // 2), clamp_channel(60 + shift // 4), clamp_channel(100 + shift // 2)),
        (clamp_channel(70 + shift // 3), clamp_channel(55 + shift // 3), clamp_channel(40 + shift // 4)),
    )

def generatePlatforms():
    """Create reachable platform path based on jump power and gravity."""
    jumpHeight = computeJumpHeight(jumpStrength, gravity)
    verticalStep = max(28, int(jumpHeight * 0.6))
    horizontalStep = max(platformGapMin, min(platformGapMax, int(jumpHeight * 1.2)))

    startY = floorY - minFloorRoom - 40
    minPlatformY = roofHeight + minCeilRoom
    maxPlatformY = floorY - minFloorRoom
    doorStart = hallLength - doorClearBuffer

    startPlatform = pygame.Rect(60, startY, 220, platformThickness)

    platforms = [startPlatform]
    currentX = startPlatform.right + random.randint(platformGapMin, horizontalStep)
    currentY = startPlatform.y

    while currentX < doorStart - platformWidthMin - platformGapMin:
        width = random.randint(platformWidthMin, platformWidthMax)
        currentY += random.randint(-verticalStep, verticalStep)
        currentY = max(minPlatformY, min(currentY, maxPlatformY))

        platforms.append(pygame.Rect(currentX, currentY, width, platformThickness))
        currentX += width + random.randint(platformGapMin, horizontalStep)

    endPlatformWidth = max(200, platformWidthMax)
    endPlatformX = max(doorStart - endPlatformWidth - 40, currentX - 80)
    endPlatformY = max(minPlatformY, min(currentY, maxPlatformY))
    endPlatform = pygame.Rect(endPlatformX, endPlatformY, endPlatformWidth, platformThickness)
    platforms.append(endPlatform)

    return platforms, startPlatform, endPlatform

def applyContractSettings(contract):
    """Set physics tuning from the chosen contract."""
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
    """Increase XP and handle level-ups."""
    global playerXP, playerLevel, xpForNextLevel
    leveled_up = False
    playerXP += amount
    while playerXP >= xpForNextLevel:
        playerXP -= xpForNextLevel
        playerLevel += 1
        xpForNextLevel = max(xpForNextLevel + 80, int(xpForNextLevel * 1.2))
        leveled_up = True
    return leveled_up

def prepareContract(contract):
    """Remember the selected contract and ready the portal."""
    global currentContract, portalActive, levelNeedsBuild
    currentContract = contract
    applyContractSettings(contract)
    portalActive = True
    levelNeedsBuild = True

def startLevelRun():
    """Build the dimension for the active contract before play begins."""
    global levelNeedsBuild, dimensionIndex
    if not levelNeedsBuild or currentContract is None:
        return
    dimensionIndex += 1
    rebuildWorld()
    levelNeedsBuild = False

def recordWin():
    """Capture rewards and head to the win screen."""
    global playerMoney, winSummary, gameState, portalActive, currentContract, levelNeedsBuild
    if currentContract is None:
        return
    payout = int(round(currentContract["payment"] * missionPayMultiplier))
    playerMoney += payout
    addXP(currentContract["xp"])
    winSummary.update({
        "payment": payout,
        "xp": currentContract["xp"],
        "contract": currentContract["name"],
        "moneyTotal": playerMoney,
        "xpTotal": playerXP,
        "level": playerLevel
    })
    portalActive = False
    levelNeedsBuild = False
    gameState = GameState.WIN
    currentContract = None

def recordFailure(reason="Out of lives"):
    """Set up the game-over screen."""
    global gameState, portalActive, gameOverSummary, currentContract, levelNeedsBuild
    if currentContract:
        gameOverSummary.update({
            "contract": currentContract["name"],
            "reason": reason
        })
    else:
        gameOverSummary.update({"contract": "Unknown", "reason": reason})
    portalActive = False
    currentContract = None
    levelNeedsBuild = False
    gameState = GameState.GAME_OVER

def returnToHub():
    """Reset the player back in the office hub."""
    global gameState, portalActive, spawnPoint, levelNeedsBuild
    global livesRemaining, maxLives, gravity, jumpStrength, shopMessage
    global platformGapMin, platformGapMax, platformWidthMin, platformWidthMax
    spawnPoint = hubSpawnPoint.copy()
    livesRemaining = 0
    maxLives = 0
    portalActive = False
    levelNeedsBuild = False
    gravity = 0.6
    jumpStrength = 9.0
    platformGapMin = 70
    platformGapMax = 150
    platformWidthMin = 160
    platformWidthMax = 260
    gameState = GameState.HUB
    shopMessage = "Welcome back to the Supply Depot."
    respawnPlayer(pygame.time.get_ticks())

def ownedCount(key):
    return ownedUpgrades.get(key, 0)

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

platformRects = []
startPlatformRect = pygame.Rect(0, 0, 0, 0)
endPlatformRect = pygame.Rect(0, 0, 0, 0)
hubSpawnPoint = pygame.Vector2(deskRect.centerx + 20, deskRect.top)
spawnPoint = hubSpawnPoint.copy()
floorHazardName = "ACID"
winSummary = {
    "payment": 0,
    "xp": 0,
    "contract": "",
    "moneyTotal": 0,
    "xpTotal": 0,
    "level": 1
}
gameOverSummary = {
    "contract": "",
    "reason": "Out of lives"
}

def rebuildWorld():
    global roofHeight, platformRects, startPlatformRect, endPlatformRect
    global velX, velY, onGround, lastGroundedMs, lastJumpPressMs, cameraX
    global doorRect, bgColor, ceilingColor, floorColor, floorHazardName, spawnPoint

    bgBase, ceilingBase, _ = applyDimensionPalette(dimensionIndex)
    roofHeight = calculateRoofHeight(jumpStrength, gravity)
    platformRects, startPlatformRect, endPlatformRect = generatePlatforms()

    hazardChoice = random.choice(hazardOptions)
    floorHazardName, floorHazardColor = hazardChoice[0], hazardChoice[1]
    bgColor, ceilingColor = bgBase, ceilingBase
    floorColor = floorHazardColor

    doorLeft = max(endPlatformRect.centerx - doorWidth // 2, endPlatformRect.left + 10)
    doorLeft = min(doorLeft, endPlatformRect.right - doorWidth - 10)
    doorTopDesired = endPlatformRect.top - doorHeight
    minDoorTop = roofHeight + 20
    doorTop = max(minDoorTop, doorTopDesired)
    doorHeightActual = max(60, endPlatformRect.top - doorTop)
    doorRect.update(doorLeft, doorTop, doorWidth, doorHeightActual)

    velX = velY = 0.0
    playerRect.midbottom = (startPlatformRect.centerx, startPlatformRect.top)
    spawnPoint = pygame.Vector2(startPlatformRect.centerx, startPlatformRect.top)
    onGround = True
    lastGroundedMs = pygame.time.get_ticks()
    lastJumpPressMs = -10_000
    cameraX = 0

    pygame.display.set_caption(f"M.U.P.S — Dimension {dimensionIndex + 1}")

def resolveHorizontal(rect, dx, solids):
    rect.x += int(dx)
    for s in solids:
        if rect.colliderect(s):
            if dx > 0: rect.right = s.left
            elif dx < 0: rect.left = s.right
    return rect

def resolveVertical(rect, dy, solids):
    rect.y += int(dy)
    onGroundLocal = False
    for s in solids:
        if rect.colliderect(s):
            if dy > 0:   # moving down
                rect.bottom = s.top; dy = 0
                onGroundLocal = True
            elif dy < 0: # moving up
                rect.top = s.bottom; dy = 0
    return rect, onGroundLocal, dy

def respawnPlayer(now, loseLife=False):
    global velX, velY, onGround, lastGroundedMs, lastJumpPressMs, cameraX
    global livesRemaining
    if loseLife and gameState == GameState.LEVEL:
        livesRemaining = max(0, livesRemaining - 1)
    playerRect.midbottom = (spawnPoint.x, spawnPoint.y)
    velX = velY = 0.0
    onGround = True
    lastGroundedMs = now
    lastJumpPressMs = -10_000
    cameraX = 0

returnToHub()

# =========================
# Main loop
# =========================
while True:
    dt = clock.tick(60)
    now = pygame.time.get_ticks()
    jumpPressedThisFrame = False
    interactPressed = False
    confirmPressed = False
    backPressed = False
    menuUp = False
    menuDown = False

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_SPACE:
                jumpPressedThisFrame = True
                lastJumpPressMs = now
            elif e.key == pygame.K_e:
                interactPressed = True
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                confirmPressed = True
            elif e.key == pygame.K_ESCAPE:
                backPressed = True
            elif e.key in (pygame.K_UP, pygame.K_w):
                menuUp = True
            elif e.key in (pygame.K_DOWN, pygame.K_s):
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
        velX = velY = 0.0
        onGround = True
        cameraX = 0
    elif gameState == GameState.SHOP:
        if menuUp:
            shopSelectionIndex = (shopSelectionIndex - 1) % len(shopItems)
        if menuDown:
            shopSelectionIndex = (shopSelectionIndex + 1) % len(shopItems)
        if confirmPressed or interactPressed:
            purchaseShopItem(shopItems[shopSelectionIndex])
        if backPressed:
            shopMessage = "Come again soon."
            gameState = GameState.HUB
        velX = velY = 0.0
        onGround = True
        cameraX = 0
    elif gameState == GameState.WIN:
        if confirmPressed or interactPressed or backPressed:
            returnToHub()
        velX = velY = 0.0
    elif gameState == GameState.GAME_OVER:
        if confirmPressed or interactPressed or backPressed:
            returnToHub()
        velX = velY = 0.0
    else:
        # HUB or LEVEL physics
        if gameState == GameState.LEVEL and levelNeedsBuild:
            startLevelRun()

        velX = (-playerSpeed if keys[pygame.K_a] else playerSpeed if keys[pygame.K_d] else 0)
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
            else:
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
                    gameState = GameState.SHOP
                elif playerRect.colliderect(computerInteractRect):
                    gameState = GameState.CONTRACT_MENU
            if gameState == GameState.HUB and portalActive and playerRect.colliderect(portalRect):
                gameState = GameState.LEVEL
                levelNeedsBuild = True
        else:
            if playerRect.left < 0:
                playerRect.left = 0
            if playerRect.right > hallLength:
                playerRect.right = hallLength

        cameraX = 0 if gameState != GameState.LEVEL else max(0, min(playerRect.centerx - screenWidth // 2, hallLength - screenWidth))

    # =========================
    # Draw
    # =========================
    screen.fill(hubBackgroundColor if gameState in (GameState.HUB, GameState.CONTRACT_MENU, GameState.SHOP, GameState.WIN, GameState.GAME_OVER) else bgColor)

    if gameState == GameState.LEVEL:
        pygame.draw.rect(screen, ceilingColor, (-cameraX, 0, hallLength, roofHeight))
        pygame.draw.rect(screen, floorColor, (-cameraX, floorY, hallLength, screenHeight - floorY))
        for plat in platformRects:
            pygame.draw.rect(screen, platformColor, (plat.x - cameraX, plat.y, plat.width, plat.height))
        pygame.draw.rect(screen, doorColor, (doorRect.x - cameraX, doorRect.y, doorRect.width, doorRect.height))
    else:
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
        portalColor = portalActiveColor if portalActive else portalInactiveColor
        pygame.draw.rect(screen, (40, 40, 60), portalRect.inflate(12, 12))
        pygame.draw.rect(screen, portalColor, portalRect)
        pygame.draw.rect(screen, (255, 255, 255), portalRect.inflate(-40, -120), 2)
        counterColor = (90, 100, 150)
        pygame.draw.rect(screen, counterColor, shopCounterRect)
        pygame.draw.rect(screen, counterColor, (shopCounterRect.left + 10, shopCounterRect.bottom, 16, 46))
        pygame.draw.rect(screen, counterColor, (shopCounterRect.right - 26, shopCounterRect.bottom, 16, 46))
        sign = uiFont.render("Shop", True, (230, 230, 255))
        signPos = (shopCounterRect.centerx - sign.get_width() // 2, shopCounterRect.y - 32)
        pygame.draw.rect(screen, (32, 32, 48), (*signPos, sign.get_width() + 16, sign.get_height() + 8))
        screen.blit(sign, (signPos[0] + 8, signPos[1] + 4))
        if officeDecorStyle == "plant":
            plantPot = pygame.Rect(deskRect.right + 20, deskRect.top - 24, 20, 24)
            pygame.draw.rect(screen, (120, 70, 40), plantPot)
            pygame.draw.circle(screen, (80, 200, 90), (plantPot.centerx, plantPot.top - 10), 18)
        elif officeDecorStyle == "poster":
            posterRect = pygame.Rect(screenWidth - 260, 60, 140, 90)
            pygame.draw.rect(screen, (30, 45, 80), posterRect)
            pygame.draw.rect(screen, (190, 210, 255), posterRect.inflate(-12, -12))
            pygame.draw.line(screen, (60, 90, 150), posterRect.midbottom, (posterRect.centerx, posterRect.top + 10), 2)

    playerDrawRect = pygame.Rect(playerRect.x - cameraX, playerRect.y, playerRect.width, playerRect.height)
    pygame.draw.rect(screen, playerColor, playerDrawRect)

    hud_lines = []
    if gameState == GameState.LEVEL:
        contractName = currentContract["name"] if currentContract else "Contract"
        basePayment = currentContract["payment"] if currentContract else 0
        payment = int(round(basePayment * missionPayMultiplier))
        hud_lines = [
            f"{contractName}",
            f"Lives: {livesRemaining}",
            f"Payment: ${payment}",
            f"Hazard: {floorHazardName}",
            f"Jump Height: {int(computeJumpHeight(jumpStrength, gravity))} px",
            f"XP: {playerXP}/{xpForNextLevel} (Lv {playerLevel})"
        ]
    elif gameState == GameState.HUB:
        hud_lines = [
            f"Level {playerLevel}    XP: {playerXP}/{xpForNextLevel}",
            f"Money: ${playerMoney}",
            "A/D to move  SPACE to jump",
            "Press E at the computer for contracts",
            "Press E at the counter for upgrades",
            f"Portal: {'ONLINE' if portalActive else 'offline'}"
        ]
    elif gameState == GameState.CONTRACT_MENU:
        hud_lines = [
            f"Level {playerLevel}    XP: {playerXP}/{xpForNextLevel}",
            f"Money: ${playerMoney}"
        ]
    else:
        hud_lines = [
            f"Level {playerLevel}    XP: {playerXP}/{xpForNextLevel}",
            f"Money: ${playerMoney}"
        ]

    for i, line in enumerate(hud_lines):
        screen.blit(uiFont.render(line, True, (255, 255, 255)), (20, 20 + i * 24))

    if gameState == GameState.CONTRACT_MENU:
        panelRect = pygame.Rect(140, 120, screenWidth - 280, screenHeight - 240)
        pygame.draw.rect(screen, (28, 28, 42), panelRect)
        pygame.draw.rect(screen, (180, 180, 210), panelRect, 2)
        title = titleFont.render("Select Contract", True, (245, 245, 255))
        screen.blit(title, (panelRect.x + 20, panelRect.y + 20))
        itemY = panelRect.y + 80
        for idx, contract in enumerate(contracts):
            isSelected = (idx == selectedContractIndex)
            effectivePay = int(round(contract['payment'] * missionPayMultiplier))
            nameText = uiFont.render(f"{contract['name']} — ${effectivePay}", True,
                                     (255, 255, 255) if isSelected else (200, 200, 220))
            descText = uiFont.render(contract["description"], True,
                                     (190, 190, 210) if isSelected else (120, 120, 150))
            if isSelected:
                highlightRect = pygame.Rect(panelRect.x + 15, itemY - 6, panelRect.width - 30, 48)
                pygame.draw.rect(screen, (70, 90, 140), highlightRect, border_radius=6)
            screen.blit(nameText, (panelRect.x + 24, itemY))
            screen.blit(descText, (panelRect.x + 24, itemY + 22))
            extra = uiFont.render(f"XP {contract['xp']}  Lives {contract['lives']}", True,
                                  (220, 220, 240) if isSelected else (130, 130, 150))
            screen.blit(extra, (panelRect.x + 24, itemY + 42))
            itemY += 70
        instructions = uiFont.render("Enter/E to accept • Esc to cancel • W/S to navigate", True, (230, 230, 240))
        screen.blit(instructions, (panelRect.x + 20, panelRect.bottom - 40))
    elif gameState == GameState.SHOP:
        panelRect = pygame.Rect(120, 110, screenWidth - 240, screenHeight - 220)
        pygame.draw.rect(screen, (32, 28, 44), panelRect)
        pygame.draw.rect(screen, (200, 200, 230), panelRect, 2)
        title = titleFont.render("Supply Depot", True, (245, 245, 255))
        screen.blit(title, (panelRect.x + 20, panelRect.y + 20))
        fundsText = uiFont.render(f"Credits: ${playerMoney}", True, (220, 220, 255))
        screen.blit(fundsText, (panelRect.x + panelRect.width - fundsText.get_width() - 20, panelRect.y + 24))
        itemY = panelRect.y + 80
        for idx, item in enumerate(shopItems):
            ownedTimes = ownedCount(item["key"])
            maxStacks = item.get("max_stacks", 1)
            available = ownedTimes < maxStacks
            isSelected = idx == shopSelectionIndex
            highlightRect = pygame.Rect(panelRect.x + 16, itemY - 8, panelRect.width - 32, 64)
            if isSelected:
                pygame.draw.rect(screen, (78, 60, 120), highlightRect, border_radius=6)
            costColor = (255, 255, 255) if available else (150, 80, 80)
            nameColor = (255, 255, 255) if available else (160, 140, 140)
            nameText = uiFont.render(f"{item['name']} (${item['cost']})", True,
                                     nameColor if not isSelected else (255, 255, 255))
            screen.blit(nameText, (panelRect.x + 26, itemY))
            detail = f"{item['description']}"
            if maxStacks > 1:
                detail += f" ({ownedTimes}/{maxStacks})"
            else:
                detail += f" {'OWNED' if ownedTimes else ''}".rstrip()
            descText = uiFont.render(detail, True, (190, 190, 210))
            screen.blit(descText, (panelRect.x + 26, itemY + 22))
            status = "Available" if available else "Owned"
            statusText = uiFont.render(status, True, costColor)
            screen.blit(statusText, (panelRect.x + panelRect.width - statusText.get_width() - 26, itemY))
            itemY += 70
        instructions = uiFont.render("Enter/E to purchase • Esc to exit • W/S to browse", True, (230, 230, 240))
        screen.blit(instructions, (panelRect.x + 20, panelRect.bottom - 60))
        messageText = uiFont.render(shopMessage, True, (220, 220, 255))
        screen.blit(messageText, (panelRect.x + 20, panelRect.bottom - 32))
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
            "Press Enter/E to return to the office."
        ]
        for i, text in enumerate(lines):
            render = uiFont.render(text, True, (220, 255, 230))
            screen.blit(render, (panelRect.x + 30, panelRect.y + 110 + i * 30))
    elif gameState == GameState.GAME_OVER:
        panelRect = pygame.Rect(180, 160, screenWidth - 360, screenHeight - 320)
        pygame.draw.rect(screen, (60, 25, 25), panelRect)
        pygame.draw.rect(screen, (200, 80, 80), panelRect, 3)
        title = titleFont.render("Mission Failed", True, (255, 210, 210))
        screen.blit(title, (panelRect.centerx - title.get_width() // 2, panelRect.y + 28))
        lines = [
            f"Contract: {gameOverSummary['contract']}",
            f"Reason: {gameOverSummary['reason']}",
            "Press Enter/E to return to the office."
        ]
        for i, text in enumerate(lines):
            render = uiFont.render(text, True, (255, 220, 220))
            screen.blit(render, (panelRect.x + 30, panelRect.y + 120 + i * 32))

    pygame.display.flip()
