# ANTs 2.6.5 (Apache-2.0), amd64. The image ships no Python, so a small
# Debian python3 is added for the wrapper and the Dice check.
FROM antsx/ants:2.6.5

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-pip \
 && rm -rf /var/lib/apt/lists/* \
 && pip3 install --no-cache-dir --break-system-packages nibabel==5.3.2 numpy==2.2.6 \
 && useradd --uid 1000 --create-home processor

# The MNI152NLin2009cAsym template (1 mm, brain-extracted) and its brain mask,
# baked in from TemplateFlow's public bucket so the container needs no network.
# Checksums pin the files fetched on 2026-10-27 (see THIRD_PARTY.md for the licence).
RUN mkdir -p /opt/templates && chmod 755 /opt/templates
ADD --chmod=0644 --checksum=sha256:97cee2cf7f51388d76d7b3632c8375d688d0fa171e1bede81fcef23726bb3d73 \
    https://templateflow.s3.amazonaws.com/tpl-MNI152NLin2009cAsym/tpl-MNI152NLin2009cAsym_res-01_desc-brain_T1w.nii.gz \
    /opt/templates/tpl-MNI152NLin2009cAsym_res-01_desc-brain_T1w.nii.gz
ADD --chmod=0644 --checksum=sha256:e40bb1816736504d4c25abc243c1c8503df1d308f64c048318aa4b829e09a7ae \
    https://templateflow.s3.amazonaws.com/tpl-MNI152NLin2009cAsym/tpl-MNI152NLin2009cAsym_res-01_desc-brain_mask.nii.gz \
    /opt/templates/tpl-MNI152NLin2009cAsym_res-01_desc-brain_mask.nii.gz
# ADD creates the target folder with a restrictive mode; the app runs as uid 1000.
RUN chmod 755 /opt/templates && chmod 644 /opt/templates/*

WORKDIR /processor
COPY processor/ /processor/processor/
COPY VERSION /processor/VERSION
ENV PYTHONPATH="/processor" \
    PYTHONUNBUFFERED=1 \
    TEMPLATE_DIR=/opt/templates

# The platform runs the container as uid 1000; do the same locally.
USER 1000

ENTRYPOINT ["python3", "-m", "processor.entry"]
