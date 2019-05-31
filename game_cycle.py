import pygame
from pygame.locals import *
from Box2D import *
import math
from vecpy import *
import time
import random
import database
import numpy as np
import sklearn as sk

from PodSixNet.Server import Server
from PodSixNet.Channel import Channel
from sklearn.svm import SVR

import socket
from collections import namedtuple

g = 10
start_time = time.time()

class ClientChannel(Channel):
    def __init__(self, *args, **kwargs):
        Channel.__init__(self, *args, **kwargs)

    def Network_CN(self, data):
        global CND

        clientname = 'C' + str(data['ID'])
        CND.CN_data[clientname]['state'] = data
        CND.CN_data[clientname]['sendCount'] += 1
        if data['mouseB1'] == 'D':
            CND.CN_data[clientname]['mouseXY'] = data['mouseXY']

        object_methods = [method_name for method_name in dir(self)
            if callable(getattr(self, method_name))]

        track = 10


    def Network_DS(self, data):
        pass

    def Network_sign_in(self, data):
        global player1_stats, player2_stats, channels
        if data['action'] == 'sign_in' :
            if data['ID'] == 1 :
                player1_stats = database.Statistics(data['login'])
                reply = {'action':'get_stats', 'ID': 1, 'username':player1_stats.username, 'killed':player1_stats.killed,
                         'died': player1_stats.died, 'played_games' : player1_stats.played_games}
                self.Send(reply)
                if(channels['2'] != None) :
                    channels['2'].Send(reply)
                if (player2_stats != None):
                    reply = {'action': 'get_stats', 'ID': 2, 'username': player2_stats.username,
                             'killed': player2_stats.killed,
                             'died': player2_stats.died, 'played_games': player2_stats.played_games}
                    self.Send(reply)
            if data['ID'] == 2 :
                player2_stats = database.Statistics(data['login'])
                reply = {'action' : 'get_stats', 'ID':2, 'username':player2_stats.username, 'killed':player2_stats.killed,
                         'died': player2_stats.died, 'played_games' : player2_stats.played_games}
                self.Send(reply)
                if (channels['1'] != None) :
                    channels['1'].Send(reply)
                if(player1_stats != None) :
                    reply = {'action': 'get_stats', 'ID': 1, 'username': player1_stats.username,
                             'killed': player1_stats.killed,
                             'died': player1_stats.died, 'played_games': player1_stats.played_games}
                    self.Send(reply)

    def Close(self):
        global channels, tank1_kills, tank2_kills
        print("deleting player")
        if self == channels['1'] :
            channels['1'] = None
            player1_stats.killed += tank1_kills
            player1_stats.died += tank2_kills
            player1_stats.played_games += 1
            player1_stats.save_user_to_db()
            if channels['2'] != None :
                player2_stats.killed += tank2_kills
                player2_stats.died += tank1_kills
                player2_stats.played_games += 1
                player2_stats.save_user_to_db()
        if self == channels['2'] :
            channels['2'] = None
            player2_stats.killed += tank2_kills
            player2_stats.died += tank1_kills
            player2_stats.played_games += 1
            player2_stats.save_user_to_db()
            if channels['1'] != None :
                player1_stats.killed += tank1_kills
                player1_stats.died += tank2_kills
                player1_stats.played_games += 1
                player1_stats.save_user_to_db()
        tank1_kills = 0
        tank2_kills = 0

channels = {'1' : None, '2' : None}

class GameServer(Server):
    channelClass = ClientChannel

    def __init__(self, *args, **kwargs):
        Server.__init__(self, *args, **kwargs)
        self.client_count = 2

    # This runs when each client connects.
    def Connected(self, channel, addr):
        global tanks, bot_mode
        print ('new connection (channel, addr):', channel, addr)

        if channels['1'] == None:
            channel.Send({"action": "hello", "P_ID": 1})
            channels['1'] = channel
            tanks[0].hull.respawn()
            tanks[1].hull.respawn()
        elif channels['2'] == None or bot_mode != '':
            channel.Send({"action": "hello", "P_ID": 2})
            channels['2'] = channel
            tanks[0].hull.respawn()
            tanks[1].hull.respawn()
        else:
            channel.Send({"action": "hello", "P_ID": 0})

    def SendInformation(self, data):
        data['action'] = 'action'

        for channel in channels :
            if channels[channel] != None :
                channels[channel].Send(data)

class ClientData:
    def __init__(self):
        # CN_data is a dictionary of dictionaries.
        self.loopsSinceLastQuietCheck = 0

        self.CN_data = {}
        for m in range(1, 3):
            # Set the player's Cm key value to a dictionary.
            self.CN_data['C' + str(m)] = {'state': None, 'sendCount': 0, 'previousSendCount': 0, 'active': False,
                                          'historyXY': []}

    def checkForQuietClients(self):
        self.loopsSinceLastQuietCheck += 1
        if self.loopsSinceLastQuietCheck > 20:
            self.loopsSinceLastQuietCheck = 0
            for clientname in CND.CN_data:
                # Check for the no change case (client is quiet).
                countChange = CND.CN_data[clientname]['sendCount'] - CND.CN_data[clientname]['previousSendCount']
                if countChange == 0:
                    CND.CN_data[clientname]['active'] = False
                else:
                    CND.CN_data[clientname]['active'] = True
                # Update the previous value for use in the next comparison.
                CND.CN_data[clientname]['previousSendCount'] = CND.CN_data[clientname]['sendCount']

def rotate(vector, angle):
    x = math.cos(angle) * vector.x - math.sin(angle) * vector.y
    y = math.sin(angle) * vector.x + math.cos(angle) * vector.y
    return Vector(x, y)

def get_angle(x1, y1, x2, y2):
    if(x1 == x2) :
        if(y1 > y2):
            return -math.pi / 2
        else :
            return +math.pi / 2
    else :
        tan = (y2 - y1) / (x2 - x1)
        angle = math.atan(tan)
        if(x2 - x1 < 0) :
            angle += math.pi
        return angle

