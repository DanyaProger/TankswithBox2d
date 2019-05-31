# Filename: A08_multiplayer_demo_client.py
# Written by: James D. Miller

import sys, os
import pygame


# PyGame Constants
from pygame.locals import *
from pygame.color import THECOLORS

# Network stuff. Note "connection" is a single instantiation.
from PodSixNet.Connection import connection, ConnectionListener

# Argument parsing...
import argparse


# =======================================================================
# Classes
# =======================================================================

class NetworkListener(ConnectionListener):
    def __init__(self, host, port):
        self.Connect((host, port))

        self.client_colors = {'C1': THECOLORS["green"], 'C2': THECOLORS["tan"], 'C3': THECOLORS["black"],
                              'C4': THECOLORS["blue"],
                              'C5': THECOLORS["pink"], 'C6': THECOLORS["red"], 'C7': THECOLORS["coral"],
                              'C8': THECOLORS["orangered1"],
                              'C9': THECOLORS["grey80"], 'C10': THECOLORS["rosybrown3"]}

        self.background_color = THECOLORS["white"]
        self.client_name = 'C0'
        self.client_color = THECOLORS["black"]

    def Network_hello(self, data):
        global Player_ID, user_state
        print
        "Network_hello:", data

        Player_ID = data['P_ID']
        self.client_name = 'C' + str(Player_ID)

        self.background_color = THECOLORS["yellow"]
        self.client_color = self.client_colors[self.client_name]

        # Initialize user state dictionary.
        user_state = {'action': 'CN',
                      'ID': Player_ID,
                      'mouseXY': (0, 0), 'mouseB1': 'U',
                      'LEFT': 'U', 'DOWN': 'U',
                      'RIGHT': 'U', 'UP': 'U'}

        if Player_ID != 0 :
            query = {'action': 'sign_in', 'login':user_login, 'ID':Player_ID}
            connection.Send(query)

        pygame.display.set_caption("Client: GamePad #" + str(Player_ID))

    def Network_get_stats(self, data):
        global player1_stats, player2_stats
        import database
        if data['ID'] == 1 :
            player1_stats = database.Statistics('')
            player1_stats.killed = data['killed']
            player1_stats.died = data['died']
            player1_stats.played_games = data['played_games']
            player1_stats.username = data['username']
        if data['ID'] == 2 :
            player2_stats = database.Statistics('')
            player2_stats.killed = data['killed']
            player2_stats.died = data['died']
            player2_stats.played_games = data['played_games']
            player2_stats.username = data['username']

    def Network_action(self, data):
        global server_state
        server_state = data

    def Network_top(self, data):
        server_state = data
    # =======================================================================


# Functions
# =======================================================================

def get_users(ip) :
    network_listener = NetworkListener(ip, 4330)
    Player_ID = 0
    while(True) :
        connection.Pump()
        if Player_ID != 0 :
            connection.Send({'action':'top'})
        network_listener.Pump()
        if server_state['action'] == 'top' :
            return (server_state['users'], server_state['users'][-1])


def signoff(user_state):
    '''data = {}
    data['action'] = 'DS'
    data['ID'] = Player_ID
    connection.Send(data)
    connection.Pump()'''
    print('Exit')
    sys.exit()


