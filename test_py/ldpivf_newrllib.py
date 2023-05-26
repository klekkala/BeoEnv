import gymnasium as gym
from ray.rllib.core.rl_module.rl_module import SingleAgentRLModuleSpec
from torchvision.models import resnet18, ResNet18_Weights
from ray.rllib.core.rl_module.torch.torch_rl_module import TorchRLModule
from ray.rllib.algorithms.ppo import PPOConfig
from ray.rllib.utils.nested_dict import NestedDict
from ray.rllib.core.testing.torch.bc_module import DiscreteBCTorchModule
from ray.rllib.algorithms.ppo.ppo_catalog import PPOCatalog
from ray.rllib.core.models.specs.typing import SpecType
from ray.rllib.core.rl_module.rl_module import RLModuleConfig
from ray.rllib.algorithms.ppo.ppo_catalog import PPOCatalog
from typing import Mapping, Any
from ray.rllib.policy.policy import Policy
import cv2
import numpy as np
from ray.rllib.models.torch.torch_distributions import TorchCategorical
from pprint import pprint
from ray.rllib.policy.sample_batch import SampleBatch
#env = gym.make("ALE/BeamRider-v5")
import torch
import torch.nn as nn
import torch.utils.data
import torch.nn.functional as F


from typing import Mapping, Any

from ray.rllib.algorithms.ppo.ppo_rl_module import PPORLModule

from ray.rllib.core.models.base import ACTOR, CRITIC, ENCODER_OUT, STATE_IN
from ray.rllib.core.rl_module.rl_module import RLModule
from ray.rllib.core.rl_module.torch import TorchRLModule
from ray.rllib.policy.sample_batch import SampleBatch
from ray.rllib.utils.annotations import override
from ray.rllib.utils.framework import try_import_torch
from ray.rllib.utils.nested_dict import NestedDict

torch, nn = try_import_torch()

#from RES_VAE import VAE
from customppo import CustomPPOCatalog


class CusEnv(gym.Env):
    def __init__(self,env_config):
        self.env = gym.make("ALE/BeamRider-v5", full_action_space=True)
        self.action_space = self.env.action_space
        self.observation_space = gym.spaces.Box(0, 255, (84, 84, 3), np.uint8) #self.env.observation_space

    def reset(self, seed=None, options=None):
        obs,info = self.env.reset()
        return cv2.resize(obs, (84, 84)), info

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        obs = cv2.resize(obs, (84, 84))
        #cv2.imwrite('obs.png', obs)
        return obs, reward, terminated, truncated, info