def dist2d(x1, y1, x2, y2) :
    dx = x2 - x1
    dy = y2 - y1
    return math.sqrt(dx * dx + dy * dy)

def rectangle_friction(center_x, center_y, width, height, angle, mass, friction, velocity, angular_velocity):
    width_cnt = 5
    height_cnt = 5
    cell_width = width / width_cnt
    cell_height = height / height_cnt
    cell_mass = mass / (width_cnt * height_cnt)

    force = Vector(0, 0)
    moment_force = 0

    norm_for_h = Vector(math.cos(angle), math.sin(angle))
    norm_for_w = Vector(math.cos(angle + math.pi / 2), math.sin(angle + math.pi / 2))

    for i in range(0, width_cnt) :
        for j in range(0, height_cnt) :
            w = (i + 0.5) * cell_width - width / 2
            h = (j + 0.5) * cell_height - height / 2

            r = rotate(Vector(center_x, center_y), angle) + norm_for_h * h + norm_for_w * w

            r90 = Vector(-r.y, r.x) ^ 0

            w_v = r90 * angular_velocity * r.length;

            v = Vector(velocity.x, velocity.y) + w_v

            if v.length == 0 :
                continue

            cell_force =  (v ^ 0) * cell_mass * g * friction * -1

            force = force + cell_force

            cell_moment_force = r90.proj(cell_force).length * r.length
            if(r90.dot(cell_force) < 0) :
                cell_moment_force *= -1

            moment_force = moment_force + cell_moment_force

    return (force, moment_force)

def caterpillar_friction(center_x, center_y, width, height, angle, mass, friction, velocity, angular_velocity):
    width_cnt = 5
    height_cnt = 5
    cell_width = width / width_cnt
    cell_height = height / height_cnt
    cell_mass = mass / (width_cnt * height_cnt)

    force = Vector(0, 0)
    moment_force = 0

    norm_for_h = Vector(math.cos(angle), math.sin(angle))
    norm_for_w = Vector(math.cos(angle + math.pi / 2), math.sin(angle + math.pi / 2))

    for i in range(0, width_cnt) :
        for j in range(0, height_cnt) :
            w = (i + 0.5) * cell_width - width / 2
            h = (j + 0.5) * cell_height - height / 2

            r = rotate(Vector(center_x, center_y), angle) + norm_for_h * h + norm_for_w * w

            r90 = Vector(-r.y, r.x) ^ 0

            w_v = r90 * angular_velocity * r.length;

            v = Vector(velocity.x, velocity.y) + w_v

            v = norm_for_w.proj(v)

            if v.length == 0 :
                continue

            cell_force =  (v ^ 0) * cell_mass * g * friction * -1

            force = force + cell_force

            cell_moment_force = r90.proj(cell_force).length * r.length
            if(r90.dot(cell_force) < 0) :
                cell_moment_force *= -1

            moment_force = moment_force + cell_moment_force

    return (force, moment_force)

class fwQueryCallback(b2QueryCallback):
    # Checks for objects at particular locations (p) like under the cursor.

    def __init__(self, p):
        super(fwQueryCallback, self).__init__()
        self.point = p
        self.fixture = None

    def ReportFixture(self, fixture):
        body = fixture.body
        if body.type == b2_dynamicBody:
            inside = fixture.TestPoint(self.point)
            if inside:
                self.fixture = fixture
                # We found the object, so stop the query
                return False
        # Continue the query
        return True

def dist(vector) :
    return math.sqrt(vector.x * vector.x + vector.y * vector.y)

def same_sign(a, b) :
    if(a > 0 and b > 0) or (a < 0 and b < 0):
        return True
    else :
        return False

