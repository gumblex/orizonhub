#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pickle
import collections


class TextBlock:

    def __init__(self, block='', blank=' '):
        self.lines = []
        self.blank = blank
        for l in block.splitlines():
            self.lines.append(l)
        if not self.lines:
            self.lines.append('')
        self.width = max(map(len, self.lines))
        self.height = len(self.lines)
        self.lines = collections.deque(l.ljust(self.width) for l in self.lines)

    def hcat(self, other, justify=0):
        delta = other.height - self.height
        start = 0
        if delta > 0:
            if justify > 0:
                self.lines.extendleft(
                    self.blank * self.width for i in range(delta))
            elif justify < 0:
                self.lines.extend(
                    self.blank * self.width for i in range(delta))
            else:
                top = delta // 2
                self.lines.extendleft(
                    self.blank * self.width for i in range(top))
                self.lines.extend(
                    self.blank * self.width for i in range(delta - top))
            self.height = other.height
        elif delta < 0:
            if justify > 0:
                start = -delta
            elif justify == 0:
                start = -delta // 2
        for ln in range(start):
            self.lines[ln] += self.blank * other.width
        for ln in range(other.height):
            self.lines[ln + start] += other.lines[ln]
        for ln in range(start + other.height, self.height):
            self.lines[ln] += self.blank * other.width
        self.width += other.width

    def __str__(self):
        return '\n'.join(self.lines)


class BlockGenerator:

    def __init__(self, fontfile, fillchar=' █'):
        self.font = pickle.load(open(fontfile, 'rb'))
        self.fillchar = fillchar

    def renderchar(self, c):
        try:
            lines = []
            g = self.font[ord(c)]
            width = g[0]
            for l in g[1:]:
                s = ''.join(self.fillchar[int(b)]
                            for b in bin(l)[2:].zfill(width))
                lines.append(s)
            return '\n'.join(lines)
        except Exception:
            return ''

    def render(self, s):
        lines = []
        for ln in s.splitlines():
            blk = TextBlock(blank=self.fillchar[0])
            start = 0
            for c in ln:
                if start:
                    blk.hcat(
                        TextBlock(self.fillchar[0], blank=self.fillchar[0]), 1)
                else:
                    start = 1
                blk.hcat(
                    TextBlock(self.renderchar(c), blank=self.fillchar[0]), 1)
            lines.append(str(blk))
        return '\n'.join(lines)

if __name__ == '__main__':
    import sys
    bg = BlockGenerator(*sys.argv[1:])
    print(bg.render(sys.stdin.read()))
