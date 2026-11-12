import unittest
from adapter import normalize


class AdapterTest(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize(" ok ", strict=True), "ok")
