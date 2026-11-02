"""
ANTs registration of each T1w image to MNI152NLin2009cAsym (1 mm, brain-extracted).

Inputs (INPUT_DIR/<name>/ when linked, else found anywhere under INPUT_DIR
by BIDS suffix):
  image   <sub>[_<entities>]_T1w.nii.gz   required
  labels  <sub>[_<entities>]_dseg.nii.gz  optional, matched by subject label

Outputs:
  OUTPUT_DIR/warped/<sub>_space-MNI152NLin2009cAsym_T1w.nii.gz   (+ _dseg.nii.gz, provenance.json)
  OUTPUT_DIR/transforms/<sub>_from-T1w_to-MNI152NLin2009cAsym_0GenericAffine.mat
  OUTPUT_DIR/transforms/<sub>_from-T1w_to-MNI152NLin2009cAsym_1Warp.nii.gz        (s, b only)
  OUTPUT_DIR/transforms/<sub>_from-T1w_to-MNI152NLin2009cAsym_1InverseWarp.nii.gz (s, b only)
  OUTPUT_DIR/transforms/<sub>_registration.json
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import nibabel as nib
import numpy as np

from processor import bids_names as bn

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("processor-ants-mni")

APP = "processor-ants-mni"
TOOL = "antsRegistrationSyNQuick.sh"
OUTPUTS = ["warped", "transforms"]
SPACE = "MNI152NLin2009cAsym"
TEMPLATE_NAME = f"tpl-{SPACE}_res-01_desc-brain_T1w.nii.gz"
TEMPLATE_MASK_NAME = f"tpl-{SPACE}_res-01_desc-brain_mask.nii.gz"
# The copy baked into the image; a run's template input replaces it.
TEMPLATE_DIR = Path(os.environ.get("TEMPLATE_DIR", "/opt/templates"))
TEMPLATE = TEMPLATE_DIR / TEMPLATE_NAME
TEMPLATE_MASK = TEMPLATE_DIR / TEMPLATE_MASK_NAME
TEMPLATE_SOURCE = "https://templateflow.s3.amazonaws.com/tpl-MNI152NLin2009cAsym/ (built into the image)"


def use_template_input(input_dir: Path) -> None:
    """Use the template input (INPUT_DIR/template/, from Pennsieve's reference
    catalog or put there by hand) when it holds both TemplateFlow files, in
    place of the built-in copy."""
    global TEMPLATE_DIR, TEMPLATE, TEMPLATE_MASK, TEMPLATE_SOURCE
    given = input_dir / "template"
    if (given / TEMPLATE_NAME).is_file() and (given / TEMPLATE_MASK_NAME).is_file():
        TEMPLATE_DIR, TEMPLATE, TEMPLATE_MASK = given, given / TEMPLATE_NAME, given / TEMPLATE_MASK_NAME
        TEMPLATE_SOURCE = "the template input (INPUT_DIR/template)"
    elif given.is_dir():
        log.warning("INPUT_DIR/template doesn't hold %s and %s; using the built-in template",
                    TEMPLATE_NAME, TEMPLATE_MASK_NAME)
TRANSFORM_TYPES = ("s", "a", "r", "b")
DEFORMABLE = ("s", "b")
DEFAULTS = {"TRANSFORM_TYPE": "s", "THREADS": "4"}


def app_version() -> str:
    for candidate in (Path(__file__).resolve().parent.parent / "VERSION", Path("/processor/VERSION")):
        if candidate.is_file():
            return candidate.read_text().strip()
    return "unknown"


def tool_version() -> str:
    try:
        out = subprocess.run(["antsRegistration", "--version"], check=True, capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        log.warning("could not read the ANTs version: %s", exc)
        return "unknown"
    for line in out.splitlines():
        if "Version" in line:
            return line.split(":", 1)[-1].strip()
    return out.strip().splitlines()[0] if out.strip() else "unknown"


def read_params() -> dict:
    raw = {k: os.environ.get(k, v).strip() or v for k, v in DEFAULTS.items()}
    if raw["TRANSFORM_TYPE"] not in TRANSFORM_TYPES:
        raise ValueError(f"TRANSFORM_TYPE must be one of {', '.join(TRANSFORM_TYPES)}, got {raw['TRANSFORM_TYPE']!r}")
    threads = int(raw["THREADS"])
    if threads < 1:
        raise ValueError(f"THREADS must be >= 1, got {threads}")
    return {"TRANSFORM_TYPE": raw["TRANSFORM_TYPE"], "THREADS": threads}


def run(cmd: list[str], sub: str) -> None:
    log.info("[%s] %s", sub, " ".join(cmd))
    subprocess.run(cmd, check=True)


def dice(a: np.ndarray, b: np.ndarray) -> float:
    inter = np.count_nonzero(a & b)
    total = np.count_nonzero(a) + np.count_nonzero(b)
    return 2.0 * inter / total if total else 0.0


def label_output_type(labels: Path) -> str:
    """The smallest integer type antsApplyTransforms can write (-u) that holds every label."""
    top = float(np.asarray(nib.load(str(labels)).dataobj).max())
    if top <= 255:
        return "uchar"
    if top <= 32767:
        return "short"
    return "int"


def registration_dice(warped: Path) -> tuple[float, dict]:
    """Dice between the warped image's foreground (> 0; the input is skull-stripped) and the template brain mask."""
    w = nib.load(str(warped))
    m = nib.load(str(TEMPLATE_MASK))
    if w.shape != m.shape:
        raise RuntimeError(f"warped image shape {w.shape} differs from the template's {m.shape}")
    fg = np.asarray(w.dataobj) > 0
    mask = np.asarray(m.dataobj) > 0
    return dice(fg, mask), {"foregroundVoxels": int(fg.sum()), "templateMaskVoxels": int(mask.sum())}


