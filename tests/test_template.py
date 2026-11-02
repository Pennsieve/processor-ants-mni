"""The template a run registers to, and that it's never taken for an input
image. Runs without ANTs: nibabel and numpy are stubbed when not installed."""
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

for mod in ("nibabel", "numpy"):
    if importlib.util.find_spec(mod) is None:
        sys.modules[mod] = types.ModuleType(mod)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from processor import bids_names as bn  # noqa: E402
from processor import main as m  # noqa: E402


def write(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


class ResolveTemplate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.input = root / "input"
        self.input.mkdir()
        self.built_in = root / "opt"
        write(self.built_in / m.TEMPLATE_NAME, "built-in")
        write(self.built_in / m.TEMPLATE_MASK_NAME, "built-in mask")
        self._was = m.BUILT_IN_TEMPLATES
        m.BUILT_IN_TEMPLATES = self.built_in

    def tearDown(self):
        m.BUILT_IN_TEMPLATES = self._was
        self.tmp.cleanup()

    def test_no_input_uses_the_built_in_copy(self):
        tpl = m.resolve_template(self.input)
        self.assertEqual(tpl.image, self.built_in / m.TEMPLATE_NAME)
        self.assertEqual(tpl.source, "built into the image")

    def test_the_input_wins_and_is_checksummed(self):
        given = self.input / "template"
        write(given / m.TEMPLATE_NAME, "catalog")
        write(given / m.TEMPLATE_MASK_NAME, "catalog mask")
        tpl = m.resolve_template(self.input)
        self.assertEqual((tpl.image, tpl.mask), (given / m.TEMPLATE_NAME, given / m.TEMPLATE_MASK_NAME))
        self.assertIn("template input", tpl.source)
        self.assertEqual(tpl.sha256()["file"], m.sha256_of(given / m.TEMPLATE_NAME))
        self.assertNotEqual(tpl.sha256()["file"], m.sha256_of(self.built_in / m.TEMPLATE_NAME))

    def test_an_incomplete_input_is_an_error_not_a_fallback(self):
        write(self.input / "template" / m.TEMPLATE_NAME)
        with self.assertRaises(ValueError) as e:
            m.resolve_template(self.input)
        self.assertIn(m.TEMPLATE_MASK_NAME, str(e.exception))

    def test_a_symlinked_template_is_followed(self):
        given = self.input / "template"
        given.mkdir()
        os.symlink(self.built_in / m.TEMPLATE_NAME, given / m.TEMPLATE_NAME)
        os.symlink(self.built_in / m.TEMPLATE_MASK_NAME, given / m.TEMPLATE_MASK_NAME)
        self.assertEqual(m.resolve_template(self.input).image, given / m.TEMPLATE_NAME)


class FlatInputs(unittest.TestCase):
    # Without INPUT_DIR/image/, images are searched in all of INPUT_DIR: the
    # template's own T1w must not become a subject.
    def test_the_template_is_not_an_image(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root / "sub-01_desc-n4_T1w.nii.gz")
            write(root / "template" / m.TEMPLATE_NAME)
            found = bn.find_input_files(root, "image", ["T1w"], exclude=[m.TEMPLATE_INPUT])
            self.assertEqual([p.name for p in found], ["sub-01_desc-n4_T1w.nii.gz"])
            # Its own folder, when there is one, is searched as before.
            write(root / "image" / "sub-02_T1w.nii.gz")
            found = bn.find_input_files(root, "image", ["T1w"], exclude=[m.TEMPLATE_INPUT])
            self.assertEqual([p.name for p in found], ["sub-02_T1w.nii.gz"])


if __name__ == "__main__":
    unittest.main()
