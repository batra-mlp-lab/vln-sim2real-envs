
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from tqdm import tqdm
import numpy as np
from PIL import Image

from utils import visualize_pred, bin_distance, DATA_DIR
from loss import SinkhornImageLoss


def neighborhoods(mu, x_range, y_range, sigma, circular_x=True, gaussian=False):
    """ Generate masks centered at mu of the given x and y range with the
        origin in the centre of the output 
    Inputs:
        mu: tensor (N, 2)
    Outputs:
        tensor (N, y_range, s_range)
    """
    x_mu = mu[:,0].unsqueeze(1).unsqueeze(1)
    y_mu = mu[:,1].unsqueeze(1).unsqueeze(1)
    # Generate bivariate Gaussians centered at position mu
    x = torch.arange(start=0,end=x_range, device=mu.device, dtype=mu.dtype).unsqueeze(0).unsqueeze(0)
    y = torch.arange(start=0,end=y_range, device=mu.device, dtype=mu.dtype).unsqueeze(1).unsqueeze(0)
    y_diff = y - y_mu
    x_diff = x - x_mu
    if circular_x:
        x_diff = torch.min(torch.abs(x_diff), torch.abs(x_diff + x_range))
    if gaussian:
        output = torch.exp(-0.5 * ((x_diff/sigma)**2 + (y_diff/sigma)**2 ))
    else:
        output = torch.logical_and(torch.abs(x_diff) <= sigma, torch.abs(y_diff) <= sigma).type(mu.dtype)
    return output


def nms(pred, max_predictions=10, sigma=1.0, gaussian=False):
    ''' Input (batch_size, 1, height, width) '''

    shape = pred.shape
    output = torch.zeros_like(pred)
    flat_pred = pred.reshape((shape[0],-1))
    supp_pred = pred.clone()
    flat_output = output.reshape((shape[0],-1))
    for i in range(max_predictions):
        # Find and save max
        flat_supp_pred = supp_pred.reshape((shape[0],-1))
        val,ix = torch.max(flat_supp_pred, dim=1)
        indices = torch.arange(0,shape[0])
        flat_output[indices,ix] = flat_pred[indices,ix]

        # Suppression
        y = ix / shape[-1]
        x = ix % shape[-1]
        mu = torch.stack([x,y], dim=1).float()
        g = neighborhoods(mu, shape[-1], shape[-2], sigma, gaussian=gaussian)
        supp_pred *= (1-g.unsqueeze(1))

    output[output < 0] = 0
    return output


def eval_net(net, dataset, device, num_examples):
    """Evaluation"""
    net.eval()
    val_loss = 0
    val_emd = 0
    criterion = SinkhornImageLoss(reduction='none')

    dataset.reset_epoch()
    n_items = len(dataset.data)
    n_batches = math.ceil(n_items/dataset.batch_size)
    last_batch_size = n_items % dataset.batch_size
    saved_ims = 0
    with torch.no_grad():
        for i in range(n_batches):

            scans, feats, true_masks, long_ids = dataset.get_batch()

            scans = torch.from_numpy(scans).to(device=device)
            feats = torch.from_numpy(feats).to(device=device)
            true_masks = torch.from_numpy(true_masks).to(device=device)

            masks_pred = net(scans,feats)
            norm_pred = F.softmax(masks_pred.flatten(1), dim=1).reshape(masks_pred.shape)
            nms_pred = nms(norm_pred)

            loss, emd = criterion(masks_pred, true_masks, compute_emd=True)
            keep = loss.shape[0] if i+1 < n_batches else last_batch_size

            if saved_ims < num_examples:
                for j in range(dataset.batch_size):
                    scan,viewpoint = long_ids[j].split('_')
                    # Load equirectangular images that have y-axis in center of image.
                    path = '%sequirectangular-v1-small/%s/%s.jpeg' % (DATA_DIR, scan, viewpoint)
                    equi = np.array(Image.open(path))
                    # Roll image by 15 degrees to match the scans and image features.
                    equi = np.roll(equi, 512//24, axis=1)
                    visualize_pred(scans[j], norm_pred[j], true_masks[j], equi, saved_ims)
                    saved_ims += 1
                    if saved_ims >= num_examples:
                        break

            if keep == 0:
                break
            val_loss += loss[:keep].sum().item()
            val_emd += emd[:keep].sum().item()
    return val_loss/n_items, val_emd/n_items
