import nibabel as nib
import os,shutil
from pathlib import Path
cycl = "data/cy"
p = "data/cycl"

os.makedirs(cycl,exist_ok=True)
ids=[]
for nii in Path(p,"images").glob("*"):
    # for nii in i.glob("*"):
        ngz = nii.name.split(".nii.gz")[0]
        ids.append(ngz)
        # with
        lb_ngz = Path(p,f"labels/{ngz}_scribble.nii.gz")
        cycl_p=f"data/cy/{ngz}"
        os.makedirs(cycl_p,exist_ok=True)
        shutil.copy2(nii,cycl_p)
        shutil.copy2(lb_ngz,cycl_p)
        # print(nii)
        # print(lb_ngz)
with open("data/uniq_ids_cycl","a")as f:
    for x,i in enumerate(ids):
        n="" if x>=len(ids)-1 else "\n"
        f.write(f"{i}{n}")

# f="data\subject1_DE.nii.gz"
# data = nib.load(f).get_fdata()
# print(data.shape)
# for i in range(data.shape[2]):
#     img = data[:,:,i]
#     print(img.shape,"  ",img.max())
#     c = img.max()/100
#     img = img //c
#     print(img.shape," > ",img.max())
    
    