class Environment:

    def __init__(self, screensize_tuple, world, screen):
        self.world = world

        self.viewZoom = 10.0
        self.viewCenter = b2Vec2(0, 0.0)
        self.viewOffset = b2Vec2(0, 0)
        self.screenSize = b2Vec2(*screensize_tuple)
        self.rMouseDown = False
        # self.textLine           = 30
        # self.font               = None
        # self.fps                = 0
        self.mouseWorld = Vector(0, 0)
        self.mouseJoint = None
        self.fire = False

        # Needed for the mousejoint
        self.groundbody = self.world.CreateBody()

        self.flipX = False
        self.flipY = True

        # pass viewZoom to init in DrawToScreen class. Call the DrawToScreen function by use of the "renderer" name.
        self.renderer = DrawToScreen(self.viewZoom, screen)

        self.pointSize = 2.5

        self.colors = {
            'mouse_point': b2Color(1, 0, 0),
            'bomb_center': b2Color(0, 0, 1.0),
            'joint_line': b2Color(0.8, 0.8, 0.8),
            'contact_add': b2Color(0.3, 0.95, 0.3),
            'contact_persist': b2Color(0.3, 0.3, 0.95),
            'contact_normal': b2Color(0.4, 0.9, 0.4),
            'force_point': b2Color(0, 1, 0)
        }

        self.pressedKeys = {'UP': False, 'DOWN':False, 'LEFT':False, 'RIGHT':False}

    def MouseDown(self, p):
        """
        Indicates that there was a left click at point p (world coordinates)
        """

        # If there is already a mouse joint just get out of here.
        self.fire = True

        if self.mouseJoint != None:
            return


        # Create a mouse joint on the selected body (assuming it's dynamic)
        # Make a small box.
        aabb = b2AABB(lowerBound=p - (0.001, 0.001), upperBound=p + (0.001, 0.001))

        # Query the world for overlapping shapes.
        query = fwQueryCallback(p)
        self.world.QueryAABB(query, aabb)

        if query.fixture:
            body = query.fixture.body
            # A body was selected, create the mouse joint
            self.mouseJoint = self.world.CreateMouseJoint(
                bodyA=self.groundbody,
                bodyB=body,
                target=p,
                maxForce=1000.0 * body.mass)
            body.awake = True

    def MouseUp(self, p):
        """
        Left mouse button up.
        """
        if self.mouseJoint:
            self.world.DestroyJoint(self.mouseJoint)
            self.mouseJoint = None

    def MouseMove(self, p):
        """
        Mouse moved to point p, in world coordinates.
        """
        self.mouseWorld = p
        if self.mouseJoint:
            self.mouseJoint.target = p

    def Keyboard_Event(self, key, down=True):
        if down:
            if key == K_UP:  # Zoom in
                self.pressedKeys['UP'] = True
            elif key == K_LEFT:  # Zoom out
                self.pressedKeys['LEFT'] = True
            elif key == K_RIGHT:
                self.pressedKeys['RIGHT'] = True
            elif key == K_DOWN:
                self.pressedKeys['DOWN'] = True

            else:
                pass
        # If up
        else:
            if key == K_UP:  # Zoom in
                self.pressedKeys['UP'] = False
            elif key == K_LEFT:  # Zoom out
                self.pressedKeys['LEFT'] = False
            elif key == K_RIGHT:
                self.pressedKeys['RIGHT'] = False
            elif key == K_DOWN:
                self.pressedKeys['DOWN'] = False

            else:
                pass

    def checkEvents(self):
        """
        Check for pygame events (mainly keyboard/mouse events).
        Passes the events onto the GUI also.
        """
        # print "checkEvents"
        for event in pygame.event.get():
            # print "event.type = ", event.type
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                print
                "early bailout"
                return False
            elif event.type == KEYDOWN:
                self.Keyboard_Event(event.key, down=True)
            elif event.type == KEYUP:
                self.Keyboard_Event(event.key, down=False)
            elif event.type == MOUSEBUTTONDOWN:
                # print "in MouseButtonDown block"
                p = self.ConvertScreenToWorld(*event.pos)
                if event.button == 1:  # left
                    self.MouseDown(p)
                elif event.button == 2:  # middle
                    pass
                elif event.button == 3:  # right
                    self.rMouseDown = True
                elif event.button == 4:
                    self.viewZoom *= 1.1
                    # print "self.viewZoom", self.viewZoom
                elif event.button == 5:
                    self.viewZoom /= 1.1
            elif event.type == MOUSEBUTTONUP:
                p = self.ConvertScreenToWorld(*event.pos)
                if event.button == 3:  # right
                    self.rMouseDown = False
                else:
                    self.MouseUp(p)
            elif event.type == MOUSEMOTION:

                p = self.ConvertScreenToWorld(*event.pos)
                self.MouseMove(p)
                if self.rMouseDown:
                    print
                    "in mousemotion block", event.pos, event.rel[0], event.rel[1]
                    self.viewCenter -= (event.rel[0] / 1.0, -event.rel[1] / 1.0)  # ... it was /5.0

        return True

    def ConvertScreenToWorld(self, x, y):
        # self.viewOffset = self.viewCenter - self.screenSize/2
        self.viewOffset = self.viewCenter
        return b2Vec2((x + self.viewOffset.x) / self.viewZoom,
                      ((self.screenSize.y - y + self.viewOffset.y) / self.viewZoom))

    def ConvertWorldtoScreen(self, point):
        """
        Convert from world to screen coordinates.
        In the class instance, we store a zoom factor, an offset indicating where
        the view extents start at, and the screen size (in pixels).
        """

        # The zoom factor works to define and scale the relationship between pixels (screen) and meters (world).

        self.viewOffset = self.viewCenter
        x = (point.x * self.viewZoom) - self.viewOffset.x
        if self.flipX:
            x = self.screenSize.x - x
        y = (point.y * self.viewZoom) - self.viewOffset.y
        if self.flipY:
            y = self.screenSize.y - y
        return (int(round(x)), int(round(y)))  # return tuple of integers

    def drawMouseJoint(self):
        if self.mouseJoint:
            p1_screen = self.ConvertWorldtoScreen(
                self.mouseJoint.anchorB)  # The point on the object converted to screen coordinates.
            p2_screen = self.ConvertWorldtoScreen(
                self.mouseJoint.target)  # The current mouse position converted to screen coordinates.

            self.renderer.DrawPoint(p1_screen, self.pointSize, self.colors['mouse_point'])
            self.renderer.DrawPoint(p2_screen, self.pointSize, self.colors['mouse_point'])
            self.renderer.DrawSegment(p1_screen, p2_screen, self.colors['joint_line'])

    def drawForcePoint(self, forcePoint_2d_m):
        forcePoint_screen = self.ConvertWorldtoScreen(forcePoint_2d_m)
        self.renderer.DrawPoint(forcePoint_screen, self.pointSize, self.colors['force_point'])

class DrawToScreen:

    def __init__(self, viewZoom, screen):
        self.viewZoom = viewZoom
        self.surface = screen

    def DrawPoint(self, p, size, color):
        """
        Draw a single point at point p given a pixel size and color.
        """
        self.DrawCircle(p, size / self.viewZoom, color, drawwidth=0)

    def DrawSegment(self, p1, p2, color):
        """
        Draw the line segment from p1-p2 with the specified color.
        """
        pygame.draw.aaline(self.surface, (255, 255, 255), p1, p2)

    def DrawCircle(self, center, radius, color, drawwidth=1):
        """
        Draw a wireframe circle given the center, radius, axis of orientation and color.
        """
        radius *= self.viewZoom
        if radius < 1:
            radius = 1
        else:
            radius = int(radius)
        pygame.draw.circle(self.surface, color.bytes, center, radius, drawwidth)

    def DrawImage(self, texture, center, angle, flipX, flipY):
        draw_surf = pygame.transform.flip(texture, flipX, flipY)
        draw_surf = pygame.transform.rotate(draw_surf, angle)
        draw_rect = draw_surf.get_rect(center=center)
        self.surface.blit(draw_surf, draw_rect)


