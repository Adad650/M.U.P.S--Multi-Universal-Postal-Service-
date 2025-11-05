import pygame, sys

screenWidth = 800
screenHeight = 600

pygame.init()
screen = pygame.display.set_mode((screenWidth, screenHeight))
clock = pygame.time.Clock()

# Colors
white = (255, 255, 255)
blue = (0, 100, 255)
brown = (150, 75, 0)

# Ball setup
ball = pygame.Rect(380, 100, 40, 40)
velocityX = 0
velocityY = 0
gravity = 0.5
jumpStrength = -15
onGround = True

# Floor setup
floor = pygame.Rect(0, 550, 800, 50)


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    # Spacebar
    key = pygame.key.get_pressed()
    if key[pygame.K_SPACE] and onGround:
        velocityY = jumpStrength
        onGround = False

    if key[pygame.K_a]:
        velocityX = -5
    elif key[pygame.K_d]:
        velocityX = 5

    if not key[pygame.K_a] and not key[pygame.K_d]:
        velocityX = 0

    # Movement
    ball.x += velocityX

    # Apply gravity
    velocityX += gravity
    ball.y += velocityY

    # Collison stuff
    if ball.colliderect(floor):
        ball.bottom = floor.top
        velocityY = 0
        onGround = True

    screen.fill(white)
    pygame.draw.rect(screen, brown, floor)
    pygame.draw.ellipse(screen, blue, ball)
    pygame.display.update()
    clock.tick(60)
    ball.clamp_ip(screen.get_rect())
