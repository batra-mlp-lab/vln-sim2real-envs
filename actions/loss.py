import torch
import torch.nn as nn
import ot
import numpy as np

from utils import radial_cost_matrix

class SinkhornImageLoss(nn.Module):

    def __init__(self, reduction='mean'):
        super(SinkhornImageLoss, self).__init__()
        self.logsoftmax = nn.LogSoftmax(dim=1)
        self.softmax = nn.Softmax(dim=1)
        self.C = torch.from_numpy(radial_cost_matrix()).float().cuda()
        self.criterion = SinkhornDistance(self.C, reduction=reduction)

    def forward(self, pred_logits, target_probs, compute_emd=False):
        # Predicted logits and target probabilities shaped (N, 1, H, W)
        batch_size = pred_logits.shape[0]
        pred_logp = self.logsoftmax(pred_logits.flatten(1))
        target_logp = torch.log(target_probs+1e-8).reshape(batch_size, -1)
        loss, P = self.criterion(pred_logp, target_logp)

        if compute_emd:
            emd = np.zeros(batch_size)
            pred_probs = self.softmax(pred_logits.flatten(1)).cpu().numpy()
            target_probs = target_probs.flatten(1).cpu().numpy()
            cost = self.C[0].cpu().numpy()
            for n in range(batch_size): 
              emd[n] = ot.emd2(pred_probs[n], target_probs[n], cost)
        else:
            emd = None
        return loss, emd



# Adapted from https://github.com/gpeyre/SinkhornAutoDiff
class SinkhornDistance(nn.Module):
    r"""
    Sinkhorn distance between two grayscale images.

    Args:
        C (1, H, W): cost matrix
        eps (float): regularization coefficient
        max_iter (int): maximum number of Sinkhorn iterations
        reduction (string, optional): Specifies the reduction to apply to the output:
            'none' | 'mean' | 'sum'. 'none': no reduction will be applied,
            'mean': the sum of the output will be divided by the number of
            elements in the output, 'sum': the output will be summed. Default: 'none'

    Shape:
        Input: (N, H, W) log probabilities
    """
    def __init__(self, C, eps=0.01, max_iter=10, reduction='mean'):
        super(SinkhornDistance, self).__init__()
        self.eps = eps
        self.max_iter = max_iter
        self.reduction = reduction
        self.C = C

    def forward(self, mu_logp, nu_logp):

        assert mu_logp.shape == nu_logp.shape
        assert len(mu_logp.shape) == 2
        batch_size = mu_logp.shape[0]
        num_points =  mu_logp.shape[1]

        u = torch.zeros_like(mu_logp)
        v = torch.zeros_like(nu_logp)
        # To check if algorithm terminates because of threshold
        # or max iterations reached
        actual_nits = 0
        # Stopping criterion
        thresh = 1e-1

        # Sinkhorn iterations
        for i in range(self.max_iter):
            u1 = u  # useful to check the update
            u = self.eps * (mu_logp - torch.logsumexp(self.M(self.C, u, v), dim=-1)) + u
            v = self.eps * (nu_logp - torch.logsumexp(self.M(self.C, u, v).transpose(-2, -1), dim=-1)) + v
            err = (u - u1).abs().sum(-1).mean()
            actual_nits += 1
            if err.item() < thresh:
                break

        U, V = u, v
        # Transport plan pi = diag(a)*K*diag(b)
        pi = torch.exp(self.M(self.C, U, V))
        # Sinkhorn distance
        cost = torch.sum(pi * self.C, dim=(-2, -1))

        if self.reduction == 'mean':
            cost = cost.mean()
        elif self.reduction == 'sum':
            cost = cost.sum()

        return cost, pi

    def M(self, C, u, v):
        "Modified cost for logarithmic updates"
        "$M_{ij} = (-c_{ij} + u_i + v_j) / \epsilon$"
        return (-C + u.unsqueeze(-1) + v.unsqueeze(-2)) / self.eps


    