flag = False
forces = dict()

class Bullet :
    def __init__ (self, world, position, angle, env, player, train) :
        self.speed = 250
        self.mass = 2000
        self.body = world.CreateDynamicBody(position=position)
        self.body.userData = self
        self.body.mass = self.mass
        self.env = env
        self.radius = 0.5
        self.player = player
        self.damage = 20
        self.train = train

        self.is_collision = False

        self.body.CreateCircleFixture(radius=self.radius, friction=0, restitution = 1)
        self.body.bullet = True

        v = Vector(math.cos(angle), math.sin(angle)) * self.speed
        self.body.linearVelocity = b2Vec2(v.x, v.y)

    def draw (self):
        position = self.env.ConvertWorldtoScreen(self.body.position)
        pygame.draw.circle(self.env.renderer.surface, (255, 0, 0), position, round(self.radius * self.env.viewZoom))


class Hull :
    def __init__ (self, pic_path, x, y, ang, theWorld, e, player) :
        self.hull_surf = pygame.image.load(pic_path).convert()
        self.hull_surf = pygame.transform.rotate(self.hull_surf, -90)
        self.world = theWorld
        width = self.hull_surf.get_width() / e.viewZoom
        height = self.hull_surf.get_height() / e.viewZoom
        self.env = e
        self.player = player

        self.mass = 20000
        self.hull_surf.set_colorkey((255, 255, 255))
        self.body = theWorld.CreateDynamicBody(position=e.ConvertScreenToWorld(x, y), angle=ang)
        self.body.CreatePolygonFixture(box=(width / 2, height / 2), density = self.mass / width / height, friction=0.00, restitution=0)
        self.body.userData = self

        self.health = 200

        self.friction = 4
        self.max_force = 1000000
        self.internal_friction = 500000
        self.radius = 2.5
        self.power_left = 0
        self.power_right = 0

    def get_damage(self, damage):
        global tank1_iskill, tank2_iskill
        self.health -= damage
        if(self.health <= 0) :
            if self.player == 1 :
                tank1_iskill = True
            if self.player == 2 :
                tank2_iskill = True

    def respawn(self):
        self.health = 200
        self.body.angle = 0
        self.body.position = self.env.ConvertScreenToWorld(*(random.choice(
            [(100, 100), (SCREEN_WIDTH - 100, 100), (100, SCREEN_HEIGHT - 100),
             (SCREEN_WIDTH - 100, SCREEN_HEIGHT - 100)])))

    def update_motors(self, keys):
        up = keys['UP']
        down = keys['DOWN']
        left = keys['LEFT']
        right = keys['RIGHT']

        if up and (left or right) :
            if left :
                self.power_left = 1000000
                self.power_right = 15000000
            else :
                self.power_left = 15000000
                self.power_right = 1000000
            return
        if up :
            self.power_left = 10000000
            self.power_right = 10000000
            return
        if down :
            self.power_left = -10000000
            self.power_right = -10000000
            return
        if left :
            self.power_left = -10000000
            self.power_right = 10000000
            return
        if right :
            self.power_left = 10000000
            self.power_right = -10000000
            return
        self.power_left = 0
        self.power_right = 0
        return

    def getForces(self):
        global flag
        speed_v = Vector(self.body.linearVelocity.x, self.body.linearVelocity.y)
        dir_v = Vector(math.cos(self.body.angle), math.sin(self.body.angle))
        v_proj_dir = dir_v.proj(speed_v)
        v = v_proj_dir.length * (v_proj_dir.dot(dir_v) / v_proj_dir.length)
        if speed_v.length == 0 :
            v = 0

        #v = dist(self.body.linearVelocity)

        left_v = v - self.body.angularVelocity * self.radius
        right_v = v + self.body.angularVelocity * self.radius
        #print(left_v, ' ', right_v)

        left_f = 0
        right_f = 0

        if flag == True :
            flag = True

        if(left_v == 0) or (same_sign(self.power_left, left_v) and self.power_left / left_v > self.internal_friction):
            if self.power_left < 0 :
                left_f = -self.max_force
            if self.power_left > 0 :
                left_f = self.max_force
            if left_v != 0 :
                if(left_f > 0) :
                    left_f = min(left_f, self.power_left / math.fabs(left_v))
                else :
                    left_f = max(left_f, self.power_left / math.fabs(left_v))
            if left_f > 0 :
                left_f -= self.internal_friction
            if left_f < 0 :
                left_f += self.internal_friction
        else :
            if not same_sign(self.power_left, left_v) :
                if self.power_left < 0:
                    left_f = -self.max_force
                if self.power_left > 0:
                    left_f = self.max_force
            else :
                left_f = 0

        if (right_v == 0) or (same_sign(self.power_right, right_v) and self.power_right / right_v > self.internal_friction):
            if self.power_right < 0:
                right_f = -self.max_force
            if self.power_right > 0:
                right_f = self.max_force
            if right_v != 0 :
                if (right_f > 0):
                    right_f = min(right_f, self.power_right / math.fabs(right_v))
                else:
                    right_f = max(right_f, self.power_right / math.fabs(right_v))
            if right_f > 0:
                right_f -= self.internal_friction
            if right_f < 0:
                right_f += self.internal_friction
        else:
            if not same_sign(self.power_right, right_v) :
                if self.power_right < 0:
                    right_f = -self.max_force
                if self.power_right > 0:
                    right_f = self.max_force
            else :
                right_f = 0

        return (left_f, right_f)

    def updatePhysics (self) :
        global flag
        global x1, y1, x2, y2
        left_f, right_f = self.getForces()
        #if time.time() - start_time > 5 :
        #    left_f = right_f = 0


        if (left_f != 0 and left_f != None) and (right_f != 0 and right_f != None):
            #print(left_f, ' ', right_f)
            flag = True
        #print(self.power_left, ' ', self.power_right)

        x = math.cos(self.body.angle)
        y = math.sin(self.body.angle)

        left_friction_force, left_friction_moment, right_friction_force, right_friction_moment = Vector(0, 0), 0, Vector(0, 0), 0
        #speed_v = Vector(x, y).proj(Vector(self.body.linearVelocity.x, self.body.linearVelocity.y))
        #speed = speed_v.length
        #if(speed_v.dot(Vector(x, y)) < 0):
        #    speed *= -1
        left_caterpillar_friction_force, left_caterpillar_friction_moment = Vector(0, 0), 0
        right_caterpillar_friction_force, right_caterpillar_friction_moment = Vector(0, 0), 0

        if self.power_left != 0 and self.power_left != 1000000 :
            point = self.body.GetWorldPoint(b2Vec2(0, self.radius))
            self.body.ApplyForce(force=b2Vec2(x * left_f, y * left_f), point=point, wake=True)
            left_caterpillar_friction_force, left_caterpillar_friction_moment = caterpillar_friction(center_x = 0, center_y = self.radius, width = 1.5, height = 7.5, angle = self.body.angle, mass = self.mass / 2,
                                                                       friction = self.friction, velocity = self.body.linearVelocity, angular_velocity = self.body.angularVelocity)
        else :
            friction = self.friction
            if self.power_left == 1000000 :
                friction /= 1.5
            left_friction_force, left_friction_moment = rectangle_friction(center_x = 0, center_y = self.radius, width = 1.5, height = 7.5, angle = self.body.angle, mass = self.mass / 2,
                                                                       friction = friction, velocity = self.body.linearVelocity, angular_velocity = self.body.angularVelocity)
        #print('good')
        if self.power_right != 0 and self.power_right != 1000000:
            point = self.body.GetWorldPoint(b2Vec2(0, -self.radius))
            self.body.ApplyForce(force=b2Vec2(x * right_f, y * right_f), point=point, wake=True)
            if(self.body.linearVelocity.y != 0) :
                tr = 0
            right_caterpillar_friction_force, right_caterpillar_friction_moment = caterpillar_friction(center_x=0, center_y=-self.radius, width=1.5,
                                                                   height=7.5, angle=self.body.angle, mass=self.mass / 2,
                                                                   friction=self.friction,
                                                                   velocity=self.body.linearVelocity,
                                                                   angular_velocity=self.body.angularVelocity)
            #else:
        else :
            friction = self.friction
            if self.power_right == 1000000 :
                friction /= 1.5
            right_friction_force, right_friction_moment = rectangle_friction(center_x=0, center_y=-self.radius, width=1.5,
                                                                   height=7.5, angle=self.body.angle, mass=self.mass / 2,
                                                                   friction=friction,
                                                                   velocity=self.body.linearVelocity,
                                                                   angular_velocity=self.body.angularVelocity)

        #rotate(left_friction_force, self.body.angle)
        #rotate(right_friction_force, self.body.angle)
        #print(left_f, ' ', right_f)
        friction_force = left_friction_force + right_friction_force
        friction_moment = left_friction_moment + right_friction_moment

        friction_force += left_caterpillar_friction_force  + right_caterpillar_friction_force
        friction_moment += left_caterpillar_friction_moment + right_caterpillar_friction_moment

        #print(left_friction_moment + right_friction_moment, ' ', left_caterpillar_friction_moment + right_caterpillar_friction_moment, ' ' , friction_moment)
        #print(left_friction_moment, ' ', right_friction_moment)

        speed = Vector(self.body.linearVelocity.x, self.body.linearVelocity.y)

        #if(speed.length != 0) :
        #    print(rotate(Vector(x, y), math.pi / 2).proj(left_caterpillar_friction_force + right_caterpillar_friction_force).length, ' ', left_f + right_f)

        vec = Vector(self.body.position.x, self.body.position.y)
        if friction_force.length != 0 :
            vec = vec + (friction_force ^ 0)
        forces['friction'] = [Vector(self.body.position.x, self.body.position.y), Vector(vec.x, vec.y)]

        vec = rotate(Vector(0, self.radius), self.body.angle)
        pos = Vector(self.body.position.x, self.body.position.y)
        if left_f != 0 :
            forces['left_f'] = [Vector((pos + vec).x, (pos + vec).y), pos + vec + ((Vector(x, y) * left_f) ^ 0)]

        vec = rotate(Vector(0, -self.radius), self.body.angle)
        pos = Vector(self.body.position.x, self.body.position.y)
        if right_f != 0 :
            forces['right_f'] = [Vector((pos + vec).x, (pos + vec).y), pos + vec + ((Vector(x, y) * right_f) ^ 0)]

        #print(x2, ' ', y2, ' ', vec, ' ', self.body.position)

        #print(left_caterpillar_friction_force , ' ', right_caterpillar_friction_force, ' ', self.body.linearVelocity.y)
        #print(self.body.linearVelocity.y)

        #if self.power_left == 0 and self.power_right == 0 :
        if True :
            #print(left_friction_moment, ' ', right_friction_moment)
            #print(left_friction_force, '  ', right_friction_force)
            #print(self.body.linearVelocity, ' ', self.body.angularVelocity)
            speed = Vector(self.body.linearVelocity.x, self.body.linearVelocity.y)
            if speed != 0 :
                if (speed * self.body.mass + friction_force * TIME_STEP).dot(speed) < 0 :
                    friction_force = speed * self.body.mass * (1 / TIME_STEP) * -1
                self.body.ApplyForce(force=b2Vec2(friction_force.x, friction_force.y), point=self.body.GetWorldPoint(b2Vec2(0, 0)), wake = True)
                #print(friction_force, ' ', rotate(Vector(x, y), math.pi / 2).proj(friction_force))

            angular_speed = self.body.angularVelocity

            if math.fabs(friction_moment * TIME_STEP) > math.fabs(angular_speed * self.body.inertia):
                friction_moment = -angular_speed * self.body.inertia * (1 / TIME_STEP)
            self.body.ApplyTorque(torque=friction_moment, wake = True)
        '''left_f = 100000
        point = self.body.GetWorldPoint(b2Vec2(0, -self.radius))
        self.body.ApplyForce(force=b2Vec2(x * left_f, y * left_f), point=point, wake=True)
        point = self.body.GetWorldPoint(b2Vec2(0, self.radius))
        self.body.ApplyForce(force=b2Vec2(x * -left_f, y * -left_f), point=point, wake=True)'''

    def draw(self):
        angle = math.degrees(self.body.angle)
        position = self.env.ConvertWorldtoScreen(self.body.position)
        data['tanks'].append((position[0], position[1], angle))
        self.env.renderer.DrawImage(self.hull_surf, position, angle, self.env.flipX, self.env.flipY)