class PPOTorchRLModule(PPORLModule, TorchRLModule):
    framework: str = "torch"

    def __init__(self, *args, **kwargs):
        TorchRLModule.__init__(self, *args, **kwargs)
        PPORLModule.__init__(self, *args, **kwargs)
        #self.blahencoder = VAE(channel_in=3, ch=32)
        #print(self.VAE)
        #checkpoint = torch.load("/lab/kiran/shelL-RL/pretrained_encoder/Models/STL10_ATTARI_84.pt")
        #self.blahencoder.load_state_dict(checkpoint['model_state_dict'])
        
        #self._weights = ResNet18_Weights.IMAGENET1K_V1
        #self.blahencoder = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
        #self._preprocess = self._weights.transforms()
        
        #self.blahencoder.eval()
        #for param in self.encoder.parameters():
        #    print(param.requires_grad)
        
        print(type(self.encoder))
        print(type(self.pi))
        print(type(self.vf))

    def _forward_inference(self, batch: NestedDict) -> Mapping[str, Any]:
        output = {}
        """
        # TODO (Artur): Remove this once Policy supports RNN
        if self.encoder.config.shared:
            batch[STATE_IN] = None
        else:
            batch[STATE_IN] = {
                ACTOR: None,
                CRITIC: None,
            }
        batch[SampleBatch.SEQ_LENS] = None
        

        with torch.no_grad():
            batch['obs'] = self.blahencoder(batch['obs'].cuda()).detach()
            encoder_outs = self.encoder(batch['obs']).detach()

        # TODO (Artur): Un-uncomment once Policy supports RNN
        # output[STATE_OUT] = encoder_outs[STATE_OUT]

        # Actions
        action_logits = self.pi(encoder_outs[ENCODER_OUT][ACTOR])
        output[SampleBatch.ACTION_DIST_INPUTS] = action_logits
        """
        return output

    def _forward_exploration(self, batch: NestedDict) -> Mapping[str, Any]:
        """PPO forward pass during exploration.
        Besides the action distribution, this method also returns the parameters of the
        policy distribution to be used for computing KL divergence between the old
        policy and the new policy during training.
         """
        with torch.no_grad():
        #    batch['obs'] = self.blahencoder(batch['obs'].cuda())[1]
            return self._common_forward(batch)

    def _forward_train(self, batch: NestedDict) -> Mapping[str, Any]:
        #with torch.no_grad():
        #    batch['obs'] = self.blahencoder(batch['obs'].cuda())[1]
        return self._common_forward(batch)

    def _common_forward(self, batch: NestedDict) -> Mapping[str, Any]:
        output = {}

        # TODO (Artur): Remove this once Policy supports RNN

        if self.encoder.config.shared:
            batch[STATE_IN] = None
        else:
            batch[STATE_IN] = {
                ACTOR: None,
                CRITIC: None,
            }
        batch[SampleBatch.SEQ_LENS] = None

        encoder_outs = self.encoder(batch)
        
        # TODO (Artur): Un-uncomment once Policy supports RNN
        # output[STATE_OUT] = encoder_outs[STATE_OUT]

        # Value head
        vf_out = self.vf(encoder_outs[ENCODER_OUT][CRITIC])
        output[SampleBatch.VF_PREDS] = vf_out.squeeze(-1)

        # Policy head
        action_logits = self.pi(encoder_outs[ENCODER_OUT][ACTOR])
        output[SampleBatch.ACTION_DIST_INPUTS] = action_logits

        return output

spec = SingleAgentRLModuleSpec(
    module_class=PPOTorchRLModule,
    #observation_space=gym.spaces.Box(0, 255, (84, 84, 3), np.uint8),
    #action_space=gym.spaces.Discrete(18),
    model_config_dict={"vf_share_layers": True, "encoder_latent_dim": 32,
        "conv_filters": None,
        "fcnet_hiddens": [128, 32]},
    catalog_class=CustomPPOCatalog
)

config = (
    PPOConfig()
    .environment(CusEnv, env_config={
        "frameskip": 1,
        "full_action_space": False,
        "repeat_action_probability": 0.0
    })
    .training(_enable_learner_api=True)
    .rl_module(
        _enable_rl_module_api=True,
        rl_module_spec=spec,
    )
    .training(model={"vf_share_layers": True,
        "fcnet_hiddens": [32],
        "conv_filters": [[16, 4, 2], [32, 4, 2], [64, 4, 2], [128, 4, 2]]},
        lambda_=0.95,
        lr=0.0001,
        kl_coeff=0.5,
        clip_param=0.1,
        vf_clip_param=10.0,
        grad_clip=100.0,
        entropy_coeff=0.01,
        #entropy_coeff=0.9,
        train_batch_size=5000,
        sgd_minibatch_size=500,
        num_sgd_iter=10)
    #.exploration(exploration_config={})
    .reporting(min_time_s_per_iteration=30)
    .rollouts(num_rollout_workers=1,
        num_envs_per_worker=1,
        rollout_fragment_length='auto')
    .resources(
        num_gpus_per_learner_worker = 2,
        num_gpus=0,
        num_learner_workers=1,
        num_cpus_per_worker=.5,
        num_gpus_per_worker=0)
        #num_cpus_for_local_worker = 1,
)

my_restored_policy = Policy.from_checkpoint("/lab/kiran/ray_results/PPO_CusEnv_2023-05-22_16-16-263lnit9sp/checkpoint_000004/policies/default_policy/")

temp = my_restored_policy.get_weights()
algorithm = config.build()
plc = algorithm.get_policy().get_weights()
for i in temp.keys():
    if 'mlp' in i:
        plc[i]=temp[i]
algorithm.get_policy().set_weights(plc)


# run for 2 training steps
for _ in range(1):
    result = algorithm.train()
    pprint(result)

