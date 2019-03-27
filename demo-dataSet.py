#!/usr/python
# -*- coding: UTF8-*- #
'''
####################################################################
# Demo for working with MDNT data set.
# Yuchen Jin @ cainmagi@gmail.com
# Requirements: (Pay attention to version)
#   python 3.6
#   tensorflow r1.13+
#   numpy, matplotlib
# This test should be run after the saveH5 test, which means you
# need to perform:
# ```
# python demo-saveH5.py
# ```
# at first.
# Test the performance of datasets. The data of this test is from 
# a dataset handle.
# Use
# ```
# python demo-dataSet.py -m tr -s dataset
# ```
# to train the network. Then use
# ```
# python demo-dataSet.py -m ts -s dataset -rd model-...
# ```
# to perform the test.
# Version: 1.00 # 2019/3/26
# Comments:
#   Create this project.
####################################################################
'''

import tensorflow as tf
from tensorflow.keras.datasets import mnist
import numpy as np
import random
import matplotlib.pyplot as plt

import mdnt
import os, sys
os.chdir(sys.path[0])
#mdnt.layers.conv.NEW_CONV_TRANSPOSE=False

def plot_sample(x_test, x_input=None, decoded_imgs=None, n=10):
    '''
    Plot the first n digits from the input data set
    '''
    plt.figure(figsize=(20, 4))
    rows = 1
    if decoded_imgs is not None:
        rows += 1
    if x_input is not None:
        rows += 1
        
    def plot_row(x, row, n, i):
        ax = plt.subplot(rows, n, i + 1 + row*n)
        plt.imshow(x[i].reshape(28, 28))
        plt.gray()
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        
    for i in range(n):
        # display original
        row = 0
        plot_row(x_test, row, n, i)
        if x_input is not None:
            # display reconstruction
            row += 1
            plot_row(x_input, row, n, i)
        if decoded_imgs is not None:
            # display reconstruction
            row += 1
            plot_row(decoded_imgs, row, n, i)
    plt.show()
    
def mean_loss_func(lossfunc, name=None, *args, **kwargs):
    def wrap_func(*args, **kwargs):
        return tf.keras.backend.mean(lossfunc(*args, **kwargs))
    if name is not None:
        wrap_func.__name__ = name
    return wrap_func
    
def build_model():
    # Build the model
    channel_1 = 32  # 32 channels
    channel_2 = 64  # 64 channels
    # this is our input placeholder
    input_img = tf.keras.layers.Input(shape=(28, 28, 1))
    # Create encode layers
    conv_1 = mdnt.layers.AConv2D(channel_1, (3, 3), strides=(2, 2), normalization='inst', activation='prelu', padding='same')(input_img)
    conv_2 = mdnt.layers.AConv2D(channel_2, (3, 3), strides=(2, 2), normalization='inst', activation='prelu', padding='same')(conv_1)
    deconv_1 = mdnt.layers.AConv2DTranspose(channel_1, (3, 3), strides=(2, 2), normalization='inst', activation='prelu', padding='same')(conv_2)
    deconv_2 = mdnt.layers.AConv2DTranspose(1, (3, 3), strides=(2, 2), normalization='bias', activation=tf.nn.sigmoid, padding='same')(deconv_1)
        
    # this model maps an input to its reconstruction
    denoiser = tf.keras.models.Model(input_img, deconv_2)
    denoiser.summary(line_length=90, positions=[.55, .85, .95, 1.])
    
    return denoiser

