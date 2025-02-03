# from multiworld.swarm.utils.wrappers import SwarmConceptObsWrapper
from rllib.algorithms.dqn.dqn import DQN
from rllib.algorithms.dqn.dqn_config import DQNConfig
from multiworld.swarm.envs.flock import FlockEnv

env = FlockEnv(
    width=100,
    height=100,
    max_steps=200,
    agents=1,
    observations=10,
    predators=1,
    predator_steps=100,
    object_size=8,
    agent_view_size=65,
    success_termination_mode="all",
    render_mode="rgb_array",
)

# env = ObservationCollectorWrapper(env, observations=10)
# env = SwarmConceptObsWrapper(env, observations=10, method="random")

config = (
    DQNConfig(
        batch_size=64,
        replay_buffer_size=10000,
        gamma=0.99,
        learning_rate=1e-4,
        eps_start=0.9,
        eps_end=0.05,
        eps_decay=100000,
        target_update=5000,
    )
    .network(conv_layers=())
    .environment(env=env)
    .training()
    .debugging(log_level="INFO")
    .rendering()
    .wandb(project="bird")
)

dqn = DQN(config)

while True:
    dqn.learn()