class Turret :
    def __init__ (self, pic_path, ang, e, hull, player) :
        self.turret_surf = pygame.image.load(pic_path).convert()
        self.turret_surf.set_colorkey((255, 0, 0))
        self.turret_surf = pygame.transform.rotate(self.turret_surf, -90)
        self.width = self.turret_surf.get_width()
        self.height = self.turret_surf.get_height()
        print(self.width)
        self.center_width = -(self.width / 2 - 55.5) / e.viewZoom
        self.center_height = 0

        self.player = player

        self.env = e

        self.hull = hull

        self.angle = 0
        self.angular_speed = 0
        self.angular_acceleration = 0
        self.angular_max_speed = math.radians(130)
        self.angular_max_acceleration = 120
        self.last_shoot_time = 0
        self.reload_time = 0.4

    def update(self):
        global TIME_STEP
        self.angular_speed += self.angular_acceleration * TIME_STEP
        if(self.angular_speed < -self.angular_max_speed) :
            self.angular_speed = -self.angular_max_speed
        if (self.angular_speed > self.angular_max_speed):
            self.angular_speed = self.angular_max_speed
        self.angle += self.angular_speed * TIME_STEP
        if self.angle > math.radians(270) :
            self.angle -= math.pi * 2
        if self.angle < math.radians(-90) :
            self.angle += math.pi * 2

    def abs_angle(self):
        angle = self.hull.body.angle + self.angle
        while angle > math.radians(270) :
            angle -= math.pi * 2
        while angle < math.radians(-90) :
            angle += math.pi * 2
        return angle

    def fire(self, train = -1):
        global bullets
        if time.time() - self.last_shoot_time < self.reload_time :
            return
        angle = self.abs_angle()
        world_position = Vector(self.hull.body.position.x, self.hull.body.position.y) + rotate(Vector(self.center_width + self.width / 2 / 10, 0), angle)
        bullets.append(Bullet(self.hull.world, b2Vec2(world_position.x, world_position.y), angle, self.env, player = self.player, train = train))
        self.last_shoot_time = time.time()

    def draw(self, hull_position, hull_angle):
        angle = self.abs_angle()
        world_position = Vector(hull_position.x, hull_position.y) + rotate(Vector(self.center_width, self.center_height), angle)
        position = self.env.ConvertWorldtoScreen(b2Vec2(world_position.x, world_position.y))
        data['turrets'].append((position[0], position[1], math.degrees(angle)))
        self.env.renderer.DrawImage(self.turret_surf, position, math.degrees(angle), self.env.flipX, self.env.flipY)

