import unittest
from pylibbitcoin.client import merkle_tree

class TestMerkleTree(unittest.TestCase):
    def test_empty_transaction_list(self):
        tree = merkle_tree("")
        self.assertTrue(tree.is_root)
        self.assertEqual(tree.height, 0)
        self.assertEqual(tree.depth, 0)

    def test_only_coinbase(self):
        pass

    def test_two_transactions(self):
        pass

    def test_uneven_number_of_transactions(self):
        pass

    def test_two_layer_tree(self):
        pass

    def test_real_world_example(self):
        pass
