import unittest
from endpoint import response


class EndpointTest(unittest.TestCase):
    def test_response(self):
        self.assertEqual(response(" ok "), {"name": "ok"})
