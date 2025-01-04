import numpy as np
import torch

from rllib.core.torch.module import TorchModule
from rllib.utils.network.network import get_output_size
from rllib.utils.spaces import ObservationSpace, ActionSpace
from rllib.core.network.processor import ConvProcessor, FCProcessor
from rllib.utils.network.network import observation_space_check, action_space_check


class MultiInputNetwork(TorchModule):
    def __init__(
        self,
        state_dim: ObservationSpace,
        action_dim: ActionSpace,
        conv_layers: tuple[int, ...] = (32, 64, 64),
        hidden_units: tuple[int, ...] = (128, 128),
    ):
        super(MultiInputNetwork, self).__init__()
        observation_space_check(state_dim)
        action_space_check(action_dim)
        self._conv0 = ConvProcessor(state_dim.box, conv_layers)
        rolled_state_dim = np.roll(state_dim.box, shift=1)  # Channels first
        conv_output_size = get_output_size(self._conv0, rolled_state_dim)
        self._fc0 = FCProcessor(
            int(state_dim.discrete), hidden_units, int(action_dim.discrete)
        )
        fc_output_size = get_output_size(self._fc0, np.array([state_dim.discrete]))
        final_input_size = conv_output_size + fc_output_size
        self._create_fc_final(final_input_size, hidden_units, int(action_dim.discrete))

    def _create_fc_final(
        self, final_input_size: int, hidden_units: tuple[int, ...], action_dim: int
    ):
        self._fc_final = FCProcessor(final_input_size, hidden_units, action_dim)

    def forward(self, x_img: torch.Tensor, x_dir: torch.Tensor) -> torch.Tensor:
        x_img = x_img.float()
        x_img = x_img.permute(0, 3, 1, 2)
        x_img = self._conv0(x_img)
        x_img = x_img.view(x_img.size(0), -1)

        x_dir = self._fc0(x_dir)

        x = torch.cat([x_img, x_dir], dim=1)
        x = self._fc_final(x)
        return x
