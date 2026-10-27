# Sample input

No NIfTI files are committed. The app expects a skull-stripped T1w (the output of the SynthStrip
and N4 steps). For a quick local run, fetch a raw CC0 T1w from OpenNeuro (ds000117, sub-01) into
`data/input/image/` (gitignored) with:

```sh
sh sample-input/fetch-sample.sh
```

which runs

```sh
aws s3 cp --no-sign-request s3://openneuro.org/ds000117/sub-01/anat/sub-01_T1w.nii.gz data/input/image/
```

A raw (not skull-stripped) image still registers, but the Dice sanity metric in
`transforms/<sub>_registration.json` only means something for a brain-extracted input, since it
compares the warped image's foreground with the template brain mask. Put a label map named
`sub-01_dseg.nii.gz` under `data/input/labels/` to exercise the label path. Then `make run`.
