import os, subprocess, sys
import argparse
import importlib
import time, datetime
import random

from typing import Tuple, List, Dict
from random import sample
from dataclasses import dataclass
from tqdm import tqdm, trange

import wandb

import numpy as np
import torch as T
nn, F = T.nn, T.nn.functional

from pixel.agents._mfrl import MFRL
from pixel.agents.dqn import DQNAgent
from pixel.networks.value_functions import QNetwork


class DDQNAgent:
# class DDQNAgent(DQNAgent):
    def __init__(self,
                 obs_dim, act_dim,
                 configs, seed, device):
        print('Initialize DDQN Agent')
        self.obs_dim, self.act_dim= obs_dim, act_dim
        self.configs, self.seed = configs, seed
        self._device_ = device
        self.online_net, self.target_net = None, None
        self._build()

    def _build(self):
        self.online_net, self.target_net = self._set_q(), self._set_q()
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.target_net.eval()

    def _set_q(self):
        obs_dim, act_dim = self.obs_dim, self.act_dim
        net_configs = self.configs['critic']['network']
        seed, device = self.seed, self._device_
        return QNetwork(obs_dim, act_dim, net_configs, seed, device)

    def get_q(self, observation, action):
        return self.online_net(observation).gather(1, action)

    def get_double_q_target(self, observation):
        with T.no_grad():
            return self.target_net(observation).gather(1, self.online_net(observation).argmax(dim=1, keepdim=True))

    def get_greedy_action(self, observation, evaluation=False): # Select Action(s) based on eps_greedy
        with T.no_grad():
            return self.online_net(T.FloatTensor(observation).to(self._device_)).argmax().cpu().numpy()

    def get_eps_greedy_action(self, observation, epsilon=0.001, evaluation=False): # Select Action(s) based on eps_greedy
        if np.random.random() < epsilon:
            return np.random.randint(0, self.act_dim)
        else:
            return self.get_greedy_action(observation)

    def get_action(self, observation, epsilon=0.001):
        return self.get_eps_greedy_action(observation, epsilon)



