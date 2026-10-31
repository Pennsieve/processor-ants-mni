#!/bin/sh
# Fetches one CC0 T1w image from OpenNeuro (ds000117) into data/input/image/ for a local run.
set -eu
cd "$(dirname "$0")/.."
mkdir -p data/input/image
aws s3 cp --no-sign-request s3://openneuro.org/ds000117/sub-01/ses-mri/anat/sub-01_ses-mri_T1w.nii.gz data/input/image/sub-01_T1w.nii.gz
ls -la data/input/image
