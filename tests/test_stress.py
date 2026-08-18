import unittest
from scripts.stress import run
class Stress(unittest.TestCase):
 def test_10k(self):self.assertEqual(run(10000,1000)['status'],'PASS')
