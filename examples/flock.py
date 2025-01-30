from rllib.algorithms.dqn.dqn import DQN
from rllib.algorithms.dqn.dqn_config import DQNConfig
from swarm.envs.flock import FlockEnv

env = FlockEnv(
    width=500,
    height=500,
    max_steps=1000,
    agents=100,
    observations=10,
    predators=2,
    predator_steps=100,
    object_size=8,
    agent_view_size=65,
    success_termination_mode="all",
    render_mode="rgb_array",
)

config = (
    DQNConfig(
        batch_size=128,
        replay_buffer_size=100000,
        gamma=0.99,
        learning_rate=1e-4,
        eps_start=0.9,
        eps_end=0.05,
        eps_decay=100000,
        target_update=1000,
    )
    .network(conv_layers=())
    .environment(env=env)
    .training()
    .debugging(log_level="INFO")
    .rendering()
    .wandb(project="mw-flockv1")
)

dqn = DQN(config)

while True:
    dqn.learn()
