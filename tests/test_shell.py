# Copyright (C) 2024 Mete Balci
#
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import unittest

from pdfsh.shell import ShellNode, ShellTree, Shell

from . import enable_debug_logging

class TestShell(unittest.TestCase):

    def setUp(self):
        enable_debug_logging()
        self.root = ShellNode('root', 'root_obj', None)
        self.c0 = ShellNode('c0', 'c0_obj', self.root)
        self.c1 = ShellNode('c1', 'c1_obj', self.root)
        self.c2 = ShellNode('c2', 'c2_obj', self.root)
        self.c00 = ShellNode('c00', 'c00_obj', self.c0)
        self.c01 = ShellNode('c01', 'c01_obj', self.c0)
        self.tree = ShellTree(self.root)

    def test_setup(self):
        self.assertIsNone(self.root.parent)
        self.assertEqual(self.c0.parent, self.root)
        self.assertEqual(self.c1.parent, self.root)
        self.assertEqual(self.c2.parent, self.root)
        self.assertEqual(self.c00.parent, self.c0)
        self.assertEqual(self.c01.parent, self.c0)
        self.assertEqual(self.tree.root, self.root)
        self.assertEqual(self.tree.current, self.root)

    def test_go_up_down(self):
        self.assertTrue(self.tree.current, self.root)
        self.assertEqual(self.tree.current_path, '/')
        self.assertFalse(self.tree.go_up())

        self.assertTrue(self.tree.go_down(self.c0))
        self.assertTrue(self.tree.current, self.c0)
        self.assertEqual(self.tree.current_path, '/c0')

        self.assertFalse(self.tree.go_down(self.c1))

        self.assertTrue(self.tree.go_down(self.c00))
        self.assertTrue(self.tree.current, self.c00)
        self.assertEqual(self.tree.current_path, '/c0/c00')

        #self.assertTrue(self.tree.go_up())
        #self.assertTrue(self.tree.current, self.c0)
        #self.assertEqual(self.tree.current_path, '/c0')

        #self.assertTrue(self.tree.go_up())
        #self.assertTrue(self.tree.current, self.root)
        #self.assertEqual(self.tree.current_path, '/')
