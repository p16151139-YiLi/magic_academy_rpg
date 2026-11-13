"""Offline, deterministic-seed NPC game AI: dynamic utility decisions + A*.

NPCs do NOT require generative model/network/API keys. Each agent observes
obstacles, the player and other agents, then chooses appropriate changing goals.
The foot collision solver uses the same map rectangles as the player.
"""
import heapq
import math
import random
import pygame
from systems.character_motion import facing_from_actual_displacement,footprint_clear

CELL = 28
FOOT_W, FOOT_H = 22, 15


def available(x, y, obstacles, bounds):
    return footprint_clear(pygame, x, y, (FOOT_W, FOOT_H), obstacles, bounds)


def grid_cell(position):
    return (int(position[0] // CELL), int(position[1] // CELL))


def grid_center(node):
    return pygame.Vector2((node[0] + .5) * CELL, (node[1] + .5) * CELL)


def astar(start, goal, obstacles, bounds, limit=1900):
    """4-connected A*: diagonals must not clip furniture corners."""
    origin, destination = grid_cell(start), grid_cell(goal)
    if origin == destination:
        return [pygame.Vector2(goal)]

    def clear(node):
        p = grid_center(node)
        return available(p.x, p.y, obstacles, bounds)

    if not clear(destination):
        return []

    queue = [(0, 0, origin)]
    distance = {origin: 0}
    parents = {}
    generation = 0
    checked = 0
    while queue and checked < limit:
        _, travelled, current = heapq.heappop(queue)
        if travelled != distance.get(current):
            continue
        checked += 1
        if current == destination:
            route = []
            while current != origin:
                route.append(grid_center(current))
                current = parents[current]
            route.reverse()
            # Goal is never farther than one grid cell from its final waypoint.
            route.append(pygame.Vector2(goal))
            return route
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            neighbor = (current[0] + dx, current[1] + dy)
            new_cost = travelled + 1
            if new_cost >= distance.get(neighbor, 10**8) or not clear(neighbor):
                continue
            distance[neighbor] = new_cost
            parents[neighbor] = current
            priority = new_cost + abs(neighbor[0] - destination[0]) + abs(neighbor[1] - destination[1])
            generation += 1
            heapq.heappush(queue, (priority, new_cost, neighbor))
    return []


class Agent:
    def __init__(self, entity, map_name, initial_pos):
        self.id = entity['id']
        self.map_name = map_name
        self.pos = pygame.Vector2(initial_pos)
        self.home = pygame.Vector2(initial_pos)
        self.role = entity.get('role', 'wander')
        self.speed = max(20.0, min(90.0, float(entity.get('speed', 45))))
        self.area = entity.get('area', [self.home.x - 125, self.home.y - 100,
                                        self.home.x + 125, self.home.y + 100])
        self.rng = random.Random(sum((i + 1) * ord(c) for i, c in enumerate(map_name + self.id)) * 103)
        self.route = []
        self.intent = 'idle'
        self.direction = 'down'
        self.moving = False
        self.state = 'standing'
        self.idle_left = self.rng.uniform(.25, 1.2) if self.role in ('patrol','guard') else self.rng.uniform(2.2, 5.0)
        self.energy = self.rng.uniform(.55, .95)
        self.curiosity = self.rng.uniform(.3, .85)
        self.social_need = self.rng.uniform(.05, .45)
        self.last_goal = None
        self.distance = 0.0
        self.observation_cooldown = 0.0

    def _face(self, diff):
        if diff.length_squared() < 1:
            return
        if abs(diff.x) > abs(diff.y):
            self.direction = 'right' if diff.x > 0 else 'left'
        else:
            self.direction = 'down' if diff.y > 0 else 'up'

    def pause_for_dialogue(self, player_pos):
        """Interrupt the planned route without showing the previous walk pose.
        The next update will choose a fresh destination after interaction.
        """
        self.route.clear()
        self.moving=False
        self.intent='observe'
        self.idle_left=0.4
        self._face(player_pos-self.pos)

    def _choose(self, obstacles, bounds, player_pos, others):
        # Utility scores are driven by internal energy, time, role, and context;
        # weighted sampling prevents scripted/predictable sequences.
        neighbor = next((a for a in others if a is not self and
                         self.pos.distance_squared_to(a.pos) < 105**2), None)
        player_near = player_pos is not None and self.pos.distance_squared_to(player_pos) < 150**2
        guard = self.role in ('patrol', 'guard')
        options = [
            ('explore', (3.3 if guard else .36) + self.curiosity * .6 + self.energy * .35),
            ('rest', .08 + (1 - self.energy) * 1.9),
            ('observe', (.28 if player_near else .08) + (.16 if guard else .02)),
            ('social', (self.social_need * .7 + .25) if neighbor is not None and not guard else .025),
            # Mental review is a stationary behavior; avoid pretending to
            # write, read or sit if the sprite has no such animation.
            ('review', .0 if guard or self.role == 'visitor' else .25),
        ]
        self.intent = self.rng.choices([n for n, _ in options],
                                        weights=[w for _, w in options], k=1)[0]
        if self.intent != 'explore':
            self.route.clear()
            self.idle_left = (self.rng.uniform(.35, 1.5) if guard else self.rng.uniform(2.2, 4.5)) if self.intent != 'rest' else self.rng.uniform(2.0, 4.0)
            if self.intent == 'social' and neighbor is not None:
                self.social_need = .03
                self._face(neighbor.pos - self.pos)
            elif self.intent == 'observe' and player_near:
                self._face(player_pos - self.pos)
            return
        x0, y0, x1, y1 = self.area
        for _ in range(21):
            goal = pygame.Vector2(self.rng.uniform(x0, x1), self.rng.uniform(y0, y1))
            if self.last_goal is not None and goal.distance_squared_to(self.last_goal) < 36**2:
                continue
            if goal.distance_squared_to(self.pos) < 44**2:
                continue
            if not available(goal.x, goal.y, obstacles, bounds):
                continue
            route = astar(self.pos, goal, obstacles, bounds)
            if route:
                self.route = route
                self.last_goal = goal
                return
        self.intent = 'rest'
        self.route.clear()
        self.idle_left = self.rng.uniform(2.0, 3.5)

    def update(self, dt, obstacles, bounds, player_pos=None, others=()):
        dt = max(0.0, min(float(dt), .08))
        self.moving = False
        self.state = 'standing'
        self.observation_cooldown = max(0.0, self.observation_cooldown - dt)
        if player_pos is not None and self.pos.distance_squared_to(player_pos) < 38**2:
            self._face(player_pos - self.pos)
            self.route.clear()
            self.intent = 'observe'
            self.idle_left = max(self.idle_left, .4)
            return
        self.social_need = min(1.0, self.social_need + dt * .005)
        self.idle_left -= dt
        if not self.route:
            self.energy = min(1.0, self.energy + dt * .02)
            if self.idle_left <= 0:
                self._choose(obstacles, bounds, player_pos, others)
            return
        # Follow a path rather than move in a straight line through scenery.
        waypoint = self.route[0]
        diff = waypoint - self.pos
        if diff.length_squared() <= 6**2:
            self.route.pop(0)
            if not self.route:
                self.intent='rest'
                self.idle_left = self.rng.uniform(1.8, 3.5)
            return
        step_distance = min(diff.length(), self.speed * dt)
        step = diff.normalize() * step_distance
        candidate = self.pos + step
        x0, y0, x1, y1 = self.area
        if not (x0 <= candidate.x <= x1 and y0 <= candidate.y <= y1):
            self.route.clear()
            self.intent='observe'
            self.idle_left = .35
            return
        if not available(candidate.x, candidate.y, obstacles, bounds):
            self.route.clear()
            self.intent='observe'
            self.idle_left = self.rng.uniform(.15, .5)
            return
        if any(a is not self and candidate.distance_squared_to(a.pos) < 25**2 for a in others):
            self.route.clear()
            self.intent='observe'
            self.idle_left = self.rng.uniform(.5, 1.2)
            return
        if player_pos is not None and candidate.distance_squared_to(player_pos) < 32**2:
            self.route.clear()
            self.intent='observe'
            self.idle_left = .4
            return
        old_pos = pygame.Vector2(self.pos)
        self.pos.update(candidate)
        real_delta = self.pos - old_pos
        direction, moved = facing_from_actual_displacement(real_delta.x,real_delta.y,self.direction)
        if moved:
            self.direction = direction
            self.moving = True
            self.state = 'moving'
        self.distance += real_delta.length()
        self.energy = max(.04, self.energy - dt * .013)
