import unittest
from pylibbitcoin.client import checksum


class TestChecksum(unittest.TestCase):
    """
    The variable `hash` has the format 12 discarded bytes + 8 relevant bytes +
    12 discared bytes.
    Only the first 49 bits in the 8 relevant bytes are really relevant the
    remainder is overwritten by the index.
    """

    def test_all_ones(self):
        hash = 'ffffffffffffffffffffffff' + \
            'ffffffffffffffff' + \
            'ffffffffffffffffffffffff'
        index = int('ffffffff', 16)
        self.assertEqual(checksum(hash, index), 0xffffffffffffffff)

    def test_all_zeros(self):
        hash = '000000000000000000000000' + \
            '0000000000000000' + \
            '000000000000000000000000'
        index = int('00000000', 16)
        self.assertEqual(checksum(hash, index), 0)

    def test_drop_high(self):
        hash = 'ffffffffffffffffffffffff' + \
             'aaaaaaaaaaaaaaaa' + \
             '000000000000000000000000'
        index = 0
        self.assertEqual(checksum(hash, index), 0xaaaaaaaaaaaa8000)

        hash = 'ffffffffffffffffffffffff' + \
            'aaaaaaaaaaaaaaaa' + \
            '000000000000000000000000'
        self.assertEqual(checksum(hash, index), 0xaaaaaaaaaaaa8000)

    def test_index(self):
        hash = 'ffffffffffffffffffffffff' + \
             'aaaaaaaaaaaaaaaa000000000000000000000000'
        index = 1
        self.assertEqual(checksum(hash, index), 0xaaaaaaaaaaaa8001)

    def test_index_higher_than_15_bits(self):
        hash = '000000000000000000000000' + \
             'aaaaaaaaaaaaaaaa000000000000000000000000'

        dont_ignore_low_values = int('00000001', 16)
        self.assertEqual(

            checksum(hash, dont_ignore_low_values),
            0xaaaaaaaaaaaa8001
        )

        ignore_high_values = int('10000000', 16)
        self.assertEqual(
            checksum(hash, ignore_high_values),
            0xaaaaaaaaaaaa8000
        )

    def test_pattern(self):
        hash = '000000000000000000000000' + \
            '01234567aaaaaaaa' + \
            'ffffffffffffffffffffffff'
        index = int('89abcdef', 16)
        self.assertEqual(hex(checksum(hash, index)), '0x1234567aaaacdef')