if __name__ == '__main__':
    import argparse
    
    def str2bool(v):
        if v.lower() in ('yes', 'true', 't', 'y', '1'):
            return True
        elif v.lower() in ('no', 'false', 'f', 'n', '0'):
            return False
        else:
            raise argparse.ArgumentTypeError('Unsupported value encountered.')
    
    parser = argparse.ArgumentParser(
        description='Perform regression on an analytic non-linear model in frequency domain.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Parse arguments.
    
    parser.add_argument(
        '-m', '--mode', default='', metavar='str',
        help='''\
        The mode of this demo.
            tr (train): training mode, would train and save a network.
            ts (test) : testing mode, would reload a network and give predictions.
        '''
    )
    
    parser.add_argument(
        '-r', '--rootPath', default='checkpoints', metavar='str',
        help='''\
        The root path for saving the network.
        '''
    )
    
    parser.add_argument(
        '-s', '--savedPath', default='model', metavar='str',
        help='''\
        The folder of the submodel in a particular train/test.
        '''
    )
    
    parser.add_argument(
        '-rd', '--readModel', default='model', metavar='str',
        help='''\
        The name of the model. (only for testing)
        '''
    )
    
    parser.add_argument(
        '-lr', '--learningRate', default=0.01, type=float, metavar='float',
        help='''\
        The learning rate for training the model. (only for training)
        '''
    )
    
    parser.add_argument(
        '-e', '--epoch', default=20, type=int, metavar='int',
        help='''\
        The number of epochs for training. (only for training)
        '''
    )
    
    parser.add_argument(
        '-tbn', '--trainBatchNum', default=256, type=int, metavar='int',
        help='''\
        The number of samples per batch for training. (only for training)
        '''
    )
    
    parser.add_argument(
        '-tsn', '--testBatchNum', default=10, type=int, metavar='int',
        help='''\
        The number of samples for testing. (only for testing)
        '''
    )
    
    parser.add_argument(
        '-sd', '--seed', default=None, type=int, metavar='int',
        help='''\
        Seed of the random generaotr. If none, do not set random seed.
        '''
    )
    
    args = parser.parse_args()
    def setSeed(seed):
        np.random.seed(seed)
        random.seed(seed+12345)
        tf.set_random_seed(seed+1234)
    if args.seed is not None: # Set seed for reproductable results
        setSeed(args.seed)
    
    def preproc(x):
        x = x / 255.
        x = x.reshape(28, 28, 1)
        # Add noise
        noise_factor = 0.5
        x_noisy = x + noise_factor * np.random.normal(loc=0.0, scale=1.0, size=x.shape)
        x_noisy = np.clip(x_noisy, 0., 1.)
        return (x_noisy, x)
    
    if args.mode.casefold() == 'tr' or args.mode.casefold() == 'train':
        denoiser = build_model()
        denoiser.compile(optimizer=mdnt.optimizers.optimizer('amsgrad', l_rate=args.learningRate), 
                            loss=mean_loss_func(tf.keras.losses.binary_crossentropy, name='mean_binary_crossentropy'))
        
        folder = os.path.abspath(os.path.join(args.rootPath, args.savedPath))
        if os.path.abspath(folder) == '.' or folder == '':
            args.rootPath = 'checkpoints'
            args.savedPath = 'model'
            folder = os.path.abspath(os.path.join(args.rootPath, args.savedPath))
        if tf.gfile.Exists(folder):
            tf.gfile.DeleteRecursively(folder)
        checkpointer = tf.keras.callbacks.ModelCheckpoint(filepath='-'.join((os.path.join(folder, 'model'), '{epoch:02d}e-val_acc_{val_loss:.2f}.h5')), save_best_only=True, verbose=1,  period=5)
        tf.gfile.MakeDirs(folder)
        parser_train = mdnt.data.H5GParser('mnist-train', ['X'],  batchSize=args.trainBatchNum, preprocfunc=preproc)
        dataSet_train = parser_train.getDataset()
        parser_test = mdnt.data.H5GParser('mnist-test', ['X'],  batchSize=args.trainBatchNum, preprocfunc=preproc)
        dataSet_test = parser_test.getDataset()
        denoiser.fit(dataSet_train, steps_per_epoch=parser_train.calSteps(),
                    epochs=args.epoch,
                    validation_data=dataSet_test, validation_steps=parser_test.calSteps(),
                    callbacks=[checkpointer])
    
    elif args.mode.casefold() == 'ts' or args.mode.casefold() == 'test':
        parser_test = mdnt.data.H5GParser('mnist-test', ['X'],  batchSize=args.testBatchNum, preprocfunc=preproc)
        dataSet_test = parser_test.getDataset()
        noisy, clean = next(dataSet_test)
        denoiser = mdnt.load_model(os.path.join(args.rootPath, args.savedPath, args.readModel)+'.h5', custom_objects={'mean_binary_crossentropy':mean_loss_func(tf.keras.losses.binary_crossentropy)})
        denoiser.summary(line_length=90, positions=[.55, .85, .95, 1.])
        decoded_imgs = denoiser.predict(noisy)
        plot_sample(clean, noisy, decoded_imgs, n=args.testBatchNum)
    else:
        print('Need to specify the mode manually. (use -m)')
        parser.print_help()