def process_subject(sub: str, image: Path, labels: Path | None, out_warped: Path, out_tf: Path,
                    params: dict, input_dir: Path, output_dir: Path) -> dict:
    ttype = params["TRANSFORM_TYPE"]
    t0 = time.monotonic()
    tmp = Path(tempfile.mkdtemp(prefix=f"{sub}_", dir="/tmp"))
    try:
        prefix = tmp / f"{sub}_"
        cmd = [TOOL, "-d", "3", "-f", str(TEMPLATE), "-m", str(image), "-o", str(prefix),
               "-t", ttype, "-n", str(params["THREADS"]), "-p", "f"]
        run(cmd, sub)

        produced = {
            "Warped.nii.gz": out_warped / bn.derived_name(image, "T1w", space=SPACE),
            "0GenericAffine.mat": out_tf / f"{sub}_from-T1w_to-{SPACE}_0GenericAffine.mat",
        }
        if ttype in DEFORMABLE:
            produced["1Warp.nii.gz"] = out_tf / f"{sub}_from-T1w_to-{SPACE}_1Warp.nii.gz"
            produced["1InverseWarp.nii.gz"] = out_tf / f"{sub}_from-T1w_to-{SPACE}_1InverseWarp.nii.gz"
        outputs = []
        for tail, dest in produced.items():
            src = Path(str(prefix) + tail)
            if not src.is_file() or src.stat().st_size == 0:
                raise RuntimeError(f"{TOOL} exited 0 but did not write {src.name}")
            shutil.move(str(src), str(dest))
            outputs.append(str(dest.relative_to(output_dir)))
        warped = produced["Warped.nii.gz"]

        commands = [cmd]
        inputs = [str(image.relative_to(input_dir))]
        if labels is not None:
            warped_labels = out_warped / bn.derived_name(labels, "dseg", space=SPACE)
            transforms = []
            if ttype in DEFORMABLE:
                transforms += ["-t", str(produced["1Warp.nii.gz"])]
            transforms += ["-t", str(produced["0GenericAffine.mat"])]
            apply_cmd = ["antsApplyTransforms", "-d", "3", "-i", str(labels), "-r", str(TEMPLATE),
                         *transforms, "-n", "GenericLabel", "-u", label_output_type(labels),
                         "-o", str(warped_labels)]
            run(apply_cmd, sub)
            if not warped_labels.is_file():
                raise RuntimeError(f"antsApplyTransforms exited 0 but did not write {warped_labels.name}")
            commands.append(apply_cmd)
            inputs.append(str(labels.relative_to(input_dir)))
            outputs.append(str(warped_labels.relative_to(output_dir)))

        score, counts = registration_dice(warped)
        seconds = round(time.monotonic() - t0, 1)
        report = {
            "subject": sub,
            "transformType": ttype,
            "dice": round(score, 4),
            **counts,
            "template": TEMPLATE.name,
            "templateSpace": SPACE,
            "command": cmd,
            "seconds": seconds,
        }
        report_path = out_tf / f"{sub}_registration.json"
        with open(report_path, "w") as fh:
            json.dump(report, fh, indent=2)
        outputs.append(str(report_path.relative_to(output_dir)))
        log.info("[%s] done in %ss; transform %s; Dice(foreground, template brain mask) = %.4f",
                 sub, seconds, ttype, score)
        return {"subject": sub, "inputs": inputs, "outputs": outputs, "command": cmd,
                "commands": commands, "seconds": seconds, "dice": round(score, 4)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    started = datetime.now(timezone.utc)
    input_dir = os.environ.get("INPUT_DIR")
    output_dir = os.environ.get("OUTPUT_DIR")
    if not input_dir or not output_dir:
        log.error("INPUT_DIR and OUTPUT_DIR must be set")
        return 2
    input_dir, output_dir = Path(input_dir), Path(output_dir)
    if not input_dir.is_dir():
        log.error("INPUT_DIR %s is not a folder", input_dir)
        return 2
    try:
        params = read_params()
    except ValueError as exc:
        log.error("bad parameter: %s", exc)
        return 2
    use_template_input(input_dir)
    for f in (TEMPLATE, TEMPLATE_MASK):
        try:
            readable = f.is_file() and os.access(f, os.R_OK)
        except OSError:
            readable = False
        if not readable:
            log.error("template file %s is missing or not readable", f)
            return 2
    os.environ["ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS"] = str(params["THREADS"])
    log.info("%s %s, ANTs %s, parameters %s, template %s (from %s)", APP, app_version(), tool_version(), params,
             TEMPLATE, TEMPLATE_SOURCE)

    out_warped = bn.output_dir_for(output_dir, OUTPUTS, "warped")
    out_tf = bn.output_dir_for(output_dir, OUTPUTS, "transforms")

    images = bn.by_subject(bn.find_input_files(input_dir, "image", ["T1w"]))
    labels = bn.by_subject(bn.find_input_files(input_dir, "labels", ["dseg"]))
    if not images:
        found = sorted(str(p.relative_to(input_dir)) for p in input_dir.rglob("*") if p.is_file())
        log.error("no T1w image (*_T1w.nii[.gz]) found under %s; files present: %s",
                  input_dir, ", ".join(found) or "(none)")
        return 1
    log.info("%d subject(s): %s; label maps for: %s", len(images), ", ".join(sorted(images)),
             ", ".join(sorted(labels)) or "(none)")
    for sub in sorted(labels):
        if sub not in images:
            log.warning("label map for %s has no matching image; ignored", sub)

    subjects, failures = [], []
    for sub in sorted(images):
        image, lab = images[sub], labels.get(sub)
        if lab is None and labels:
            log.warning("[%s] no label map for this subject", sub)
        try:
            subjects.append(process_subject(sub, image, lab, out_warped, out_tf, params, input_dir, output_dir))
        except (subprocess.CalledProcessError, RuntimeError, OSError, ValueError) as exc:
            log.error("[%s] failed: %s", sub, exc)
            failures.append({"subject": sub, "inputs": [str(image.relative_to(input_dir))], "error": str(exc)})

    provenance = {
        "app": APP,
        "appVersion": app_version(),
        "tool": TOOL,
        "toolVersion": tool_version(),
        "template": {"space": SPACE, "resolution": "01", "file": TEMPLATE.name, "mask": TEMPLATE_MASK.name,
                     "source": TEMPLATE_SOURCE},
        "startedAt": started.isoformat(),
        "finishedAt": datetime.now(timezone.utc).isoformat(),
        "parameters": params,
        "subjects": subjects,
        "failures": failures,
    }
    with open(out_warped / "provenance.json", "w") as fh:
        json.dump(provenance, fh, indent=2)

    log.info("%d of %d subject(s) registered", len(subjects), len(images))
    if not subjects:
        log.error("every subject failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
