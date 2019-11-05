#!/usr/bin/env python3
"""
This model is used to import the images and store them into a 3D matrix.

We prepare two strategies to parse the different techniques of in situ sequencing, which published by R Ke and CH Eng.

Here, Ke's data (R Ke, Nat. Methods, 2013) is employed as the major data structure in our software. In this data
structure, barcodes are composed of 4 types of pseudo-color, representing the A, T, C, G bases. In addition there's a
DAPI background.

In the type of Eng's data, each image is composed of 4 channels, of which, the first 3 channels represents blobs by
3 pseudo-colors and the last one is background. Then, each continuous 4 images are made a Round, also named a Cycle.
So, there are 12 pseudo-colors in a Round. For example, the Eng's data (CH Eng, Nat. Methods, 2017) include 5 Rounds,
20 images, 80 channels in any of shooting region.

Our software generate a 3D matrix to store all the images. Each channel is made of a image matrix, and insert into this
tensor in the order of cycle
"""


from sys import stderr
from cv2 import (imread, imreadmulti, imwrite,
                 add, addWeighted, warpAffine,
                 IMREAD_GRAYSCALE)
from numpy import (array,
                   uint8)

from .register_images import register_cycles


def decode_data_Ke(f_cycles):
    """
    For parsing data generated by the technique described in Ke et al, Nature Methods (2013).

    Input the directories of cycle.
    Returning a pixel matrix which contains all the gray scales of image pixel as well as their coordinates.

    :param f_cycles: The image directories in sequence of cycles, of which the different channels are stored.
    :return: A tuple including a 3D matrix and a background image matrix.
    """
    if len(f_cycles) < 1:
        print('ERROR CYCLES', file=stderr)

        exit(1)

    f_cycle_stack = []

    f_std_img = array([], dtype=uint8)
    reg_ref = array([], dtype=uint8)

    for cycle_id in range(0, len(f_cycles)):
        adj_img_mats = []

        ####################################
        # Read five channels into a matrix #
        ####################################
        channel_A = imread('/'.join((f_cycles[cycle_id], 'Y5.tif')),   IMREAD_GRAYSCALE)
        channel_T = imread('/'.join((f_cycles[cycle_id], 'FAM.tif')),  IMREAD_GRAYSCALE)
        channel_C = imread('/'.join((f_cycles[cycle_id], 'TXR.tif')),  IMREAD_GRAYSCALE)
        channel_G = imread('/'.join((f_cycles[cycle_id], 'Y3.tif')),   IMREAD_GRAYSCALE)
        channel_0 = imread('/'.join((f_cycles[cycle_id], 'DAPI.tif')), IMREAD_GRAYSCALE)
        ####################################

        #########################################################################################
        # Merge different channels from a same cycle into one matrix for following registration #
        #                                                                                       #
        # BE CARE: The parameters 'alpha' and 'beta' maybe will affect whether the registering  #
        # success. Sometimes, a registeration would succeed with only using DAPI from different #
        # cycle instead of merged images                                                        #
        #########################################################################################
        alpha = 0.7
        beta = 0.3

        merged_img = addWeighted(add(add(add(channel_A, channel_T), channel_C), channel_G), alpha, channel_0, beta, 0)
        ########
        # merged_img = channel_0  # Alternative option

        if cycle_id == 0:
            reg_ref = merged_img

            ###################################
            # Output background independently #
            ###################################
            foreground = add(add(add(channel_A, channel_T), channel_C), channel_G)
            background = channel_0

            f_std_img = addWeighted(foreground, 0.8, background, 0.6, 0)
            ########
            # f_std_img = foreground
            # f_std_img = addWeighted(foreground, 0.5, background, 0.5, 0)  # Alternative option
            # f_std_img = addWeighted(foreground, 0.4, background, 0.8, 0)  # Alternative option
            ###################################

        trans_mat = register_cycles(reg_ref, merged_img, 'BRISK')

        #############################
        # For registration checking #
        #############################
        # debug_img = warpAffine(merged_img, trans_mat, (reg_ref.shape[1], reg_ref.shape[0]))
        # imwrite('debug.cycle_' + str(int(cycle_id + 1)) + '.tif', merged_img)
        # imwrite('debug.cycle_' + str(int(cycle_id + 1)) + '.reg.tif', debug_img)
        #############################

        adj_img_mats.append(warpAffine(channel_A, trans_mat, (f_std_img.shape[1], f_std_img.shape[0])))
        adj_img_mats.append(warpAffine(channel_T, trans_mat, (f_std_img.shape[1], f_std_img.shape[0])))
        adj_img_mats.append(warpAffine(channel_C, trans_mat, (f_std_img.shape[1], f_std_img.shape[0])))
        adj_img_mats.append(warpAffine(channel_G, trans_mat, (f_std_img.shape[1], f_std_img.shape[0])))
        #########################################################################################

        ###################################################################################################
        # This stacked 3D-tensor is a common data structure for following analysis and data compatibility #
        ###################################################################################################
        f_cycle_stack.append(adj_img_mats)
        ###################################################################################################

    return f_cycle_stack, f_std_img


