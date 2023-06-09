#!/usr/bin/env python3.7


import os
import random
import argparse
import shutil
import warnings
from pathlib import Path
from functools import partial
from typing import Callable, List, Tuple
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import nibabel as nib
from skimage.io import imsave
from numpy import unique as uniq, ndarray

from utils import map_, mmap_, center_pad, augment


def norm_arr(img: np.ndarray) -> np.ndarray:
    casted = img.astype(np.float32)
    shifted = casted - casted.min()
    norm = shifted / shifted.max()
    res = 255 * norm

    assert 0 == res.min(), res.min()
    assert res.max() == 255, res.max()

    return res.astype(np.uint8)


def fuse_labels(t1: np.ndarray, id_: str, acq: Path, nib_obj, cycl: bool = False, lab_sufix: str = "") -> tuple[
    ndarray, ndarray]:
    gt: np.ndarray = np.zeros_like(t1, dtype=np.uint8)
    gt1: np.ndarray = np.zeros_like(t1, dtype=np.uint8)
    assert gt.dtype == np.uint8
    acq_ = acq.parent
    labels: List[Path] = list(acq_.glob(f"{id_}{lab_sufix}.nii.gz"))
    assert len(labels) >= 1, (acq, id_)
    # except:
    # pass
    label_path: Path
    label: np.ndarray
    for label_path in labels:
        label_obj = nib.load(str(label_path))
        label = np.asarray(label_obj.dataobj, dtype=np.float64)

        assert sanity_label(label, t1, label_obj.header.get_zooms(), nib_obj.header.get_zooms(), label_path)

        binary_label: np.ndarray = (label > 0).astype(np.uint8)
        binary_label1: np.ndarray = (label > 1).astype(np.uint8)
        assert binary_label.dtype == np.uint8, binary_label.dtype
        assert set(uniq(binary_label)) <= {0, 1}

        gt |= binary_label  # logical OR if labels overlap
        gt1 |= binary_label1  # logical OR if labels overlap
        # gt += binary_label
    assert set(uniq(gt)) <= {0, 1}
    assert gt.dtype == np.uint8

    return gt, gt1


def sanity_t1(t1, x, y, z, dx, dy, dz) -> bool:
    assert t1.dtype in [np.float32], t1.dtype
    assert -0.0003 <= t1.min(), t1.min()
    assert t1.max() <= 100.0001, t1.max()

    assert 1 <= dx <= 1, dx
    assert dy <= 1, dy
    assert 1 <= dz <= 1, dz

    assert x != y, (x, y)
    assert x != z or y != z, (x, y, z)
    assert x in [230], x
    assert y in [225, 240], y
    assert z in [230], z

    return True


def sanity_label(label, t1, resolution, t1_resolution, label_path) -> bool:
    # assert False
    assert label.shape == t1.shape
    assert resolution == t1_resolution

    assert label.dtype in [np.float64], label.dtype
    labels_allowed = [[0.0, 0.9999999997671694],
                      [0., 254.9999999406282],
                      [0., 0.9999999997671694, 253.99999994086102, 254.9999999406282],
                      [0.0, 0.9999999997671694, 1.9999999995343387, 252.99999994109385, 253.99999994086102,
                       254.9999999406282]]

    # assert set(uniq(label)) in set(labels_allowed), (set(uniq(label)), label_path)
    matches: List[bool] = [set(uniq(label)) == set(allowed) for allowed in labels_allowed]
    # assert any(matches), (set(uniq(label)), label_path)

    return True


