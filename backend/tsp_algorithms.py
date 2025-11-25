# backend/tsp_algorithms.py

from typing import List, Tuple
from shapely.geometry import Point
import itertools
import math
import random
import time

# ---------------------------------------------------
# Distancia entre dos puntos (Haversine, en metros)
# ---------------------------------------------------
def geo_distance(p1: Point, p2: Point) -> float:
    """
    Calcula la distancia aproximada en metros entre dos puntos
    usando la fórmula de Haversine sobre coordenadas lon/lat.
    """
    R = 6371000  # radio de la Tierra en metros

    lat1, lon1 = p1.y, p1.x
    lat2, lon2 = p2.y, p2.x

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# ===================================================
# TSP SOBRE MATRIZ DE DISTANCIAS
# dist_matrix[i][j] = distancia más corta en la red
# ===================================================

# ---------------------------------------------------
# 1. Fuerza bruta
# ---------------------------------------------------
def brute_force_tsp_matrix(dist_matrix: List[List[float]]) -> Tuple[List[int], float, float]:
    """
    Aplica fuerza bruta al TSP usando una matriz de distancias.
    Retorna:
      - ruta (lista de índices de puntos, empezando en 0)
      - distancia total (float)
      - tiempo de ejecución en segundos (float)
    """
    n = len(dist_matrix)
    if n <= 1:
        return list(range(n)), 0.0, 0.0

    indices = list(range(n))
    best_distance = float("inf")
    best_route: List[int] = []

    start_time = time.time()

    # Fijamos el punto 0 como inicio para reducir permutaciones
    for perm in itertools.permutations(indices[1:]):
        route = [0] + list(perm)  # no cerramos ciclo, solo visitamos todos

        dist = 0.0
        for i in range(len(route) - 1):
            a, b = route[i], route[i + 1]
            dist += dist_matrix[a][b]

        if dist < best_distance:
            best_distance = dist
            best_route = route

    elapsed = time.time() - start_time
    return best_route, best_distance, elapsed


# ---------------------------------------------------
# 2. Nearest Neighbor (vecino más cercano)
# ---------------------------------------------------
def nearest_neighbor_tsp_matrix(dist_matrix: List[List[float]]) -> Tuple[List[int], float, float]:
    """
    Algoritmo heurístico del vecino más cercano sobre matriz de distancias.
    Retorna:
      - ruta (lista de índices)
      - distancia total
      - tiempo de ejecución
    """
    n = len(dist_matrix)
    if n <= 1:
        return list(range(n)), 0.0, 0.0

    start_time = time.time()

    unvisited = set(range(1, n))  # dejamos 0 como inicio
    route = [0]
    total_dist = 0.0
    current = 0

    while unvisited:
        # elegir el más cercano al actual
        next_idx = min(unvisited, key=lambda j: dist_matrix[current][j])
        total_dist += dist_matrix[current][next_idx]
        route.append(next_idx)
        unvisited.remove(next_idx)
        current = next_idx

    elapsed = time.time() - start_time
    return route, total_dist, elapsed


# ---------------------------------------------------
# 3. Simulated Annealing (heurístico avanzado)
# ---------------------------------------------------
def simulated_annealing_tsp_matrix(
    dist_matrix: List[List[float]],
    initial_temp: float = 1000.0,
    cooling: float = 0.995,
    steps: int = 5000,
) -> Tuple[List[int], float, float]:
    """
    Heurístico de Simulated Annealing para TSP usando matriz de distancias.
    Retorna:
      - mejor ruta (lista de índices)
      - mejor distancia
      - tiempo de ejecución
    """
    n = len(dist_matrix)
    if n <= 1:
        return list(range(n)), 0.0, 0.0

    def route_distance(route: List[int]) -> float:
        d = 0.0
        for i in range(len(route) - 1):
            a, b = route[i], route[i + 1]
            d += dist_matrix[a][b]
        return d

    # Ruta inicial aleatoria
    route = list(range(n))
    random.shuffle(route)

    current_dist = route_distance(route)
    best_route = route[:]
    best_dist = current_dist

    T = initial_temp
    start_time = time.time()

    for _ in range(steps):
        # intercambio de dos posiciones (movimiento sencillo)
        i, j = random.sample(range(n), 2)
        new_route = route[:]
        new_route[i], new_route[j] = new_route[j], new_route[i]

        new_dist = route_distance(new_route)
        delta = new_dist - current_dist

        # criterio de aceptación
        if delta < 0 or random.random() < math.exp(-delta / T):
            route = new_route
            current_dist = new_dist
            if new_dist < best_dist:
                best_dist = new_dist
                best_route = new_route

        T *= cooling
        if T < 1e-6:
            break

    elapsed = time.time() - start_time
    return best_route, best_dist, elapsed
