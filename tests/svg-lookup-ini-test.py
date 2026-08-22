#!/usr/bin/env python3

import argparse
import configparser
import unittest
import sys
from pathlib import Path

path = None
svgdir = None
config = None


class TestSVGLookup(unittest.TestCase):
    def test_has_sections(self):
        self.assertTrue(config.sections())

    def test_required(self):
        for name in config.sections():
            s = config[name]
            self.assertIn("DeviceMatch", s)
            self.assertIn("Svg", s)

    def test_svg_filename(self):
        svgs = [config[s]["Svg"] for s in config.sections()]
        for svg in svgs:
            self.assertTrue(Path(svgdir, svg).exists(), msg=svg)

    def test_uniq_match(self):
        matches = [config[s]["DeviceMatch"] for s in config.sections()]
        d = {}
        for match in matches:
            self.assertNotIn(match, d, msg=f'Duplicate match "{match}"')
            d[match] = True


def setUpModule():
    global config, path

    config = configparser.ConfigParser(strict=True)
    config.optionxform = lambda option: option
    config.read(path)
    assert config.sections()


def main():
    global path, svgdir

    parser = argparse.ArgumentParser(description="Device data-file checker")
    parser.add_argument("file", nargs=1, help="Absolute path to svg-lookup.ini")
    parser.add_argument("svgdir", nargs=1, help="Directory containing svg files")
    args, remainder = parser.parse_known_args()
    path = args.file[0]
    svgdir = args.svgdir[0]
    unittest.main(argv=[sys.argv[0], *remainder])


if __name__ == "__main__":
    main()