def checkforUserInput(user_state):
    global is_exit
    # Check the button status.
    (button1, button2, button3) = pygame.mouse.get_pressed()

    # Get all the events since the last call to get().
    for event in pygame.event.get():
        if (event.type == pygame.QUIT):
            is_exit = True
        elif (event.type == pygame.KEYDOWN):
            if (event.key == K_ESCAPE):
                is_exit = True

            elif (event.key == K_LEFT):
                user_state['LEFT'] = 'D'
            elif (event.key == K_DOWN):
                user_state['DOWN'] = 'D'
            elif (event.key == K_RIGHT):
                user_state['RIGHT'] = 'D'
            elif (event.key == K_UP):
                user_state['UP'] = 'D'

        elif (event.type == pygame.KEYUP):
            if (event.key == K_LEFT):
                user_state['LEFT'] = 'U'
            elif (event.key == K_DOWN):
                user_state['DOWN'] = 'U'
            elif (event.key == K_RIGHT):
                user_state['RIGHT'] = 'U'
            elif (event.key == K_UP):
                user_state['UP'] = 'U'

        elif event.type == pygame.MOUSEBUTTONDOWN:
            user_state['mouseB1'] = 'D'

        elif event.type == pygame.MOUSEBUTTONUP:
            user_state['mouseB1'] = 'U'

        # cursor x,y
        user_state['mouseXY'] = pygame.mouse.get_pos()

def DrawImage(surf, x, y, angle) :
    draw_surf = pygame.transform.flip(surf, flipX, flipY)
    draw_surf = pygame.transform.rotate(draw_surf, angle)
    draw_rect = draw_surf.get_rect(center=(x, y))
    client_display.blit(draw_surf, draw_rect)

def DrawWalls() :
    width = 20

    pygame.draw.rect(client_display, (128, 128, 128), (0, 0, SCREEN_WIDTH, width))
    pygame.draw.rect(client_display, (128, 128, 128), (0, 0, width, SCREEN_HEIGHT))
    pygame.draw.rect(client_display, (128, 128, 128), (SCREEN_WIDTH - width, 0, width, SCREEN_HEIGHT))
    pygame.draw.rect(client_display, (128, 128, 128), (0, SCREEN_HEIGHT - width, SCREEN_WIDTH, width))


def get_users(ip, login) :
    import database
    user = database.Statistics(login)
    top_users = database.get_global_records('killed')
    return (top_users, user)

def DrawHealth(position, is_my, cof) :
    color = (0, 255, 0)
    width = 60
    height = 5
    offset = 40
    x = position[0]
    y = position[1]
    if not is_my :
        color = (255, 0, 0)
    pygame.draw.rect(client_display, (128, 128, 128), (x - width / 2, y - offset - height, width, height))
    pygame.draw.rect(client_display, color, (x - width / 2, y - offset - height, width * cof, height))

def DrawKills(text, surface, font_size, color, x, y):
    text_obj = pygame.font.SysFont(None, font_size).render(text, 1, color)
    text_rect = text_obj.get_rect()
    text_rect.center = (x, y)
    surface.blit(text_obj, text_rect)

def ClearWindow(display, texture):
    for i in range(0, 2) :
        for j in range(0, 3) :
            field_rect = pygame.Rect(j * 300, i * 300, 300, 300)
            display.blit(texture, field_rect)
    #text = pygame.transform.chop(texture, pygame.Rect(0, 0, 300, 200))
    for j in range(0, 3) :
        display.blit(texture, (j * 300, 600), (0, 0, 300, 200))
    #print(cof, ' ', x, ' ', y)
# =======================================================================
# Main program statements
# =======================================================================

#pygame.init()

screenXY = SCREEN_WIDTH, SCREEN_HEIGHT = 800, 800
flipX = False
flipY = True
client_display = None
Player_ID = 0
user_login = ''

user_state = None
server_state = None

player1_stats = None
player2_stats = None

is_exit = False

#client_display = pygame.display.set_mode(screenXY)
def start(display, login, ip) :
    global client_display, user_state, server_state, Player_ID, is_exit, user_login, player1_stats, player2_stats
    client_display = display
    user_login = login


    is_exit = False

