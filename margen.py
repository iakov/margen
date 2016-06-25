#!/usr/bin/python2
"""
   Copyright 2016 Iakov Kirilenko

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.


   Simple generator for colorful AR tags
"""
import argparse
import errno
import numpy as np
import os

import cv2 as cv


def generate_palette(s):
    maxDarkLuma = 120
    n = int(s)
    if n == 0:
        return lambda _: (0, 0, 0)
    elif n == 1:
        colors = [(maxDarkLuma*9/10, 0, 0), (0, maxDarkLuma * 7 / 10, 0), (0, 0, maxDarkLuma)]
        return lambda (row, col): colors[(row + col) % len(colors)]
    else:
        raise argparse.ArgumentTypeError("palette %r not implemented" % s)


def parse_args():
    parser = argparse.ArgumentParser(description='AR marker tag generator')
    parser.add_argument('codes', metavar='N[..M]', nargs='+', help='integer code N or range N..M')
    parser.add_argument('--force', dest='force', action='store_true',
                        help='ignore checks & errors (depends on context)')
    parser.add_argument('--out-dir', dest='dir', default='.', help='output directory name')
    parser.add_argument('--palette', dest='palette', metavar='P', type=generate_palette, default=generate_palette("0"),
                        help='use palette #P ( 0 -- b/w) ')
    parser.add_argument('--box-size', dest='boxSize', type=int, default=50, help='bit box size per side in pixels')
    return parser.parse_args()


class Generator:
    def draw_box(self, pos, color=None):
        if color is None:
            color = self.args.palette(pos)
        row, col = pos
        top_left = ((col + 1) * self.args.boxSize, (row + 1) * self.args.boxSize)
        down_right = ((col + 2) * self.args.boxSize - 1, (row + 2) * self.args.boxSize - 1)
        points = np.array([top_left, (down_right[0], top_left[1]), down_right, (top_left[0], down_right[1])])
        cv.fillConvexPoly(self.img, points, color)

    def generate(self, code):
        freeBits = (6 - 2) * (6 - 2) - 3
        if code < 0 or code >= 1 << freeBits:
            return None

        binCode = bin(code)[2:].zfill(freeBits)
        binCode = '1' + binCode[0:11] + '1' + binCode[11:] + '0'

        """Check message (for parity, etc.)"""
        if binCode[3] == '1' or binCode[8] == '1' or binCode.count('1') % 2 != 0:
            if not self.args.force:
                return None

        """Draw border"""
        for i in range(0, 6):
            for pos in [(0, i), (5, i), (i, 0), (i, 5)]:
                self.draw_box(pos)

        """Draw message"""
        for i in range(0, len(binCode)):
            pos = (i / 4 + 1, i % 4 + 1)
            self.draw_box(pos, None if binCode[i] == '1' else (255, 255, 255))

        return self.img

    def __init__(self, args):
        self.img = cv.bitwise_not(np.zeros(((6 + 2) * args.boxSize, (6 + 2) * args.boxSize, 3), np.uint8))
        self.args = args


def main():
    args = parse_args()
    try:
        os.makedirs(args.dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    g = Generator(args)
    for code in [z for y in [x.split("..") for x in args.codes]
                 for z in range(int(y[0]), 1 + int(y[0] if len(y) == 1 else y[1]))]:

        marker = g.generate(code)
        if marker is None: continue
        filename = args.dir + '/{0:04}.png'.format(code)
        cv.cvtColor(marker, cv.COLOR_RGB2BGR565, marker)
        cv.imwrite(filename, marker, [cv.IMWRITE_PNG_COMPRESSION, 9])


if __name__ == "__main__":
    main()
