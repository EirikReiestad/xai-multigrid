import random
from typing import Any, List, SupportsFloat

import numpy as np
from numpy.typing import NDArray

from multigrid.base import MultiGridEnv
from multigrid.core.action import Action
from multigrid.core.area import Area
from multigrid.core.grid import Grid
from multigrid.core.world_object import Box, Container, Goal, Wall, WorldObject
from multigrid.utils.position import Position
from multigrid.utils.typing import AgentID, ObsType


class CleanUpEnv(MultiGridEnv):
    def __init__(self, boxes: int, *args, **kwargs):
        self._num_boxes = boxes
        super().__init__(*args, **kwargs)

    def _gen_grid(self, width: int, height: int):
        self.grid = Grid(width, height)

        container_obj = lambda: Container()
        area_sizes = [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]
        num_areas = 1
        for _ in range(num_areas):
            area_size = self._rand_elem(area_sizes)
            placeable_areas = self.grid.get_empty_areas(area_size)
            if len(placeable_areas) == 0:
                continue
            pos: Position = self._rand_elem(placeable_areas)
            container_area = Area(area_size, container_obj)
            container_area.place(self.grid, pos())

        placeable_positions = self.grid.get_empty_positions(self._num_boxes)
        for pos in placeable_positions:
            self.grid.set(pos, Box())

        placeable_positions = self.grid.get_empty_positions(len(self.agents))
        for agent, pos in zip(self.agents, placeable_positions):
            agent.state.pos = pos

    def step(
        self, actions: dict[AgentID, Action | int]
    ) -> tuple[
        dict[AgentID, ObsType],
        dict[AgentID, SupportsFloat],
        dict[AgentID, bool],
        dict[AgentID, bool],
        dict[AgentID, dict[str, Any]],
    ]:
        rewards: dict[AgentID, SupportsFloat] = {
            str(agent.index): 0 for agent in self.agents
        }
        terminations: dict[AgentID, bool] = {
            str(agent.index): False for agent in self.agents
        }
        for agent in self.agents:
            if actions[str(agent.index)] != Action.drop:
                continue

            if agent.state.carrying is None:
                continue

            fwd_pos = agent.front_pos
            fwd_obj = self.grid.get(fwd_pos)
            if fwd_obj is not None and not fwd_obj.can_place:
                continue

            agent_present = np.array(self._agent_states.pos == fwd_pos).any()
            if agent_present:
                continue

            continue

            self.on_success(
                agent,
                rewards,
                terminations,
            )

        observations, step_rewards, terms, truncations, info = super().step(actions)

        rewards = {
            str(agent.index): float(rewards[str(agent.index)])
            + float(step_rewards[str(agent.index)])
            for agent in self.agents
        }
        terminations = {
            str(agent.index): bool(terminations[str(agent.index)])
            or bool(terms[str(agent.index)])
            for agent in self.agents
        }

        return observations, rewards, terminations, truncations, info
