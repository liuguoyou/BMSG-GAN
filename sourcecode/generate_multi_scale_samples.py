""" Utility to generate multi-scale resolution grids from the trained models"""

import argparse
import torch as th
import os
from torch.backends import cudnn
from MSG_GAN.GAN import Generator
from torchvision.utils import make_grid
from torch.nn.functional import interpolate
from math import sqrt, ceil
from scipy.misc import imsave
from tqdm import tqdm

# turn on the fast GPU processing mode on
cudnn.benchmark = True


# set the manual seed
# th.manual_seed(3)


def parse_arguments():
    """
    default command line argument parser
    :return: args => parsed command line arguments
    """

    parser = argparse.ArgumentParser()

    parser.add_argument("--generator_file", action="store", type=str,
                        help="pretrained weights file for generator", required=True)

    parser.add_argument("--latent_size", action="store", type=int,
                        default=256,
                        help="latent size for the generator")

    parser.add_argument("--depth", action="store", type=int,
                        default=6,
                        help="latent size for the generator")

    parser.add_argument("--num_samples", action="store", type=int,
                        default=300,
                        help="number of synchronized grids to be generated")

    parser.add_argument("--num_columns", action="store", type=int,
                        default=None,
                        help="Number of columns " +
                             "required in the generated sample sheets")

    parser.add_argument("--out_dir", action="store", type=str,
                        default="interp_animation_frames/",
                        help="path to the output directory for the frames")

    args = parser.parse_args()

    return args


def progressive_upscaling(images):
    """
    upsamples all images to the highest size ones
    :param images: list of images with progressively growing resolutions
    :return: images => images upscaled to same size
    """
    with th.no_grad():
        for factor in range(1, len(images)):
            images[len(images) - 1 - factor] = interpolate(
                images[len(images) - 1 - factor],
                scale_factor=pow(2, factor)
            )

    return images


def main(args):
    """
    Main function for the script
    :param args: parsed command line arguments
    :return: None
    """

    print("Creating generator object ...")
    # create the generator object
    gen = th.nn.DataParallel(Generator(
        depth=args.depth,
        latent_size=args.latent_size
    ))

    print("Loading the generator weights from:", args.generator_file)
    # load the weights into it
    gen.load_state_dict(
        th.load(args.generator_file)
    )

    # path for saving the files:
    save_path = args.out_dir

    print("Generating scale synchronized images ...")
    for img_num in tqdm(range(1, args.num_samples + 1)):
        # generate the images:
        with th.no_grad():
            points = th.randn(1, args.latent_size)
            points = (points / points.norm()) * sqrt(args.latent_size)
            ss_images = gen(points)

        # resize the images:
        ss_images = progressive_upscaling(ss_images)

        # reverse the ss_images
        # ss_images = list(reversed(ss_images))

        # squeeze the batch dimension from each image
        ss_images = list(map(lambda x: th.squeeze(x, dim=0), ss_images))

        # make a grid out of them
        num_cols = int(ceil(sqrt(len(ss_images)))) if args.num_columns is None \
            else args.num_columns
        ss_image = make_grid(
            ss_images,
            nrow=num_cols,
            normalize=True,
            scale_each=True
        )

        # save the ss_image in the directory
        imsave(os.path.join(save_path, str(img_num) + ".png"),
               ss_image.permute(1, 2, 0).cpu())

    print("Generated %d images at %s" % (args.num_samples, save_path))


if __name__ == '__main__':
    main(parse_arguments())
