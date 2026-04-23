# =============================================================================
# PATRON: STRATEGY (Comportamiento)
# =============================================================================
# QUÉ ES:
#   Define una familia de algoritmos intercambiables, encapsulados en
#   clases separadas. El cliente puede cambiar el algoritmo en runtime
#   sin modificar su propio código.
#
# POR QUÉ SE USA AQUÍ:
#   El servicio de agentes necesita asignar un agente a un ticket.
#   Hay múltiples estrategias de asignación válidas:
#     - LeastLoaded: asigna al agente con menos tickets activos
#     - RoundRobin: asigna de forma equitativa rotatoria
#     - SkillBased: asigna al agente que tenga el skill requerido
#
#   La estrategia se selecciona via variable de entorno, permitiendo
#   cambiar el algoritmo sin redesplegar código.
#
# CUÁNDO USARLO EN PRODUCCIÓN:
#   - Algoritmos de pricing (fijo, descuento, por volumen)
#   - Estrategias de cache (LRU, LFU, TTL)
#   - Algoritmos de routing/load balancing
#   - Validación con diferentes reglas según contexto
#   - Cálculo de impuestos por país/región
#   - Algoritmos de búsqueda/ranking
#
# CUÁNDO NO USARLO:
#   - Si solo hay un algoritmo y no se prevén cambios
#   - Si la selección es trivial (un if/else simple basta)
#   - Si los algoritmos comparten mucho estado (considerar Template Method)
# =============================================================================

import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Strategy Interface (Abstract Strategy)
# ---------------------------------------------------------------------------
class AssignmentStrategy(ABC):
    """
    Interfaz que todas las estrategias de asignación deben implementar.
    Define un contrato único: dado un ticket y una lista de agentes
    disponibles, retorna el agente seleccionado.
    """

    @abstractmethod
    def select_agent(self, agents: list[dict], ticket: dict) -> dict | None:
        """
        Selecciona un agente para asignar al ticket.

        Args:
            agents: Lista de agentes disponibles (status=ONLINE, active < max)
            ticket: Datos del ticket a asignar (incluye category, priority)

        Returns:
            El agente seleccionado, o None si no hay agentes disponibles.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre descriptivo de la estrategia."""
        pass


# ---------------------------------------------------------------------------
# Concrete Strategies
# ---------------------------------------------------------------------------
class LeastLoadedStrategy(AssignmentStrategy):
    """
    Asigna al agente con MENOS tickets activos.

    Lógica: ordena agentes por active_tickets_count ascendente.
    El primero en la lista es el que tiene menos carga.

    Ventajas: distribución equitativa de carga.
    Desventajas: no considera skills ni prioridad del ticket.
    """

    @property
    def name(self) -> str:
        return "LEAST_LOADED"

    def select_agent(self, agents: list[dict], ticket: dict) -> dict | None:
        if not agents:
            return None

        # Ordenar por carga ascendente
        sorted_agents = sorted(agents, key=lambda a: a.get("active_tickets_count", 0))
        selected = sorted_agents[0]

        logger.info(
            f"[{self.name}] Selected agent {selected.get('id')} "
            f"(load: {selected.get('active_tickets_count', 0)})"
        )
        return selected


class RoundRobinStrategy(AssignmentStrategy):
    """
    Asigna de forma ROTATORIA entre los agentes disponibles.

    Usa un counter estático que incrementa con cada asignación.
    El agente se selecciona con módulo sobre el total de agentes.

    Ventajas: distribución perfectamente equitativa.
    Desventajas: no considera carga actual ni skills.
    """

    _counter = 0

    @property
    def name(self) -> str:
        return "ROUND_ROBIN"

    def select_agent(self, agents: list[dict], ticket: dict) -> dict | None:
        if not agents:
            return None

        index = RoundRobinStrategy._counter % len(agents)
        RoundRobinStrategy._counter += 1

        selected = agents[index]
        logger.info(
            f"[{self.name}] Selected agent {selected.get('id')} "
            f"(index: {index}/{len(agents)})"
        )
        return selected


class SkillBasedStrategy(AssignmentStrategy):
    """
    Asigna al agente que tenga el SKILL que matchea con la categoría
    del ticket. Si hay varios con el skill, elige el de menor carga.

    Lógica:
      1. Filtra agentes que tengan el skill = ticket.category
      2. Si hay match, ordena por carga y toma el de menor carga
      3. Si no hay match, fallback a LeastLoaded sobre todos

    Ventajas: asigna al experto en el tema.
    Desventajas: puede sobrecargar a agentes con skills raros.
    """

    @property
    def name(self) -> str:
        return "SKILL_BASED"

    def select_agent(self, agents: list[dict], ticket: dict) -> dict | None:
        if not agents:
            return None

        category = ticket.get("category", "").lower()

        # Filtrar agentes con el skill que matchea
        skilled = [
            a for a in agents
            if category in [s.lower() for s in a.get("skills", [])]
        ]

        if skilled:
            # Entre los que tienen el skill, tomar el de menor carga
            selected = min(skilled, key=lambda a: a.get("active_tickets_count", 0))
            logger.info(
                f"[{self.name}] Selected agent {selected.get('id')} "
                f"(skill match: {category})"
            )
        else:
            # Fallback: menor carga entre todos
            selected = min(agents, key=lambda a: a.get("active_tickets_count", 0))
            logger.info(
                f"[{self.name}] No skill match for '{category}', "
                f"fallback to least loaded: {selected.get('id')}"
            )

        return selected


# ---------------------------------------------------------------------------
# Context (Strategy Selector)
# ---------------------------------------------------------------------------
class AgentAssignmentContext:
    """
    Context que usa una Strategy para asignar agentes.

    La estrategia se selecciona via variable de entorno ASSIGNMENT_STRATEGY.
    Valores: LEAST_LOADED (default), ROUND_ROBIN, SKILL_BASED.

    Uso:
        ctx = AgentAssignmentContext()  # Lee ASSIGNMENT_STRATEGY del env
        agent = ctx.assign(agents_list, ticket_data)

        # O cambiar en runtime:
        ctx.set_strategy(SkillBasedStrategy())
        agent = ctx.assign(agents_list, ticket_data)
    """

    _strategies = {
        "LEAST_LOADED": LeastLoadedStrategy,
        "ROUND_ROBIN": RoundRobinStrategy,
        "SKILL_BASED": SkillBasedStrategy,
    }

    def __init__(self, strategy: AssignmentStrategy = None):
        if strategy:
            self._strategy = strategy
        else:
            strategy_name = os.environ.get("ASSIGNMENT_STRATEGY", "LEAST_LOADED")
            strategy_class = self._strategies.get(strategy_name.upper(), LeastLoadedStrategy)
            self._strategy = strategy_class()
            logger.info(f"AgentAssignmentContext using strategy: {self._strategy.name}")

    def set_strategy(self, strategy: AssignmentStrategy) -> None:
        """Cambia la estrategia en runtime."""
        self._strategy = strategy
        logger.info(f"Strategy changed to: {strategy.name}")

    def assign(self, agents: list[dict], ticket: dict) -> dict | None:
        """Delega la selección al strategy actual."""
        return self._strategy.select_agent(agents, ticket)

    @property
    def current_strategy(self) -> str:
        return self._strategy.name