class Tank :
    def __init__(self, hull_picture_path, turret_picture_path, x, y, ang, theWorld, e, player) :
        self.hull = Hull(hull_picture_path, x, y, ang, theWorld, e, player)
        self.turret = Turret(turret_picture_path, 0, e, self.hull, player)
        self.player = player

    def update_motors(self, keys):
        self.hull.update_motors(keys)

    def updatePhysics(self):
        self.hull.updatePhysics()
        self.turret.update()

    def draw(self):
        self.hull.draw()
        self.turret.draw(self.hull.body.position, self.hull.body.angle)

def update_contorls_my_tank(tank, env):
    up = env.pressedKeys['UP']
    down = env.pressedKeys['DOWN']
    left = env.pressedKeys['LEFT']
    right = env.pressedKeys['RIGHT']

    tank.hull.power_left = 0
    tank.hull.power_right = 0
    if up and (left or right):
        if left:
            tank.hull.power_left = 1000000
            tank.hull.power_right = 15000000
        else:
            tank.hull.power_left = 15000000
            tank.hull.power_right = 1000000
    elif down and (left or right) :
        if right:
            tank.hull.power_left = 1000000
            tank.hull.power_right = -15000000
        else :
            tank.hull.power_left = -15000000
            tank.hull.power_right = 1000000
    elif up:
        tank.hull.power_left = 10000000
        tank.hull.power_right = 10000000
    elif down:
        tank.hull.power_left = -10000000
        tank.hull.power_right = -10000000
    elif left:
        tank.hull.power_left = -10000000
        tank.hull.power_right = 10000000
    elif right:
        tank.hull.power_left = 10000000
        tank.hull.power_right = -10000000

    turret_angle = tank.turret.abs_angle()
    mouse_angle = get_angle(tank.hull.body.position.x, tank.hull.body.position.y, env.mouseWorld.x, env.mouseWorld.y)
    #print(math.degrees(turret_angle), ' ', math.degrees(mouse_angle))
    #print(math.degrees(mouse_angle))
    if 0 <= turret_angle - mouse_angle <= math.pi or turret_angle - mouse_angle <= -math.pi :
        if(tank.turret.angular_acceleration > 0) :
            tank.turret.angular_speed = 0
        tank.turret.angular_acceleration = -math.radians(150)
        #print(1)
    else:
        if (tank.turret.angular_acceleration < 0) :
            tank.turret.angular_speed = 0
        tank.turret.angular_acceleration = math.radians(150)
        #print(2)

    if env.fire :
        env.fire = False
        tank.turret.fire()
        #print(3)

