"""
Adapted from:
    1. https://github.com/openai/gym
    2. https://github.com/mgbellemare/Arcade-Learning-Environment
    3. https://github.com/ShangtongZhang/DeepRL
    4. https://github.com/Kaixhin/Rainbow

"""
import psutil
import argparse
import time, datetime
from tqdm import tqdm, trange

import wandb
import numpy as np

import gym
from gym.spaces import Box, Discrete, MultiDiscrete
# from gym.wrappers import AtariPreprocessing, FrameStack
from gym.vector.async_vector_env import AsyncVectorEnv
from gym.vector.sync_vector_env import SyncVectorEnv

from pixel.envs.wrappers import AtariPreprocessing, FrameStack

from pixel.envs.atari_env import AtariEnv


class GymMaker:
    def __init__(self, configs, eval=False, device=None, seed=0):
        # print('Initialize GymMaker')
        self.configs = configs
        self.eval = eval
        self._device_ = device
        self.seed = seed
        self.name = configs['name']
        self.env = self._gym_make(configs, eval, device, seed)
        # if configs['domain'] == 'atari':
        #     self.observation_space = self.env.observation_space
        #     self.observation_dim = self.env.observation_dim
        #     self.action_space = self.env.action_space
        #     self.action_dim = self.env.action_dim
        # else:
        self.observation_space = self.env.observation_space
        if configs['state'] == 'pixel':
            self.observation_dim = 'pixel'
        else:
            self.observation_dim = int(np.prod(self.observation_space.shape[0]))
        self.action_space = self.env.action_space
        if isinstance(self.action_space, Box):
            self.action_dim = self.action_space.shape[0]
        elif isinstance(self.action_space, Discrete):
            self.action_dim = self.action_space.n
        elif isinstance(self.env.single_action_space, Discrete):
            self.action_dim = self.env.single_action_space.n

        # self._seed_env()

        # self.lives = 0
        # self.life_terminal = False

    def _gym_make(self, configs, eval, device, seed):
        def create_env():
            def _make():
                if configs['domain'] == 'atari':
                    env = AtariEnv(configs, eval, device, seed)
                else:
                    env = gym.make(
                            id=configs['name'],
                            frameskip=configs['frameskip'],
                            max_num_frames_per_episode=configs['max-frames'],
                            repeat_action_probability=configs['repeat-action-probability'],
                            )
                return env
            return _make

        # if configs['domain'] == 'atari':
        #     env = create_env()
        #     return env()
        # else:
        if (configs['n-envs'] == 0) or eval:
            if eval: configs['pre-processing']['terminal_on_life_loss'] = False
            env = create_env()
            return env()
        else:
            env_fns = [ create_env() for e in range(configs['n-envs']) ]
            return AsyncVectorEnv(env_fns) if configs['asynchronous'] else SyncVectorEnv(env_fns)

    def _seed_env(self):
        self.env.action_space.seed(self.seed)
        self.env.observation_space.seed(self.seed)

    def reset(self, seed=None):
        return self.env.reset(seed=seed)

    def step(self, action):
        return self.env.step(action)

    def render(self):
        return self.env.render()

    def close(self):
        return self.env.close()




# environment = {
#     # 'name': 'ALE/Asterix-v5',
#     # 'name': 'ALE/Boxing-v5',
#     # 'name': 'ALE/Breakout-v5',
#     'name': 'ALE/Hero-v5',
#     'domain': 'atari',
#     'state': 'pixel',
#     'action': 'discrete',
#     'n-envs': 1,
#     'asynchronous': True,
#     'n-stacks': 4,
#     'frame-skip': 4,
#     'reward-clip': False,
#     'max-steps': int(27e3), # per episode
#     'max-frames': int(108e3), # per episode
#     'pre-process': ['AtariPreprocessing'],
# }


# if __name__ == '__main__':
#     # parser = argparse.ArgumentParser()
#     # for k, v in environment.items():
#     #     parser.add_argument(f"--{k}", type=type(v), default=v)
#     # configs = parser.parse_args()
#
#     configs = environment
#
#
#     env = GymMaker(configs)
#
#     observation, info = env.reset()
#     # envs.render()
#     mask = np.ones([max(1, configs['n-envs'])], dtype=bool)
#     total_steps = 0
#
#     LS = int(1e4)
#     LT = trange(1, LS+1, desc=configs['name'], position=0)
#
#     for t in LT:
#         if mask.sum()==0:
#             o, info = env.reset()
#             mask = np.ones([max(1, configs['n-envs'])], dtype=bool)
#             # envs.render()
#         action = env.action_space.sample()
#         print('observation: ', observation.shape)
#         print('action: ', action)
#         observation_next, reward, terminated, truncated, info = env.step(action)
#         print('reward: ', reward)
#         print('terminated: ', terminated)
#         # envs.render()
#         # time.sleep(0.05)
#         if configs['n-envs'] == 0:
#             terminated, truncated = np.array([terminated]), np.array([truncated])
#         mask[mask] = ~terminated[mask]
#         mask[mask] = ~truncated[mask]
#         total_steps += mask.sum()
#         if total_steps >= LS: break
#     print('observation: ', observation.shape)
#     env.close()