# Instantiate clock to help control the framerate.
    client_clock = pygame.time.Clock()

    # Background color of the game pad.

    # Font object for rendering text onto display surface.
    fnt = pygame.font.SysFont("Arial", 14)

    hull_surf = pygame.image.load('hull.png').convert()
    hull_surf.set_colorkey((255, 255, 255))
    hull_surf = pygame.transform.rotate(hull_surf, -90)

    turret_surf = pygame.image.load('turret.png').convert()
    turret_surf.set_colorkey((255, 0, 0))
    turret_surf = pygame.transform.rotate(turret_surf, -90)

    field_surf = pygame.image.load('th.jpeg').convert()
    #field_surf = pygame.transform.chop(field_surf, pygame.Rect(0, 0, 300, 300))


    Player_ID = 0

    parser = argparse.ArgumentParser(description='Input client parameters.')
    # Example IP address used here; edit this line.
    print(ip)
    parser.add_argument('serverIP', type=str, nargs='?', default=ip)
    args = parser.parse_args()
    print("args:", args.serverIP)

    # Initialize the state dictionary
    user_state = {}
    server_state = {}

    # Note, the connection can take place in the NetworkListener or here.
    # This "connection" is an instatiation of the EndPoint class that is done in the Connection.py file.
    # Note, if you do this here, you have to call the "DoConnect" method, not the "Connect" method that
    # is indicated on the web site.
    # connection.DoConnect((args.serverIP, 4330))
    #connection.DoConnect((args.serverIP, 4330))
    network_listener = NetworkListener(args.serverIP, 4330)

    framerate_limit = 30
    flip_timer = 0.0

    print(Player_ID)

    while True:

        dt_s = float(client_clock.tick(framerate_limit) * 1e-3)
        # client_clock.tick(framerate_limit)

        connection.Pump()
        if Player_ID != 0:
             #print "user_state", user_state
            connection.Send(user_state)

        object_methods = [method_name for method_name in dir(connection)
                          if callable(getattr(connection, method_name))]

        network_listener.Pump()

        checkforUserInput(user_state)
        if is_exit :
            connection.Close()
            object_methods = [method_name for method_name in dir(network_listener)
                              if callable(getattr(network_listener, method_name))]
            print('close')
            player1_stats = None
            player2_stats = None
            break;

        client_display.fill((0, 0, 0))
        #ClearWindow(display, field_surf)

        DrawWalls()
        if 'tanks' in server_state :
            for tank_data in server_state['tanks'] :
                DrawImage(hull_surf, tank_data[0], tank_data[1], tank_data[2])

        if 'turrets' in server_state :
            for turret in server_state['turrets'] :
                DrawImage(turret_surf, turret[0], turret[1], turret[2])

        if 'bullets' in server_state :
            for bullet in server_state['bullets'] :
                pygame.draw.circle(client_display, (255, 0, 0), (bullet[0], bullet[1]), round(bullet[2]))

        if 'healths' in server_state :
            #print(Player_ID)
            position1 = (server_state['tanks'][0][0], server_state['tanks'][0][1])
            DrawHealth(position1, (Player_ID == 1), server_state['healths'][0] / 200)
            position2 = (server_state['tanks'][1][0], server_state['tanks'][1][1])
            DrawHealth(position2, (Player_ID == 2), server_state['healths'][1] / 200)
            #print(server_state['healths'][0])
        if 'kills' in server_state :
            kill1 = server_state['kills'][0]
            kill2 = server_state['kills'][1]
            color1 = (255, 0, 0)
            color2 = (0, 255, 0)
            if Player_ID == 1 :
                color1, color2 = color2, color1
            DrawKills('kills = ' + str(kill1), display, 25, color1, 50, 825)
            if player1_stats != None and player1_stats.username != '' :
                DrawKills('player: ' + player1_stats.username + ' ' + str(player1_stats.killed) + '/' + str(player1_stats.died), display, 25, color1, 150, 825)
            DrawKills('kills = ' + str(kill2), display, 25, color2, 750, 825)
            if player2_stats != None and player2_stats.username != '':
                DrawKills('player: ' + player2_stats.username + ' ' + str(player2_stats.killed) + '/' + str(
                    player2_stats.died), display, 25, color2, 650, 825)

        pygame.display.update()
