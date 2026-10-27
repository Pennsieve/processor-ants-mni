# Third-party software and data

## ANTs (Advanced Normalization Tools) 2.6.5

- Base image: `antsx/ants:2.6.5` (linux/amd64, Debian 12), https://hub.docker.com/r/antsx/ants
- Source: https://github.com/ANTsX/ANTs
- Licence: Apache License 2.0
- Tools used: `antsRegistrationSyNQuick.sh` (which drives `antsRegistration`), `antsApplyTransforms`
- Citations:
  - Tustison NJ, Cook PA, Holbrook AJ, et al. The ANTsX ecosystem for quantitative biological and medical
    imaging. Sci Rep. 2021;11:9068. https://doi.org/10.1038/s41598-021-87564-6
  - Avants BB, Epstein CL, Grossman M, Gee JC. Symmetric diffeomorphic image registration with
    cross-correlation: evaluating automated labeling of elderly and neurodegenerative brain. Med Image Anal.
    2008;12(1):26-41. https://doi.org/10.1016/j.media.2007.06.004

## MNI152NLin2009cAsym template (baked into the image under /opt/templates/)

ICBM 152 Nonlinear Asymmetrical template version 2009c, 1 mm, brain-extracted T1w and brain mask,
as distributed by TemplateFlow (RRID:SCR_008796):

- `tpl-MNI152NLin2009cAsym_res-01_desc-brain_T1w.nii.gz`
  (sha256 97cee2cf7f51388d76d7b3632c8375d688d0fa171e1bede81fcef23726bb3d73)
- `tpl-MNI152NLin2009cAsym_res-01_desc-brain_mask.nii.gz`
  (sha256 e40bb1816736504d4c25abc243c1c8503df1d308f64c048318aa4b829e09a7ae)
- Source: https://templateflow.s3.amazonaws.com/tpl-MNI152NLin2009cAsym/ (public, no credentials),
  https://github.com/templateflow/tpl-MNI152NLin2009cAsym
- Citations:
  - Fonov V, Evans AC, Botteron K, Almli CR, McKinstry RC, Collins DL. Unbiased average age-appropriate
    atlases for pediatric studies. NeuroImage. 2011;54(1):313-327. https://doi.org/10.1016/j.neuroimage.2010.07.033
  - Fonov V, Evans A, McKinstry R, Almli C, Collins D. Unbiased nonlinear average age-appropriate brain
    templates from birth to adulthood. NeuroImage. 2009;47(Suppl 1):S102. https://doi.org/10.1016/S1053-8119(09)70884-5
  - Ciric R, et al. TemplateFlow: FAIR-sharing of multi-scale, multi-species brain models. Nat Methods.
    2022;19:1568-1571. https://doi.org/10.1038/s41592-022-01681-2

Licence (from the template's LICENSE file):

> Copyright (C) 1993-2004 Louis Collins, McConnell Brain Imaging Centre, Montreal Neurological Institute,
> McGill University. Permission to use, copy, modify, and distribute this software and its documentation
> for any purpose and without fee is hereby granted, provided that the above copyright notice appear in
> all copies. The authors and McGill University make no representations about the suitability of this
> software for any purpose. It is provided "as is" without express or implied warranty. The authors are
> not responsible for any data loss, equipment damage, property loss, or injury to subjects or patients
> resulting from the use or misuse of this software package.

## Python packages (installed in the image)

- NiBabel 5.3.2, MIT licence, https://nipy.org/nibabel/
- NumPy 2.2.6, BSD-3-Clause licence, https://numpy.org/
- Debian `python3` 3.11 and `python3-pip`, PSF licence