def update_controls_client(tank, user_state) :
    if type(user_state) != type({}) :
        return
    if not 'UP' in user_state :
        return
    up = user_state['UP'] == 'D'
    down = user_state['DOWN'] == 'D'
    left = user_state['LEFT'] == 'D'
    right = user_state['RIGHT'] == 'D'

    tank.hull.power_left = 0
    tank.hull.power_right = 0
    if up and (left or right):
        if left:
            tank.hull.power_left = 1000000
            tank.hull.power_right = 15000000
        else:
            tank.hull.power_left = 15000000
            tank.hull.power_right = 1000000
    elif down and (left or right):
        if right:
            tank.hull.power_left = 1000000
            tank.hull.power_right = -15000000
        else:
            tank.hull.power_left = -15000000
            tank.hull.power_right = 1000000
    elif up:
        tank.hull.power_left = 10000000
        tank.hull.power_right = 10000000
    elif down:
        tank.hull.power_left = -10000000
        tank.hull.power_right = -10000000
    elif left:
        tank.hull.power_left = -10000000
        tank.hull.power_right = 10000000
    elif right:
        tank.hull.power_left = 10000000
        tank.hull.power_right = -10000000

    position = tank.hull.env.ConvertScreenToWorld(user_state['mouseXY'][0], user_state['mouseXY'][1])
    turret_angle = tank.turret.abs_angle()
    mouse_angle = get_angle(tank.hull.body.position.x, tank.hull.body.position.y, position.x, position.y)
    # print(math.degrees(turret_angle), ' ', math.degrees(mouse_angle))
    # print(math.degrees(mouse_angle))
    if 0 <= turret_angle - mouse_angle <= math.pi or turret_angle - mouse_angle <= -math.pi:
        if (tank.turret.angular_acceleration > 0):
            tank.turret.angular_speed = 0
        tank.turret.angular_acceleration = -math.radians(150)
        # print(1)
    else:
        if (tank.turret.angular_acceleration < 0):
            tank.turret.angular_speed = 0
        tank.turret.angular_acceleration = math.radians(150)
        # print(2)

    if user_state['mouseB1'] == 'D':
        tank.turret.fire()

def update_bot() :
    global tanks, bot_mode, bot_time, training, svr_rbf
    if bot_mode == 'collect' :
        if time.time() - bot_time < 0.5 :
            return
        angle = get_angle(tanks[1].hull.body.position.x, tanks[1].hull.body.position.y, tanks[0].hull.body.position.x, tanks[0].hull.body.position.y)
        v = rotate(tanks[0].hull.body.linearVelocity, -angle)
        shoot_dir = angle + random.uniform(-math.pi / 8, math.pi / 8)
        tanks[1].turret.angle = shoot_dir - tanks[1].hull.body.angle
        if len(training) < 100 :
            tanks[1].turret.fire(len(training))
            training[str(len(training))] = (dist2d(tanks[1].hull.body.position.x, tanks[1].hull.body.position.y, tanks[0].hull.body.position.x, tanks[0].hull.body.position.y), v.x, v.y, shoot_dir - angle)
        else :
            tanks[1].turret.fire()

        bot_time = time.time()
    if bot_mode == 'attack' :
        if time.time() - bot_time > 0.5 :
            angle = get_angle(tanks[1].hull.body.position.x, tanks[1].hull.body.position.y,
                              tanks[0].hull.body.position.x, tanks[0].hull.body.position.y)
            v = rotate(tanks[0].hull.body.linearVelocity, -angle)
            d = dist2d(tanks[1].hull.body.position.x, tanks[1].hull.body.position.y,
                              tanks[0].hull.body.position.x, tanks[0].hull.body.position.y)

            dangle = svr_rbf.predict([[d, v.x, v.y]])
            #dangle[0] = 0
            shoot_dir = angle + dangle[0]
            print(d, ' ', v.x, ' ', v.y, ' ', dangle[0])
            tanks[1].turret.angle = shoot_dir - tanks[1].hull.body.angle
            tanks[1].turret.fire()

            bot_time = time.time()

class myContactListener(b2ContactListener):
    def __init__(self):
        b2ContactListener.__init__(self)
    def BeginContact(self, contact):
        A = contact.fixtureA.body.userData
        B = contact.fixtureB.body.userData
        if (type(A) is Bullet) and (type(B) is Bullet):
            contact.enabled = False
            return
    def EndContact(self, contact):
        pass
    def PreSolve(self, contact, oldManifold):
        pass
    def PostSolve(self, contact, impulse):
        global training
        A = contact.fixtureA.body.userData
        B = contact.fixtureB.body.userData

        #print(0)

        if (type(A) is Bullet) and not(type(B) is Bullet):
            A.is_collision = True
            if type(B) is Hull and B.player != A.player :
                B.get_damage(A.damage)
            else :
                if A.train != -1 :
                    training.pop(str(A.train), None)
            #print(1)
        if (type(B) is Bullet) and not(type(A) is Bullet):
            B.is_collision = True
            if type(A) is Hull and B.player != A.player :
                A.get_damage(B.damage)
            else :
                if B.train != -1 :
                    training.pop(str(B.train), None)
            #print(2)


bodies = []
bullets = []
data = dict()
TARGET_FPS = 30
TIME_STEP = 1.0 / TARGET_FPS
screenXY = SCREEN_WIDTH, SCREEN_HEIGHT = 800, 800
power_left = 0
power_right = 0

tank1_kills = 0
tank2_kills = 0

tank1_iskill = False
tank2_iskill = False

player1_stats = None
player2_stats = None

bot_mode = 'attack'
svr_rbf = None

bot_time = time.time()

tanks = []

training = {}

CND = ClientData()

