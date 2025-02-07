from multiworld.multigrid.envs.go_to_goal import GoToGoalEnv
from rllib.algorithms.dqn.dqn import DQN
from rllib.algorithms.dqn.dqn_config import DQNConfig
from rllib.core.network.network import NetworkType
from utils.common.observation import (
    load_and_split_observation,
    zip_observation_data,
)
from utils.core.model_loader import ModelLoader
from utils.core.plotting import plot_3d
from xailib.common.activations import (
    compute_activations_from_artifacts,
)
from xailib.common.binary_concept_score import binary_concept_scores
from xailib.common.probes import get_probes
from xailib.core.linear_probing.probe_to_observation import ProbeObservation


def run(concept: str):
    ignore = []

    model_artifacts = ModelLoader.load_latest_model_from_path("artifacts", dqn.model)
    positive_observation, test_observation = load_and_split_observation(concept, 0.8)
    negative_observation, _ = load_and_split_observation("random_negative", 0.8)

    test_observation_zipped = zip_observation_data(test_observation)

    test_activations, test_input, test_output = compute_activations_from_artifacts(
        model_artifacts, test_observation_zipped, ignore
    )

    probes = get_probes(
        model_artifacts, positive_observation, negative_observation, ignore
    )

    layer_idx = 0
    probe = list(probes["latest"].values())[layer_idx]
    probe_observation = ProbeObservation(probe)
    activation_shape = list(list(test_activations.values())[0].values())[layer_idx][
        "output"
    ].shape[1:]
    probe_observation._get_positive_activations(activation_shape)


if __name__ == "__main__":
    env = GoToGoalEnv(render_mode="rgb_array")
    config = (
        DQNConfig(
            batch_size=64,
            replay_buffer_size=10000,
            gamma=0.99,
            learning_rate=3e-4,
            eps_start=0.9,
            eps_end=0.05,
            eps_decay=50000,
            target_update=1000,
        )
        .network(network_type=NetworkType.MULTI_INPUT)
        .debugging(log_level="INFO")
        .environment(env=env)
    )

    dqn = DQN(config)

    # concepts = concept_checks.keys()
    concepts = [
        "agent_in_front",
        "agent_in_view",
        "agent_to_left",
        "agent_to_right",
        "goal_in_front",
        "goal_in_view",
        "goal_to_left",
        "goal_to_right",
        "random",
    ]
    concepts = ["random"]

    for concept in concepts:
        run(concept)
