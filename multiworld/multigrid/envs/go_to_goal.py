from typing import Any, Dict, SupportsFloat, Tuple

import numpy as np

from multiworld.core.position import Position
from multiworld.multigrid.base import MultiGridEnv
from multiworld.multigrid.core.action import Action
from multiworld.multigrid.core.grid import Grid
from multiworld.multigrid.core.world_object import Goal
from multiworld.utils.typing import AgentID, ObsType


class GoToGoalEnv(MultiGridEnv):
    def __init__(self, goals: int = 1, *args, **kwargs):
        self._goals = goals
        super().__init__(*args, **kwargs)

    def _gen_world(self, width: int, height: int):
        self._world = Grid(width, height)

        n = self._rand_int(1, self._goals) if self._goals > 1 else self._goals
        for _ in range(n):
            placeable_positions = self._world.get_empty_positions()
            goal_pos = self._rand_elem(placeable_positions)
            goal_pos = Position(self._width // 2, self._height // 2)
            self.goal = Goal()
            self._world.set(goal_pos, self.goal)

        placeable_positions = np.array(self._world.get_empty_positions())
        np.random.shuffle(placeable_positions)
        for i, agent in enumerate(self.agents):
            pos = placeable_positions[i]
            agent.state.pos = pos

    def step(
        self, actions: Dict[AgentID, Action | int]
    ) -> Tuple[
        Dict[AgentID, ObsType],
        Dict[AgentID, SupportsFloat],
        Dict[AgentID, bool],
        Dict[AgentID, bool],
        Dict[AgentID, Dict[str, Any]],
    ]:
        print(actions)
        observations, rewards, terminations, truncations, info = super().step(actions)
        for agent in self.agents:
            obj = self._world.get(agent.state.pos)
            if obj is None:
                continue
            if np.array_equal(obj, self.goal):
                self.add_reward(agent, rewards, 10)
                agent.pos = Position(-1, -1)
        return observations, rewards, terminations, truncations, info
