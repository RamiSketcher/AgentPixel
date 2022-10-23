

configurations = {

    'comments': {
        'Rami': None,
    },

    'experiment': {
        'id': None,
        'device': 'cpu',
        'print_logs': True,
        'logger': 'WB',
    },

    'environment': {
        'name': 'CartPole-v1',
        'domain': 'gym',
        'horizon': int(500),
        'state': 'discrete',
        'action': 'discrete',
        'n-envs': 1,
    },

    'learning': {
        'steps': int(2e4),
        'init_steps': int(128),
        'expl_steps': int(0),
        'frequency': 1, # iteration
        'grad_steps': 1,
        'render': False,
    },

    'evaluation': {
        'evaluate': True,
        'frequency': 100, # iteration
        'episodes': 5,
        'render': False,
    },

    'algorithm': {
        'name': 'RainbowVEC',
        # 'model': None,
        # 'on-policy': False,
        # 'model-based': False,
        'hyper-parameters': {
            'gamma': 0.99,
            'alpha': 0.2,
            'beta': 0.6,
            'prio-eps': 1e-6,
            'v-min': 0.0, #
            'v-max': 200.0,
            'atom-size': 51,
            'n-steps': 3,
            'target_update_frequency': 100, # iteration
        }
    },

    'actor': {
        'type': 'greedy'
    },

    'critic': {
        'type': 'Q-functions',
        'network': {
            'optimizer': 'Adam',
            'op_activation': 'Identity',
            'activation': 'ReLU',
            'arch': [128, 128],
            'lr': 1e-3,
        }
    },

    'data': {
        'buffer_type': 'per+nSteps',
        'buffer_size': int(1e4),
        'batch_size': 128,

    }

}