def decode_data_Eng(f_cycles):
    """
    For parsing data generated by the technique described in Eng et al, Nature Methods (2013) and
    Eng et al. Nature (2019)

    Input the image files in each cycle.
    Returning a pixel matrix which contains all the gray scales of image pixel as well as their coordinates

    :param f_cycles: The image files in sequence of cycles. Each file include 4 channels.
    :return: A tuple including a 3D common data tensor and a background image matrix.
    """
    if len(f_cycles) % 4 != 0:
        print('ERROR ROUNDS', file=stderr)

        exit(1)

    f_cycle_stack = []

    f_std_img = array([], dtype=uint8)
    reg_ref = array([], dtype=uint8)

    for cycle_id in range(0, len(f_cycles), 4):
        adj_img_mats = []

        _, img_r1_mats = imreadmulti(f_cycles[cycle_id + 0], None, IMREAD_GRAYSCALE)
        _, img_r2_mats = imreadmulti(f_cycles[cycle_id + 1], None, IMREAD_GRAYSCALE)
        _, img_r3_mats = imreadmulti(f_cycles[cycle_id + 2], None, IMREAD_GRAYSCALE)
        _, img_r4_mats = imreadmulti(f_cycles[cycle_id + 3], None, IMREAD_GRAYSCALE)
        ###########################################
        # Alexa 488 channel labeled all the spots #
        ###########################################
        merged_img1 = img_r1_mats[3]
        merged_img2 = img_r1_mats[3]
        merged_img3 = img_r1_mats[3]
        merged_img4 = img_r1_mats[3]
        ###########################################

        if cycle_id == 0:
            reg_ref = add(add(add(img_r1_mats[0], img_r1_mats[1]), img_r1_mats[2]), img_r1_mats[3])
            ########
            # reg_ref = merged_img1  # Alternative option

            f_std_img = merged_img1

        trans_mat1 = register_cycles(reg_ref, merged_img1, 'BRISK')
        trans_mat2 = register_cycles(reg_ref, merged_img2, 'BRISK')
        trans_mat3 = register_cycles(reg_ref, merged_img3, 'BRISK')
        trans_mat4 = register_cycles(reg_ref, merged_img4, 'BRISK')

        imwrite('debug.round_' + str(int(cycle_id / 4 + 1)) + '.tif', merged_img1)
        imwrite('debug.round_' + str(int(cycle_id / 4 + 1)) + '.tif', merged_img2)
        imwrite('debug.round_' + str(int(cycle_id / 4 + 1)) + '.tif', merged_img3)
        imwrite('debug.round_' + str(int(cycle_id / 4 + 1)) + '.tif', merged_img4)

        debug_img1 = warpAffine(merged_img1, trans_mat1, (reg_ref.shape[1], reg_ref.shape[0]))
        debug_img2 = warpAffine(merged_img2, trans_mat2, (reg_ref.shape[1], reg_ref.shape[0]))
        debug_img3 = warpAffine(merged_img3, trans_mat3, (reg_ref.shape[1], reg_ref.shape[0]))
        debug_img4 = warpAffine(merged_img4, trans_mat4, (reg_ref.shape[1], reg_ref.shape[0]))

        imwrite('debug.round_' + str(int(cycle_id / 4 + 1)) + '.reg.tif', debug_img1)
        imwrite('debug.round_' + str(int(cycle_id / 4 + 1)) + '.reg.tif', debug_img2)
        imwrite('debug.round_' + str(int(cycle_id / 4 + 1)) + '.reg.tif', debug_img3)
        imwrite('debug.round_' + str(int(cycle_id / 4 + 1)) + '.reg.tif', debug_img4)

        adj_img_mats.append(warpAffine(img_r1_mats[0], trans_mat1, (reg_ref.shape[1], reg_ref.shape[0])))
        adj_img_mats.append(warpAffine(img_r1_mats[1], trans_mat1, (reg_ref.shape[1], reg_ref.shape[0])))
        adj_img_mats.append(warpAffine(img_r1_mats[2], trans_mat1, (reg_ref.shape[1], reg_ref.shape[0])))

        adj_img_mats.append(warpAffine(img_r2_mats[0], trans_mat2, (reg_ref.shape[1], reg_ref.shape[0])))
        adj_img_mats.append(warpAffine(img_r2_mats[1], trans_mat2, (reg_ref.shape[1], reg_ref.shape[0])))
        adj_img_mats.append(warpAffine(img_r2_mats[2], trans_mat2, (reg_ref.shape[1], reg_ref.shape[0])))

        adj_img_mats.append(warpAffine(img_r3_mats[0], trans_mat3, (reg_ref.shape[1], reg_ref.shape[0])))
        adj_img_mats.append(warpAffine(img_r3_mats[1], trans_mat3, (reg_ref.shape[1], reg_ref.shape[0])))
        adj_img_mats.append(warpAffine(img_r3_mats[2], trans_mat3, (reg_ref.shape[1], reg_ref.shape[0])))

        adj_img_mats.append(warpAffine(img_r4_mats[0], trans_mat4, (reg_ref.shape[1], reg_ref.shape[0])))
        adj_img_mats.append(warpAffine(img_r4_mats[1], trans_mat4, (reg_ref.shape[1], reg_ref.shape[0])))
        adj_img_mats.append(warpAffine(img_r4_mats[2], trans_mat4, (reg_ref.shape[1], reg_ref.shape[0])))

        f_cycle_stack.append(adj_img_mats)

    return f_cycle_stack, f_std_img


