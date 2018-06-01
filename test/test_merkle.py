import unittest
import binascii
import hashlib
from anytree import PreOrderIter
from pylibbitcoin.client import merkle_tree, merkle_branch


class TestMerkleTree(unittest.TestCase):
    coinbase_hash = b'00'
    hash_1 = b'01'
    hash_2 = b'02'

    def test_empty_transaction_list(self):
        tree = merkle_tree([])

        self.assertIsNone(tree)

    def test_only_coinbase(self):
        root = merkle_tree([self.coinbase_hash])

        self.assertTrue(root.is_root)
        self.assertEqual(root.height, 0)
        self.assertEqual(root.depth, 0)
        self.assertEqual(root.name, self.coinbase_hash)

    def test_two_transactions(self):
        root = merkle_tree([self.coinbase_hash, self.hash_1])

        all_nodes = list(PreOrderIter(root))
        self.assertEqual(len(all_nodes), 3)
        self.assertEqual(
            root.name,
            hashlib.sha256(
                hashlib.sha256(self.coinbase_hash + self.hash_1).digest()
            ).digest()
        )

    def test_uneven_number_of_transactions(self):
        root = merkle_tree([
            self.coinbase_hash,
            self.hash_1,
            self.hash_2,
        ])

        all_nodes = list(PreOrderIter(root))
        self.assertEqual(len(all_nodes), 7)
        next_to_last, last = root.children[1].children
        self.assertEqual(last.name, next_to_last.name)

    def test_real_world_example(self):
        with open('test/transactions-of-525285-merkle-root-8694fe0d737b26b49bf7fc906b90c19aeadfe37c6082a95968825cbdbc183a94.txt') as f:  # noqa: E501
            hashes = f.readlines()

        hashes = [binascii.unhexlify(hash_.strip())[::-1] for hash_ in hashes]
        root = merkle_tree(hashes)
        self.assertEqual(
            root.name,
            binascii.unhexlify('8694fe0d737b26b49bf7fc906b90c19aeadfe37c6082a95968825cbdbc183a94')[::-1]  # noqa: E501
        )


class TestMerkleBranch(unittest.TestCase):
    tree = merkle_tree([
        b'00',
        b'01',
        b'02',
    ])

    def test_hash_not_found(self):
        branch = merkle_branch(b'deadbeef', self.tree)

        self.assertIsNone(branch)

    def test_hash_found(self):
        branch = merkle_branch(b'01', self.tree)

        self.assertIsNotNone(branch)
