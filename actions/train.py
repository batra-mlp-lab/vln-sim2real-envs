import argparse
import logging
import os
import sys

import numpy as np
import torch
import torch.nn as nn
from torch import optim
from tqdm import tqdm
from loss import SinkhornImageLoss

from eval import eval_net
from dataloader import DataLoader
from utils import read_img_features
from unet import UNet

torch.set_printoptions(precision=3, sci_mode=False)

dir_checkpoint = 'chpts/'



def train_net(net,
              device,
              epochs=5,
              batch_size=1,
              num_examples=20,
              lr=0.1,
              save_cp=True,
              scan_dropout=0):

    features = read_img_features()
    train = DataLoader(features, splits=['train'], bs=batch_size, augment=True, dropout=scan_dropout)
    val = DataLoader(features, splits=['val'], bs=batch_size, dropout=scan_dropout)
    n_train = len(train.data)
    n_val = len(val.data)

    logging.info(f'''Starting training:
        Epochs:          {epochs}
        Batch size:      {batch_size}
        Learning rate:   {lr}
        Training size:   {n_train}
        Scan dropout:    {scan_dropout}
        Validation size: {n_val}
        Checkpoints:     {save_cp}
        Device:          {device.type}
    ''')

    optimizer = optim.Adam(net.parameters(), lr=lr)
    criterion = SinkhornImageLoss()

    val_loss, val_emd = eval_net(net, val, device, num_examples)
    logging.info('Validation Loss at Initialization: {0:.2f}m'.format(val_loss))
    logging.info('Validation EMD at Initialization: {0:.2f}m'.format(val_emd))

    for epoch in range(epochs):
        net.train()

        epoch_loss = 0
        n_batches = n_train//batch_size
        with tqdm(total=n_train, desc=f'Epoch {epoch + 1}/{epochs}', unit='img') as pbar:
            for i in range(n_batches):

                scans, feats, true_masks, _ = train.get_batch()

                scans = torch.from_numpy(scans).to(device=device)
                feats = torch.from_numpy(feats).to(device=device)
                true_masks = torch.from_numpy(true_masks).to(device=device)

                masks_pred = net(scans,feats)
                loss, _ = criterion(masks_pred, true_masks, compute_emd=False)
                epoch_loss += loss.item()

                pbar.set_postfix(**{'loss (batch)': loss.item()})

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                pbar.update(batch_size)

        logging.info('Train Loss: {0:.2f}m'.format(epoch_loss/n_batches))

        if save_cp:
            try:
                os.mkdir(dir_checkpoint)
                logging.info('Created checkpoint directory')
            except OSError:
                pass
            torch.save(net.state_dict(),
                       dir_checkpoint + f'CP_epoch{epoch + 1}.pth')
            logging.info(f'Checkpoint {epoch + 1} saved !')

        val_loss, val_emd = eval_net(net, val, device, num_examples)
        logging.info('Validation Loss: {0:.2f}m'.format(val_loss))
        logging.info('Validation EMD: {0:.2f}m'.format(val_emd))

def evaluation(net, device, num_examples):
    features = read_img_features()
    val = DataLoader(features, splits=['val'], bs=1)
    val_loss, val_emd = eval_net(net, val, device, num_examples)


def get_args():
    parser = argparse.ArgumentParser(description='Train the UNet on images and target masks',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-e', '--epochs', metavar='E', type=int, default=20,
                        help='Number of epochs', dest='epochs')
    parser.add_argument('-b', '--batch-size', metavar='B', type=int, nargs='?', default=32,
                        help='Batch size', dest='batchsize')
    parser.add_argument('-l', '--learning-rate', metavar='LR', type=float, nargs='?', default=0.1,
                        help='Learning rate', dest='lr')
    parser.add_argument('-sd', '--scan-dropout', metavar='SD', type=float, nargs='?', default=0.05,
                        help='Dropout on scans in both train and test', dest='scan_dropout')
    parser.add_argument('-md', '--model-dropout', metavar='D', type=float, nargs='?', default=0.2,
                        help='Dropout on model layers during training', dest='model_dropout')
    parser.add_argument('-f', '--load', dest='load', type=str, default=False,
                        help='Load model from a .pth file')
    parser.add_argument('-v', '--eval', dest='eval', action='store_true', help='Evaluate model')
    parser.add_argument('-ex', '--examples', metavar='EX', dest='examples', type=int, default=20,
                        help='Number of example predictions to save')
    return parser.parse_args()



if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    args = get_args()
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logging.info(f'Using device {device}')

    net = UNet(n_channels=2, n_classes=1, ch=64, dropout=args.model_dropout)
    logging.info(f'Network:\n'
                 f'\t{net.n_channels} input channels\n'
                 f'\t{net.n_classes} output channels (classes)\n'
                 f'\t{"Bilinear" if net.bilinear else "Dilated conv"} upscaling')

    if args.load:
        net.load_state_dict(
            torch.load(args.load, map_location=device)
        )
        logging.info(f'Model loaded from {args.load}')

    net.to(device=device)
    # faster convolutions, but more memory
    # cudnn.benchmark = True
    if args.eval:
        evaluation(net,device,args.examples)
    else:
        try:
            train_net(net=net,
                      epochs=args.epochs,
                      batch_size=args.batchsize,
                      num_examples=args.examples,
                      lr=args.lr,
                      device=device,
                      scan_dropout=args.scan_dropout)
        except KeyboardInterrupt:
            torch.save(net.state_dict(), 'INTERRUPTED.pth')
            logging.info('Saved interrupt')
            try:
                sys.exit(0)
            except SystemExit:
                os._exit(0)