######################################################
# This is a interface for Weinstein's data (DISABLE) #
#                                                    #
# Anybody could write interface for our software,    #
# for being compatible with more type of data, as    #
# long as following our 3D data structure            #
######################################################
# def decode_data_Weinstein(f_cycles):
#     """
#     For parsing the technique which published on Nature Methods in 2019 by JA Weinstein.
#
#     Input the directories of cycle.
#     Returning a pixel matrix which contains all the gray scales of image pixel as well as their coordinates
#
#     :param f_cycles:
#     :return:
#     """
#     pass
######################################################


def decode_data_Lee(f_cycles):
    """
    For parsing data generated by the technique described in Lee et al (FISSEQ), Nature Protocols (2015).
    Which are so similar with the Ke's data, and don't need a registration.

    Input the directories of cycle.
    Returning a pixel matrix which contains all the gray scales of image pixel as well as their coordinates.

    :param f_cycles: The image directories in sequence of cycles, of which the different channels are stored.
    :return: A tuple including a 3D matrix and a background image matrix.
    """
    if len(f_cycles) < 1:
        print('ERROR CYCLES', file=stderr)

        exit(1)

    f_cycle_stack = []

    f_std_img = array([], dtype=uint8)

    for cycle_id in range(0, len(f_cycles)):
        adj_img_mats = []

        cycle = '%02d' % cycle_id

        ##############################################
        # Read five channels of FISSEQ into a matrix #
        ##############################################
        channel_A = imread('/'.join((f_cycles[cycle_id], 'f3_T_' + cycle + '_C_01.tif')), IMREAD_GRAYSCALE)
        channel_T = imread('/'.join((f_cycles[cycle_id], 'f3_T_' + cycle + '_C_02.tif')), IMREAD_GRAYSCALE)
        channel_C = imread('/'.join((f_cycles[cycle_id], 'f3_T_' + cycle + '_C_03.tif')), IMREAD_GRAYSCALE)
        channel_G = imread('/'.join((f_cycles[cycle_id], 'f3_T_' + cycle + '_C_04.tif')), IMREAD_GRAYSCALE)
        channel_0 = imread('/'.join((f_cycles[cycle_id], 'f3_T_' + cycle + '_C_00.tif')), IMREAD_GRAYSCALE)
        ##############################################

        if cycle_id == 0:
            ###################################
            # Output background independently #
            ###################################
            f_std_img = channel_0

        adj_img_mats.append(channel_0)
        adj_img_mats.append(channel_A)
        adj_img_mats.append(channel_T)
        adj_img_mats.append(channel_C)
        adj_img_mats.append(channel_G)

        ###################################################################################################
        # This stacked 3D-tensor is a common data structure for following analysis and data compatibility #
        ###################################################################################################
        f_cycle_stack.append(adj_img_mats)
        ###################################################################################################

    return f_cycle_stack, f_std_img


if __name__ == '__main__':
    pass
