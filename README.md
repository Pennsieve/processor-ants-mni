# processor-ants-mni

Registers each T1-weighted image to the MNI152NLin2009cAsym template (1 mm, brain-extracted,
from [TemplateFlow](https://www.templateflow.org/)) with
[ANTs](https://github.com/ANTsX/ANTs) 2.6.5 `antsRegistrationSyNQuick.sh`, and carries an
optional label map along into template space. Step 4 of the Clinical Brain MRI workflow: it takes
the skull-stripped, bias-corrected T1w from the N4 step. The template and its brain mask are baked
into the image under `/opt/templates/`, so the container needs no network. The `template` input (Ports, below) can bring the same files instead; `provenance.json` records which copy was used and its sha256.

## Ports

| Port | Kind | Files | Notes |
|---|---|---|---|
| `image` | input, required | `<sub>[_<entities>]_T1w.nii.gz` | one per subject, e.g. `sub-01_desc-n4_T1w.nii.gz`; found in `INPUT_DIR/image/`, else anywhere under `INPUT_DIR` by the `T1w` suffix |
| `labels` | input, optional | `<sub>[_<entities>]_dseg.nii.gz` | matched by subject label (the part before the first `_`); resampled with `GenericLabel` |
| `template` | input, optional | `tpl-MNI152NLin2009cAsym_res-01_desc-brain_T1w.nii.gz`, `tpl-MNI152NLin2009cAsym_res-01_desc-brain_mask.nii.gz` | Pennsieve's reference catalog fills it (a sha256-checked, versioned copy); without it the built-in copy is used. If it's there it must hold both files. Never searched for images |
| `warped` | output | `warped/<sub>_space-MNI152NLin2009cAsym_T1w.nii.gz`, `warped/<sub>_space-MNI152NLin2009cAsym_dseg.nii.gz` (with labels), `warped/provenance.json` | 193 x 229 x 193 voxels, 1 mm |
| `transforms` | output | `transforms/<sub>_from-T1w_to-MNI152NLin2009cAsym_0GenericAffine.mat`, `..._1Warp.nii.gz`, `..._1InverseWarp.nii.gz` (deformable types only), `transforms/<sub>_registration.json` | |

Per subject the app runs

```
antsRegistrationSyNQuick.sh -d 3 -f /opt/templates/tpl-MNI152NLin2009cAsym_res-01_desc-brain_T1w.nii.gz \
  -m <image> -o /tmp/<tmp>/<sub>_ -t TRANSFORM_TYPE -n THREADS -p f
antsApplyTransforms -d 3 -i <labels> -r <template> [-t <1Warp>] -t <0GenericAffine> -n GenericLabel -u <uchar|short|int> \
  -o warped/<sub>_space-MNI152NLin2009cAsym_dseg.nii.gz          # only with a label map
```

and renames the script's `Warped.nii.gz`, `0GenericAffine.mat`, `1Warp.nii.gz` and
`1InverseWarp.nii.gz` to the names above. As a sanity metric it computes the Dice overlap between
the warped image's foreground (voxels > 0, since the input is skull-stripped) and the template brain
mask, and writes `transforms/<sub>_registration.json` with `subject`, `transformType`, `dice`,
`template` and `command`. A skull-stripped T1w that registered well scores around 0.9 or higher;
a raw head image scores lower because its foreground includes the scalp. A subject that fails is
logged and skipped; the run exits 1 only when every subject failed, or when no T1w image was found.

## Parameters

| Parameter | Type | Default | |
|---|---|---|---|
| `TRANSFORM_TYPE` | string | `s` | `s`: rigid + affine + deformable SyN; `b`: rigid + affine + deformable B-spline SyN; `a`: rigid + affine; `r`: rigid only. `a` and `r` write no warp files. |
| `THREADS` | integer | `4` | `ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS` and the script's `-n` |

## Runtime

Container only (`computeTypes: [standard]`): 4 vCPU, 16 GiB, 60 min timeout. SyN (`s`) on a 1 mm
T1w took about 35 s with 4 threads on an arm64 Mac under amd64 emulation (SyNQuick is quick); affine only (`a`) about 15 s. Native amd64 hardware is at least as fast.
The image is `antsx/ants:2.6.5` plus Debian `python3`, NiBabel, NumPy and the two template files
(3.6 MB); it runs as uid 1000.

## Running it locally

```sh
sh sample-input/fetch-sample.sh   # one CC0 T1w from OpenNeuro into data/input/image/
make run                          # builds (linux/amd64) and runs over data/input/, output in data/output/
```

Set `TRANSFORM_TYPE=a` in `dev.env` for a quick affine-only run. On an arm64 Mac the amd64 image
runs under emulation and is many times slower. `make test` runs the wrapper with the local Python
instead (needs ANTs and `nibabel` installed, and `TEMPLATE_DIR` pointing at a folder with the two
template files).

## Citation

- Tustison NJ et al. The ANTsX ecosystem for quantitative biological and medical imaging. Sci Rep 2021;11:9068.
- Avants BB et al. Symmetric diffeomorphic image registration with cross-correlation. Med Image Anal 2008;12:26.
- Fonov V et al. Unbiased average age-appropriate atlases for pediatric studies. NeuroImage 2011;54:313 (MNI152NLin2009cAsym).

See `THIRD_PARTY.md` for licences, including the template's. This repo is Apache-2.0, copyright 2026 Pennsieve.
