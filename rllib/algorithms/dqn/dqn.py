import logging
from typing import Any, Dict, List, Mapping, SupportsFloat

import numpy as np
import torch
import torch.nn as nn

from multiworld.utils.advanced_typing import Action
from multiworld.utils.typing import AgentID, ObsType
from rllib.algorithms.algorithm import Algorithm
from rllib.algorithms.dqn.dqn_config import DQNConfig
from rllib.core.memory.replay_memory import ReplayMemory, Transition
from rllib.core.network.multi_input_network import MultiInputNetwork
from rllib.utils.dqn.misc import get_non_final_mask
from rllib.utils.dqn.preprocessing import preprocess_next_observations
from rllib.utils.torch.processing import (
    observation_to_torch_unsqueeze,
    observations_seperate_to_torch,
)
from utils.core.model_loader import ModelLoader


class DQN(Algorithm):
    _policy_net: MultiInputNetwork
    _target_net: MultiInputNetwork

    def __init__(self, config: DQNConfig):
        super().__init__(config)
        self._config = config
        self._memory = ReplayMemory(config.replay_buffer_size)
        self._policy_net = MultiInputNetwork(
            self.observation_space,
            self.action_space,
            conv_layers=self._config.conv_layers,
            hidden_units=self._config.hidden_units,
        )
        self._target_net = MultiInputNetwork(
            self.observation_space,
            self.action_space,
            conv_layers=self._config.conv_layers,
            hidden_units=self._config.hidden_units,
        )

        if self._config._model_path is not None:
            ModelLoader.load_model_from_path(self._config._model_path, self._policy_net)
        self._target_net.load_state_dict(self._policy_net.state_dict())
        self._optimizer = torch.optim.AdamW(
            self._policy_net.parameters(), lr=config.learning_rate, amsgrad=True
        )
        self._eps_threshold = np.inf

    def train_step(
        self,
        observations: Dict[AgentID, ObsType],
        next_observations: Dict[AgentID, ObsType],
        actions: Dict[AgentID, int],
        rewards: Dict[AgentID, SupportsFloat],
        terminations: Dict[AgentID, bool],
        truncations: Dict[AgentID, bool],
        step: int,
        infos: Dict[AgentID, Dict[str, Any]],
    ):
        next_obs = preprocess_next_observations(
            next_observations, terminations, truncations
        )

        self._memory.add_dict(
            keys=observations.keys(),
            state=observations,
            action=actions,
            next_state=next_obs,
            reward=rewards,
        )
        self._optimize_model()
        self._hard_update_target()

    def log_episode(self):
        super().log_episode()
        metadata = {
            "agents": len(self._env.agents),
            "width": self._env._width,
            "height": self._env._height,
            "eps_threshold": self._eps_threshold,
            "conv_layers": self._config.conv_layers,
            "hidden_units": self._config.hidden_units,
        }
        self.log_model(
            self._policy_net,
            f"model_{self._episodes_done}",
            self._episodes_done,
            metadata,
        )
        self.add_log("eps_threshold", self._eps_threshold)

    def predict(self, observation: dict[AgentID, ObsType]) -> dict[AgentID, int]:
        self._eps_threshold = self._config.eps_end + (
            self._config.eps_start - self._config.eps_end
        ) * np.exp(-1.0 * self._steps_done / self._config.eps_decay)

        actions = self._get_policy_actions(observation)
        for key, _ in actions.items():
            if np.random.rand() < self._eps_threshold:
                actions[key] = self._get_random_action()
        return actions

    def load_model(self, model: Mapping[str, Any]):
        self._policy_net.load_state_dict(model)
        self._target_net.load_state_dict(self._policy_net.state_dict())
        self._policy_net.eval()
        self._target_net.eval()

    @property
    def model(self) -> nn.Module:
        return self._policy_net

    def _get_policy_actions(
        self, observations: Dict[AgentID, ObsType]
    ) -> Dict[AgentID, int]:
        torch_observations = observations_seperate_to_torch(list(observations.values()))
        with torch.no_grad():
            pred_actions = self._policy_net(*torch_observations)

        actions = {}
        for key, action in zip(observations.keys(), pred_actions):
            actions[key] = action.argmax().item()
        return actions

    def _get_policy_action(self, observation: ObsType) -> Action:
        with torch.no_grad():
            torch_obs = observation_to_torch_unsqueeze(observation)
            return self._policy_net(*torch_obs).argmax().item()

    def _get_random_action(self):
        return np.random.randint(self.action_space.n)

    def _optimize_model(self) -> float | None:
        if len(self._memory) < self._config.batch_size:
            return None

        transitions = self._memory.sample(self._config.batch_size)

        batch = Transition(*zip(*transitions))

        non_final_mask = get_non_final_mask(batch.next_state)
        non_final_next_states = observations_seperate_to_torch(
            batch.next_state, skip_none=True
        )
        if len(non_final_next_states) == 0:
            logging.warning("No non final next states, consider increasing batch size.")
            return None

        state_batch = observations_seperate_to_torch(batch.state)
        action_batch = torch.tensor(batch.action).unsqueeze(1)
        reward_batch = torch.tensor(batch.reward)

        state_action_values = self._predict_policy_values(state_batch, action_batch)

        next_state_values = torch.zeros(self._config.batch_size)
        self._predict_target_values(
            non_final_next_states, next_state_values, non_final_mask
        )
        expected_state_action_values = self._expected_state_action_values(
            next_state_values, reward_batch
        )

        loss = self._compute_loss(state_action_values, expected_state_action_values)

        self.add_log("loss", loss.item())

        self._optimizer.zero_grad()
        loss.backward()
        self._optimizer.step()

        return loss.item()

    def _predict_policy_values(
        self, state: List[torch.Tensor], action_batch: torch.Tensor
    ) -> torch.Tensor:
        return self._policy_net(*state).gather(1, action_batch)

    def _predict_target_values(
        self,
        non_final_next_states: List[torch.Tensor],
        next_state_values: torch.Tensor,
        non_final_mask: List[bool],
    ) -> torch.Tensor:
        with torch.no_grad():
            output = self._target_net(*non_final_next_states).max(1).values
            next_state_values[non_final_mask] = output
        return next_state_values

    def _expected_state_action_values(
        self, next_state_values: torch.Tensor, reward_batch: torch.Tensor
    ) -> torch.Tensor:
        return next_state_values * self._config.gamma + reward_batch

    def _compute_loss(
        self,
        state_action_values: torch.Tensor,
        expected_state_action_values: torch.Tensor,
    ) -> torch.nn.SmoothL1Loss:
        return self._compute_action_loss(
            state_action_values, expected_state_action_values
        )

    def _compute_action_loss(
        self,
        state_action_values: torch.Tensor,
        expected_state_action_values: torch.Tensor,
    ) -> torch.nn.SmoothL1Loss:
        criterion = torch.nn.SmoothL1Loss()
        return criterion(
            state_action_values, expected_state_action_values.unsqueeze(1)
        ).mean()

    def _hard_update_target(self):
        if self._steps_done % self._config.target_update != 0:
            return
        self._target_net.load_state_dict(self._policy_net.state_dict())

    def _soft_update_target(self):
        target_net_state_dict = self._target_net.state_dict()
        policy_net_state_dict = self._policy_net.state_dict()
        for key in policy_net_state_dict:
            target_net_state_dict[key] = policy_net_state_dict[
                key
            ] * 0.005 + target_net_state_dict[key] * (1 - 0.005)
        self._target_net.load_state_dict(target_net_state_dict)