class DDQNLearner(MFRL):
    """
    Double Deep Q Network (DDQN) [DeepMind (van Hasselt et al.); 20??]
    """
    def __init__(self, exp_prefix, configs, seed, device, wb):
        super(DDQNLearner, self).__init__(exp_prefix, configs, seed, device)
        print('Initialize DDQN Learner')
        self.configs = configs
        self.seed = seed
        self._device_ = device
        self.WandB = wb
        self._build()

    def _build(self):
        super(DDQNLearner, self)._build()
        self._build_ddqn()

    def _build_ddqn(self):
        self._set_agent()

    def _set_agent(self):
        self.agent = DDQNAgent(self.obs_dim, self.act_dim, self.configs, self.seed, self._device_)

    def learn(self):
        LT = self.configs['learning']['steps']
        iT = self.configs['learning']['init_steps']
        xT = self.configs['learning']['expl_steps']
        Lf = self.configs['learning']['frequency']
        Vf = self.configs['evaluation']['frequency']
        G = self.configs['learning']['grad_steps']
        alg = self.configs['algorithm']['name']
        epsilon = self.configs['algorithm']['hyper-parameters']['init-epsilon']

        oldJq = 0
        Z, S, L, Traj = 0, 0, 0, 0
        DQNLT = trange(1, LT+1, desc=alg)
        observation, info = self.learn_env.reset()
        logs, ZList, LList, JQList = dict(), [0], [0], []
        termZ, termL = 0, 0
        # EPS = []

        for t in DQNLT:
            observation, Z, L, Traj_new = self.interact(observation, Z, L, t, Traj, epsilon)
            if (Traj_new - Traj) > 0:
                # termZ, termL = lastZ, lastL
                ZList.append(lastZ), LList.append(lastL)
            else:
                lastZ, lastL = Z, L
            Traj = Traj_new

            if (t>iT):
            # if (t>iT) and ((t-1)%Lf == 0):
                Jq = self.train_ddqn(t)
                oldJq = Jq
                epsilon = self.update_epsilon(epsilon)
            else:
                Jq = oldJq

            if ((t-1)%Vf == 0):
                VZ, VS, VL = self.evaluate()
                logs['data/env_buffer_size                '] = self.buffer.size
                logs['training/ddqn/Jq                     '] = Jq
                logs['training/ddqn/epsilon                '] = epsilon
                logs['learning/real/rollout_return_mean   '] = np.mean(ZList)
                logs['learning/real/rollout_return_std    '] = np.std(ZList)
                logs['learning/real/rollout_length        '] = np.mean(LList)
                # logs['learning/real/rollout_return_mean   '] = termZ
                # logs['learning/real/rollout_return_std    '] = termZ
                # logs['learning/real/rollout_length        '] = termL
                logs['evaluation/episodic_return_mean     '] = np.mean(VZ)
                logs['evaluation/episodic_return_std      '] = np.std(VZ)
                logs['evaluation/episodic_length_mean     '] = np.mean(VL)
                DQNLT.set_postfix({'Traj': Traj, 'learnZ': np.mean(ZList), 'evalZ': np.mean(VZ)})
                if self.WandB: wandb.log(logs, step=t)

        VZ, VS, VL = self.evaluate()
        logs['data/env_buffer_size                '] = self.buffer.size
        logs['training/ddqn/Jq                     '] = Jq
        logs['training/ddqn/epsilon                '] = epsilon
        logs['learning/real/rollout_return_mean   '] = np.mean(ZList)
        logs['learning/real/rollout_return_std    '] = np.std(ZList)
        logs['learning/real/rollout_length        '] = np.mean(LList)
        # logs['learning/real/rollout_return_mean   '] = termZ
        # logs['learning/real/rollout_return_std    '] = termZ
        # logs['learning/real/rollout_length        '] = termL
        logs['evaluation/episodic_return_mean     '] = np.mean(VZ)
        logs['evaluation/episodic_return_std      '] = np.std(VZ)
        logs['evaluation/episodic_length_mean     '] = np.mean(VL)
        if self.WandB: wandb.log(logs, step=t)

        self.learn_env.close()
        self.eval_env.close()

    def train_ddqn(self, t) -> T.Tensor:
        batch_size = self.configs['data']['batch_size']
        TUf = self.configs['algorithm']['hyper-parameters']['target_update_frequency']
        batch = self.buffer.sample_batch(batch_size, device=self._device_)
        Jq = self.update_online_net(batch)
        Jq = Jq.item()
        if ((t-1)%TUf == 0): self.update_target_net()
        return Jq

    def update_online_net(self, batch: Dict[str, np.ndarray]) -> T.Tensor:
        gamma = self.configs['algorithm']['hyper-parameters']['gamma']

        observations = T.FloatTensor(batch['observations']).to(self._device_)
        actions = T.LongTensor(batch['actions']).to(self._device_)
        rewards = T.FloatTensor(batch['rewards']).to(self._device_)
        observations_next = T.FloatTensor(batch['observations_next']).to(self._device_)
        terminals = T.FloatTensor(batch['terminals']).to(self._device_)

        q_value = self.agent.get_q(observations, actions)
        q_next = self.agent.get_double_q_target(observations_next)
        q_target = rewards + gamma * (1 - terminals) * q_next
        Jq = F.smooth_l1_loss(q_value, q_target)

        self.agent.online_net.optimizer.zero_grad()
        Jq.backward()
        self.agent.online_net.optimizer.step()

        return Jq

    def update_target_net(self) -> None:
        self.agent.target_net.load_state_dict(self.agent.online_net.state_dict())

    def update_epsilon(self, epsilon):
        max_epsilon = self.configs['algorithm']['hyper-parameters']['max-epsilon']
        min_epsilon = self.configs['algorithm']['hyper-parameters']['min-epsilon']
        epsilon_decay = self.configs['algorithm']['hyper-parameters']['epsilon-decay']
        return max(min_epsilon,
                   epsilon - (max_epsilon - min_epsilon) * epsilon_decay)

    def func2(self):
        pass





def main(exp_prefix, config, seed, device, wb):

    print('Start DDQN experiment...')
    print('\n')

    configs = config.configurations

    if seed:
        random.seed(seed), np.random.seed(seed), T.manual_seed(seed)

    alg_name = configs['algorithm']['name']
    env_name = configs['environment']['name']
    env_domain = configs['environment']['domain']

    group_name = f"{env_name}-{alg_name}" # H < -2.7
    exp_prefix = f"seed:{seed}"
    # print('group: ', group_name)

    if wb:
        wandb.init(
            group=group_name,
            name=exp_prefix,
            project=f'VECTOR',
            config=configs
        )

    ddqn_learner = DDQNLearner(exp_prefix, configs, seed, device, wb)

    ddqn_learner.learn()

    print('\n')
    print('... End DDQN experiment')



if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('-exp_prefix', type=str)
    parser.add_argument('-cfg', type=str)
    parser.add_argument('-seed', type=str)
    parser.add_argument('-device', type=str)
    parser.add_argument('-wb', type=str)

    args = parser.parse_args()

    exp_prefix = args.exp_prefix
    # sys.path.append(f"{os.getcwd()}/configs")
    sys.path.append(f"pixel/configs")
    config = importlib.import_module(args.cfg)
    seed = int(args.seed)
    device = args.device
    wb = eval(args.wb)

    main(exp_prefix, config, seed, device, wb)
