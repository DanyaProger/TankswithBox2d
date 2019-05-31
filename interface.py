import pygame
import tanks_client
#import database
pygame.init()

WINDOW_SIZE_X = 800
WINDOW_SIZE_Y = 800

WHITE = (255, 255, 255)
BLACK = (255, 255, 255)
RED = (255, 50, 0)
NICE_BLUE = (0, 125, 255)
SKY_BLUE = (135, 206, 235)

class Button:
    def __init__(self, game_window, x, y, w, h, color, text, action=None, sender=None):
        self.text = str(text)
        self.action = action
        self.sender = sender
        self.color = color
        self.game_window = game_window
        self.rect = pygame.Rect(x, y, w, h)

    def draw(self):
        pygame.draw.rect(self.game_window, self.color, self.rect)
        draw_text(self.text, self.game_window, int(self.rect.h / 2), WHITE,
                  self.rect.x + self.rect.w / 2, self.rect.y + self.rect.h / 2)

    def is_clicked(self, x, y):
        if self.rect.collidepoint(x, y):
            if self.text == "Connect":
                #if self.sender[1].text == '' :
                #    return True
                self.action(self.game_window, self.sender[1].text, self.sender[0].text)
            elif self.text == "Rating":
                self.action(self.game_window, self.sender[1].text, self.sender[0].text)
            elif self.text == "Return":
                pass
            elif self.text == "Delete player":
                self.action(self.sender.text)
                self.sender.erase()
            elif self.text == "Continue":
                return True
            else:
                self.action()
            return True
        return False


class InputBox:
    COLOR_INACTIVE = WHITE
    COLOR_ACTIVE = SKY_BLUE
    FONT_SIZE = 70
    FONT = pygame.font.Font(None, FONT_SIZE)

    def __init__(self, screen, x, y, w, h, text=''):
        self.screen = screen
        self.w = w
        self.rect = pygame.Rect(x, y, w, h)
        self.color = self.COLOR_INACTIVE
        self.text = text
        self.txt_surface = self.FONT.render(text, True, self.color)
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos[0], event.pos[1]):
                self.active = not self.active
            else:
                self.active = False
            self.color = self.COLOR_ACTIVE if self.active else self.COLOR_INACTIVE
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                    #self.erase()
                else:
                    self.text += event.unicode
                self.txt_surface = self.FONT.render(self.text, True, self.color)

    def erase(self):
        self.text = ""
        self.txt_surface = self.FONT.render(self.text, True, self.color)
        self.draw()

    def draw(self):
        width = max(self.w, self.txt_surface.get_width() + 10)
        self.rect.w = width
        self.screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        pygame.draw.rect(self.screen, self.color, self.rect, 2)

def draw_text(text, surface, font_size, color, x, y):
    text_obj = pygame.font.SysFont(None, font_size).render(str(text), 1, color)
    text_rect = text_obj.get_rect()
    text_rect.center = (x, y)
    surface.blit(text_obj, text_rect)

def show_main_menu(display):

    ip_input = InputBox(display,
                         WINDOW_SIZE_X / 2,
                         WINDOW_SIZE_Y / 2 - 300,
                         350,
                         70)
    ip_input.text = '127.0.1.1'
    ip_input.txt_surface = ip_input.FONT.render(ip_input.text, True, ip_input.color)


    login_input = InputBox(display,
                         WINDOW_SIZE_X / 2,
                         WINDOW_SIZE_Y / 2 - 50,
                         350,
                         70)


    connect_button = Button(display,
                        WINDOW_SIZE_X / 2 - 250,
                        WINDOW_SIZE_Y / 2 + 200,
                        225, 100, NICE_BLUE,
                        "Connect",
                        tanks_client.start, (ip_input, login_input))

    rating_button = Button(display,
                        WINDOW_SIZE_X / 2 + 25,
                        WINDOW_SIZE_Y / 2 + 200,
                        225, 100, NICE_BLUE,
                        "Rating",
                        show_statistics_menu, (ip_input, login_input))

    buttons = list()
    buttons.append(connect_button)
    buttons.append(rating_button)
    done = False
    field_surf = pygame.image.load('th.jpeg').convert()
    while not done:
        display.fill((0, 0, 0))
        #ClearWindow(display, field_surf)

        draw_text('Enter IP', display, 50, WHITE,
                  (WINDOW_SIZE_X / 2 - 200), (WINDOW_SIZE_Y / 2 - 250))

        draw_text('Enter your name:', display, 50, WHITE,
                  200, (WINDOW_SIZE_Y / 2))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            ip_input.handle_event(event)
            login_input.handle_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN:
                for button in buttons:
                    button.is_clicked(event.pos[0], event.pos[1])
        for button in buttons:
            button.draw()
        ip_input.draw()
        login_input.draw()
        pygame.display.update()

def ClearWindow(display, texture):
    for i in range(0, 2) :
        for j in range(0, 3) :
            field_rect = pygame.Rect(j * 300, i * 300, 300, 300)
            display.blit(texture, field_rect)
    #text = pygame.transform.chop(texture, pygame.Rect(0, 0, 300, 200))
    for j in range(0, 3) :
        display.blit(texture, (j * 300, 600), (0, 0, 300, 300))


def show_statistics_menu(display, login, ip):
    top_users, user = tanks_client.get_users(ip, login)

    display.fill((0, 0, 0))
    field_surf = pygame.image.load('th.jpeg').convert()
    #ClearWindow(display, field_surf)


    draw_text('Top Statistics', display, 70, NICE_BLUE,
              (WINDOW_SIZE_X / 2), (80))
    draw_text('kills', display, 50, NICE_BLUE,
              160 * 2, 160)
    draw_text('died', display, 50, NICE_BLUE,
              160 * 3, 160)
    draw_text('games', display, 50, NICE_BLUE,
              160 * 4, 160)
    for i in range(len(top_users)):
        draw_text(top_users[i]['username'], display, 50, NICE_BLUE,
                  160, 240 + 80 * i)
        draw_text(top_users[i]['killed'], display, 50, NICE_BLUE,
                 160 * 2, 240 + 80 * i)
        draw_text(top_users[i]['died'], display, 50, NICE_BLUE,
                  160 * 3, 240 + 80 * i)
        draw_text(top_users[i]['played_games'], display, 50, NICE_BLUE,
                  160 * 4, 240 + 80 * i)

    draw_text('Your stats', display, 70, NICE_BLUE, WINDOW_SIZE_X / 2, 640)
    draw_text(user.username, display, 50, NICE_BLUE,
              160, 720)
    draw_text(user.killed, display, 50, NICE_BLUE,
              160 * 2, 720)
    draw_text(user.died, display, 50, NICE_BLUE,
              160 * 3, 720)
    draw_text(user.played_games, display, 50, NICE_BLUE,
              160 * 4, 720)


    return_button = Button(display,
                        WINDOW_SIZE_X / 2 - 200,
                        800 - 25,
                        400, 50, NICE_BLUE,
                        "Return",
                        clicks_checked)

    pygame.display.update()

    clicks_checked(return_button)

def clicks_checked(*buttons):
    is_exit = False
    while True:
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                for b in buttons:
                    if b.is_clicked(event.pos[0], event.pos[1]) and b.text == 'Return' :
                        is_exit = True
            if event.type == pygame.QUIT:
                is_exit = True
        if is_exit :
            break;
        for b in buttons:
            b.draw()
        pygame.display.update()