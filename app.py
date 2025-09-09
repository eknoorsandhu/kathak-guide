"""little intro screen for the practice guide"""
import pygame

pygame.display.init()
pygame.font.init()
screen = pygame.display.set_mode((1000, 740))
pygame.display.set_caption("Kathak Practice Guide")
font = pygame.font.Font(None, 32)
lines = ["Kathak Practice Guide", "Stand back so your whole body and feet are visible.",
         "Use a teacher-approved tempo and alternate one foot per beat.",
         "Left and right mean your anatomical feet, not screen sides."]
clock = pygame.time.Clock()
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    screen.fill((23, 29, 37))
    for index, line in enumerate(lines):
        screen.blit(font.render(line, True, (232, 236, 240)), (30, 40 + index * 65))
    pygame.display.flip()
    clock.tick(30)
pygame.quit()
