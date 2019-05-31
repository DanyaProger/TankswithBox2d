import pygame
import interface

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800

game_window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT + 50))

interface.show_main_menu(game_window)