def CreateBumpers(world, env):
    width = 20

    walls = []
    top = world.CreateStaticBody(
        position=env.ConvertScreenToWorld(SCREEN_WIDTH / 2, width / 2),
        shapes=b2PolygonShape(box=(SCREEN_WIDTH / env.viewZoom / 2, width / env.viewZoom / 2))
    )
    walls.append(top)
    left = world.CreateStaticBody(
        position=env.ConvertScreenToWorld(width / 2, SCREEN_HEIGHT / 2),
        shapes=b2PolygonShape(box=(width / env.viewZoom / 2, SCREEN_HEIGHT / env.viewZoom / 2))
    )
    walls.append(left)
    bottom = world.CreateStaticBody(
        position=env.ConvertScreenToWorld(SCREEN_WIDTH / 2, SCREEN_HEIGHT - width / 2),
        shapes=b2PolygonShape(box=(SCREEN_WIDTH / env.viewZoom / 2, width / env.viewZoom / 2))
    )
    walls.append(bottom)
    right = world.CreateStaticBody(
        position=env.ConvertScreenToWorld(SCREEN_WIDTH - width / 2, SCREEN_HEIGHT / 2),
        shapes=b2PolygonShape(box=(width / env.viewZoom / 2, SCREEN_HEIGHT / env.viewZoom / 2))
    )
    walls.append(right)
    return walls

def main() :
    global x1, y1, x2, y2, bullets, data, CND, tank1_kills, tank2_kills, tank1_iskill, tank2_iskill, tanks, bot_mode, training, svr_rbf, bot_time

    training = database.load_train(training)

    if bot_mode == 'attack' :
        #svr_rbf = SVR(gamma ='auto')
        svr_rbf = sk.linear_model.LinearRegression()
        n = len(training)
        array = np.ndarray(shape=(n, 4))
        i = 0
        for key in training:
            dist = training[key][0]
            x = training[key][1]
            y = training[key][2]
            angle = training[key][3]
            array[i] = [dist, x, y, angle]
            i += 1
        #print(array)
        X = array[:, 0:3]
        #print(X)
        Y = array[:, 3]
        #print(Y)
        svr_rbf.fit(X, Y)

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('Tanks')

    world = b2World(gravity=(0, 0), doSleep=True, contactListener = myContactListener())

    e = Environment(screenXY, world, screen)

    walls = CreateBumpers(world, e)
    bodies.extend(walls)


    tanks.append(Tank('hull.png', 'turret.png', 100, 100, 0, world, e, 1))
    tanks.append(Tank('hull.png', 'turret.png', 400, 400, 0, world, e, 2))

    colors = {
        b2_staticBody: (255, 255, 255, 255),
        b2_dynamicBody: (127, 127, 127, 255),
    }

    clock = pygame.time.Clock()

    local_ip = socket.gethostbyname(socket.gethostname())
    local_port = 4330
    print("Server IP address and port: ", local_ip, local_port)
    drawBoard_server = GameServer(localaddr=(local_ip, local_port))

    # Initialize the client states and mouse histories.

    running = True
    #bullets.append(Bullet(world, b2Vec2(20, 20), 0, e, player = 2))
    #bullets[-1].body.linearVelocity = b2Vec2(0, 0)
    #print(my_tank.body.position)
    index = 0

    bot_time = time.time()
    print(bot_time)
    print(time.time())
    #print('pizdec')

    while running :
        running = e.checkEvents()

        drawBoard_server.Pump()
        data = dict()
        data['tanks'] = list()
        data['turrets'] = list()
        data['bullets'] = list()
        #data['damages'] = list()

        #update_contorls_my_tank(tanks[0], e)
        if(CND.CN_data['C1'] != None) :
            update_controls_client(tanks[0], CND.CN_data['C1']['state'])
        if (CND.CN_data['C2'] != None) :
            update_controls_client(tanks[1], CND.CN_data['C2']['state'])
        if channels['1'] != None :
            update_bot()

        for tank in tanks :
            tank.updatePhysics()

        world.Step(TIME_STEP, 10, 10)

        screen.fill((0, 0, 0))


        true_bullets = []
        for bullet in bullets :
            if bullet.is_collision :
                #object_methods = [method_name for method_name in dir(world)
                #                  if callable(getattr(world, method_name))]
                world.DestroyBody(bullet.body)
            else:
                true_bullets.append(bullet)
        bullets = true_bullets

        for body in bodies:  # or: world.bodies
            for fixture in body.fixtures:
                shape = fixture.shape

                vertices_screen = []
                for vertex_object in shape.vertices:
                    vertex_world = body.transform * vertex_object  # Overload operation
                    vertex_screen = e.ConvertWorldtoScreen(vertex_world)  # This returns a tuple
                    vertices_screen.append(vertex_screen)  # Append to the list.

                pygame.draw.polygon(screen, colors[body.type], vertices_screen)

        for bullet in bullets :
            bullet.draw()
            position = e.ConvertWorldtoScreen(bullet.body.position)
            radius = bullet.radius * e.viewZoom
            data['bullets'].append((position[0], position[1], radius))

        data['healths'] = (tanks[0].hull.health, tanks[1].hull.health)
        data['iskills'] = (tank1_iskill, tank2_iskill)
        if tank1_iskill :
            tank2_kills += 1
            tank1_iskill = False
            tanks[0].hull.respawn()
        if tank2_iskill:
            tank1_kills += 1
            tank2_iskill = False
            tanks[1].hull.respawn()

        #print(tank1_kills, ' ' ,tank2_kills)
        data['kills'] = (tank1_kills, tank2_kills)


        for tank in tanks :
            tank.draw()
        drawBoard_server.SendInformation(data)
        #for force in forces :
        #    pygame.draw.line(screen, (255, 255, 255), e.ConvertWorldtoScreen(forces[force][0]), e.ConvertWorldtoScreen(forces[force][1]))

        e.drawMouseJoint()

        pygame.display.update()

        clock.tick(TARGET_FPS)
    if bot_mode == 'collect' :
        database.save_train(training)

main()