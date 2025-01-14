from rllib.algorithms.ppo.ppo import PPO
from rllib.algorithms.ppo.ppo_config import PPOConfig
from rllib.algorithms.dqn.dqn import DQN
from rllib.algorithms.dqn.dqn_config import DQNConfig
from multigrid.envs.go_to_goal import GoToGoalEnv

env = GoToGoalEnv(
    width=10,
    height=10,
    max_steps=150,
    agents=5,
    success_termination_mode="all",
    render_mode="human",
)

config = (
    PPOConfig(
        batch_size=8,
        mini_batch_size=4,
        epochs=10,
        gamma=0.99,
        lambda_=0.95,
        epsilon=0.2,
        learning_rate=1e-4,
    )
    .environment(env)
    .training()
    # .debugging(log_level="INFO")
    .rendering()
    # .wandb(project="test")
)

ppo = PPO(config)

config = (
    DQNConfig(
        batch_size=32,
        replay_buffer_size=50000,
        gamma=0.99,
        learning_rate=1e-4,
        eps_start=0.2,
        eps_end=0.05,
        eps_decay=1000000,
        target_update=1000,
    )
    .environment(env=env)
    .training()
    # .debugging(log_level="INFO")
    .rendering()
    # .wandb(project="multigrid-go-to-goal-dqn")
)
dqn = DQN(config)

while True:
    ppo.learn()
