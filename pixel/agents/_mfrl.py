

import gym

from pixel.data.buffers import ReplayBuffer






class MFRL:
    """
    Model-Free Reinforcement Learning
    """
    def __init__(self, exp_prefix, configs, seed, device):
        print('init MFRL!')
        self.exp_prefix = exp_prefix
        self.configs = configs
        self.seed = seed
        self._device_ = device


    def _build(self):
        self._set_env()
        self._set_buffer()

    def _set_env(self):
        def seed_env(env):
            # env.seed(self.seed)
            env.action_space.seed(self.seed)
            env.observation_space.seed(self.seed)
        env_name = self.configs['environment']['name']
        evaluate = self.configs['evaluation']['evaluate']
        self.learn_env = gym.make(env_name)
        seed_env(self.learn_env)
        if evaluate:
            self.eval_env = gym.make(env_name)
            seed_env(self.eval_env)
        self.obs_dim = self.learn_env.observation_space.shape[0] # Continous S
        self.act_dim = self.learn_env.action_space.n # Discrete A
        self.env_horizon = self.learn_env.spec.max_episode_steps

    def _set_buffer(self):
        obs_dim, act_dim = self.obs_dim, self.act_dim
        max_size = self.configs['data']['buffer_size']
        self.buffer = ReplayBuffer(obs_dim, max_size)

    def interact(self, observation, Z, L, t, Traj, epsilon):
        xT = self.configs['learning']['expl_steps']
        if t > xT:
            action = self.agent.get_eps_greedy_action(observation, epsilon=epsilon)
        # else:
        #     action = self.learn_env.action_space.sample()
        observation_next, reward, terminated, truncated, info = self.learn_env.step(action)
        self.buffer.store_sarsd(observation,
                                action,
                                reward,
                                observation_next,
                                terminated)
        observation = observation_next
        Z += reward
        L += 1
        # if terminated:
        if terminated or truncated:
            Z, S, L, Traj = 0, 0, 0, Traj+1
            observation, info = self.learn_env.reset()
        return observation, Z, L, Traj

    def evaluate(self):
        evaluate = self.configs['evaluation']['evaluate']
        if evaluate:
            # print('\n[ Evaluation ]')
            EE = self.configs['evaluation']['episodes']
            MAX_H = None
            VZ, VS, VL = [], [], []
            for ee in range(1, EE+1):
                Z, S, L = 0, 0, 0
                observation, info = self.eval_env.reset()
                while True:
                    action = self.agent.get_greedy_action(observation, evaluation=True)
                    observation, reward, terminated, truncated, info = self.eval_env.step(action)
                    Z += reward
                    L += 1
                    if terminated or truncated: break
                VZ.append(Z)
                VL.append(L)
        self.eval_env.close()
        return VZ, VS, VL
