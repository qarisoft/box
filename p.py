import nibabel as nib
import os,shutil
from pathlib import Path
cycl = "data/cy"
p = "data/n"

os.makedirs(p,exist_ok=True)
ids=[]
for id in Path(p).glob("R*"):
        ids.append(id.name)

if Path("data/uniq_ids").exists():
    r=open("data/uniq_ids","w")
    r.close()
with open("data/uniq_ids","a")as f:
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
    
    