def slice_patient(id_: str, dest_path: Path, source_path: Path, shape: Tuple[int, int],
                  n_augment: int, cycl: bool = True, img_sufix: str = '', lab_sufix: str = '_manual'
                  ):
    id_path: Path = Path(source_path, id_)
    acq: Path = Path(id_path, f"{id_}.nii.gz")
    t1_path: Path = acq  # Path(acq, f"")
    nib_obj = nib.load(str(t1_path))
    t1: np.ndarray = np.asarray(nib_obj.dataobj, dtype=np.float32)
    if t1.max() > 100:
        cc0 = t1.max() / 100
        t1 = t1 // cc0
    # print("t1 shape ",t1.shape)
    x, y, z = t1.shape

    # print("args", *t1.shape, "zoom",*nib_obj.header.get_zooms())
    # assert sanity_t1(t1, *t1.shape, *nib_obj.header.get_zooms())
    # try:
    # assert sanity_t1(t1, *t1.shape, *nib_obj.header.get_zooms())
    # except:
    # print("SSSSSSSSSSSSSSSS")
    # continue
    # gt: np.ndarray = fuse_labels(t1, id_, acq, nib_obj)
    gt, gt1 = fuse_labels(t1, id_, acq, nib_obj, cycl=cycl, lab_sufix=lab_sufix)

    norm_img: np.ndarray = norm_arr(t1)

    for idz in range(z):
        # try:
        padded_img: np.ndarray = center_pad(norm_img[:, :, idz], shape)
        padded_gt: np.ndarray = center_pad(gt[:, :, idz], shape)
        padded_gt1: np.ndarray = center_pad(gt1[:, :, idz], shape)
        assert padded_img.shape == padded_gt.shape == shape
        # except:
        # continue
        for k in range(n_augment + 1):
            arrays: List[np.ndarray] = [padded_img, padded_gt, padded_gt1]

            augmented_arrays: List[np.ndarray]
            if k == 0:
                augmented_arrays = arrays[:]
            else:
                augmented_arrays = map_(np.asarray, augment(*arrays))

            subfolders: List[str] = ["img", "gt", "gt1"]
            assert len(augmented_arrays) == len(subfolders)
            for save_subfolder, data in zip(subfolders,
                                            augmented_arrays):
                filename = f"{id_}_{idz}_{k}.png"

                save_path: Path = Path(dest_path, save_subfolder)
                save_path.mkdir(parents=True, exist_ok=True)

                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=UserWarning)
                    imsave(str(Path(save_path, filename)), data)


def get_splits(id_list: str, retains: int, fold: int) -> Tuple[List[str], List[str]]:
    id_file: Path = Path(id_list)

    ids: List[str]
    with open(id_file, 'r') as f:
        ids = f.read().split()

    print(f"Founds {len(ids)} in the id list")
    assert len(ids) > retains

    random.shuffle(ids)  # Shuffle before to avoid any problem if the patients are sorted in any way
    validation_slice = slice(fold * retains, (fold + 1) * retains)
    validation_ids: List[str] = ids[validation_slice]
    assert len(validation_ids) == retains

    training_ids: List[str] = [e for e in ids if e not in validation_ids]
    assert (len(training_ids) + len(validation_ids)) == len(ids)

    return training_ids, validation_ids


def main(args: argparse.Namespace):
    src_path: Path = Path(args.source_dir)
    dest_path: Path = Path(args.dest_dir)

    # Assume the cleaning up is done before calling the script
    assert src_path.exists()
    if dest_path.exists():
        shutil.rmtree(dest_path)

    training_ids: List[str]
    validation_ids: List[str]
    training_ids, validation_ids = get_splits(args.id_list, args.retains, args.fold)

    split_ids: List[str]
    for mode, split_ids in zip(["train", "val"], [training_ids, validation_ids]):
        dest_mode: Path = Path(dest_path, mode)
        print(f"Slicing {len(split_ids)} pairs to {dest_mode}")

        # pfun: Callable = partial(slice_patient,
        #                          dest_path=dest_mode,
        #                          source_path=src_path,
        #                          shape=tuple(args.shape),
        #                          n_augment=args.n_augment if mode == "train" else 0)
        # mmap_(pfun, split_ids)
        # mmap_.
        # with ProcessPoolExecutor() as executor:
        #     executor.map(pfun, split_ids)
        #     print(executor._mp_context)

        # executor
        for i in split_ids:
            slice_patient(i,
                          dest_path=dest_mode,
                          source_path=src_path,
                          shape=tuple(args.shape),
                          n_augment=args.n_augment if mode == "train" else 0,
                          cycl=args.cycl,
                          img_sufix=args.img_sufix,
                          lab_sufix=args.lab_sufix
                          )
        #     break


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Slicing parameters')
    parser.add_argument('--source_dir', type=str, required=True)
    parser.add_argument('--dest_dir', type=str, required=True)
    parser.add_argument('--id_list', type=str, required=True)

    # parser.add_argument('--img_dir', type=str, default="IMG")
    # parser.add_argument('--gt_dir', type=str, default="GT")
    parser.add_argument('--shape', type=int, nargs="+", default=[256, 256])
    parser.add_argument('--retains', type=int, default=2, help="Number of retained patient for the validation data")
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--fold', type=int, default=0)
    parser.add_argument("--cycl", type=bool, default=True)
    parser.add_argument("--img_sufix", type=str, default='')
    parser.add_argument("--lab_sufix", type=str, default='_manual')

    parser.add_argument('--n_augment', type=int, default=0,
                        help="Number of augmentation to create per image, only for the training set")
    args = parser.parse_args()
    random.seed(args.seed)

    print(args)
    # args.cycl=True
    return args


if __name__ == "__main__":
    # global args
    args = get_args()
    main(args)
