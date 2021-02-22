# Bounding boxes for weakly supervised segmentation: Global constraints get close to full supervision
Official repository for [Bounding boxes for weakly supervised segmentation: Global constraints get close to full supervision](http://proceedings.mlr.press/v121/kervadec20a.html), oral at [MIDL 2020](https://2020.midl.io). Recording of the talk is available [on the MIDL YouTube channel](https://youtu.be/1HIK_z-XeMU).


* [MIDL 2020 Proceedings](http://proceedings.mlr.press/v121/kervadec20a.html)
* [arXiv preprint](https://arxiv.org/abs/2004.06816)

## Table of contents
* [Table of contents](#table-of-contents)
* [Requirements (PyTorch)](#requirements-pytorch)
* [Usage](#usage)
* [Automation](#automation)
    * [Data scheme](#data-scheme)
        * [dataset](#dataset)
        * [results](#results)
    * [Cool tricks](#cool-tricks)

## Requirements (PyTorch)
To reproduce our experiments:
* python3.8+
* Pytorch 1.5+
* nibabel (only when slicing 3D volumes)
* Scipy
* NumPy
* Matplotlib
* Scikit-image
* zsh

## Usage
The most important part of the code is contained in [`bounds.py`](bounds.py), with the definition of the `BoxPriorBounds`. (`BoxBounds` is used for the emptyness constraints on the size of the box.) It generates a list of tuples, each tuple containing the mask of the segment (one-hot encoded), and its lower bound (`w` or lower). Those tuples are then used by the `BoxPrior` loss in [`losses.py`](losses.py).

In short, things go in the following order:
- `BoxPriorBounds` generates a list of (segment,width) pairs `list[tuple[Tensor, Tensor]` ;
- the dataloader returns them with the key `'box_priors'` ;
- `BoxPrior` consumes that list of tuples (basically doing a pixel-wise multiplication between the segment and the softmax, then enforcing the lower bound).



## Automation
Experiments are handled by [GNU Make](https://en.wikipedia.org/wiki/Make_(software)). It should be installed on pretty much any machine.

Instruction to download the data are contained in the lineage files [prostate.lineage](data/prostate.lineage) and [atlas.lineage](data/atlas.lineage). They are text files containing the md5sum of the original zip.

Once the zip is in place, everything should be automatic:
```sh
make -f prostate.make
make -f atlas.make
```
Usually takes a little bit more than a day per makefile.

This perform in the following order:
* unpacking of the data;
* remove unwanted big files;
* normalization and slicing of the data;
* training with the different methods;
* plotting of the metrics curves;
* display of a report;
* archiving of the results in an .tar.gz stored in the `archives` folder.

Make will handle by itself the dependencies between the different parts. For instance, once the data has been pre-processed, it won't do it another time, even if you delete the training results. It is also a good way to avoid overwriting existing results by accident.

Of course, parts can be launched separately :
```sh
make -f prostate.make data/prostate # Unpack only
make -f prostate.make data/prostate # unpack if needed, then slice the data
make -f prostate.make results/prostate/box_prior_box_size_neg_size # train only that setting. Create the data if needed
make -f prostate.make results/prostate/val_dice.png # Create only this plot. Do the trainings if needed
```
There is many options for the main script, because I use the same code-base for other projects. You can safely ignore most of them, and the different recipe in the makefiles should give you an idea on how to modify the training settings and create new targets. In case of questions, feel free to contact me.

### Data scheme
#### datasets
For instance
```
prostate/
    train/
        cbf/
            Case10_0_0.png
            ...
        cbv/
        gt/
        in_npy/
            Case10_0_0.npy
            ...
        gt_npy/
        ...
    val/
        cbf/
            Case10_0_0.png
            ...
        cbv/
        gt/
        in_npy/
            Case10_0_0.npy
            ...
        gt_npy/
        ...
```
The network takes npy files as an input (there is multiple modalities), but images for each modality are saved for convenience. The gt folder contains gray-scale images of the ground-truth, where the gray-scale level are the number of the class (namely, 0 and 1). This is because I often use my [segmentation viewer](https://github.com/HKervadec/segmentation_viewer) to visualize the results, so that does not really matter. If you want to see it directly in an image viewer, you can either use the remap script, or use imagemagick:
```
mogrify -normalize data/prostate/val/gt/*.png
```

#### results
```
results/
    prostate/
        fs/
            best_epoch/
                val/
                    Case10_0_0.png
                    ...
            iter000/
                val/
            ...
            best.pkl # best model saved
            metrics.csv # metrics over time, csv
            best_epoch.txt # number of the best epoch
            val_dice.npy # log of all the metric over time for each image and class
        box_prior_box_size_neg_size/
            ...
        val_dice.png # Plot over time comparing different methods
        ...
    atlas/
        ...
archives/
    $(REPO)-$(DATE)-$(HASH)-$(HOSTNAME)-prostate.tar.gz
    $(REPO)-$(DATE)-$(HASH)-$(HOSTNAME)-atlas.tar.gz
```

### Cool tricks
Remove all assertions from the code. Usually done after making sure it does not crash for one complete epoch:
```sh
make -f prostate.make <anything really> CFLAGS=-O
```

Use a specific python executable:
```sh
make -f prostate.make <super target> CC=/path/to/the/executable
```

Train for only 5 epochs, with a dummy network, and only 10 images per data loader. Useful for debugging:
```sh
make -f prostate.make <really> NET=Dimwit EPC=5 DEBUG=--debug
```

Rebuild everything even if already exist:
```sh
make -f prostate.make <a> -B
```

Only print the commands that will be run:
```sh
make -f prostate.make <a> -n
```

Create a gif for the predictions over time of a specific patient:
```
cd results/prostate/fs
convert iter*/val/Case14_0_0.png Case14_0_0.gif
mogrify -normalize Case14_0_0.gif
```


## Known issues
Two minor issues (soon to be fixed):
- NegSizeLoss currently sums the wrong probability, so it works when using a negative weight
- `BoxPriorBounds` incorrectly handles rotated boxes, creating segments too loose for rotate boxes (when using data augmentation).