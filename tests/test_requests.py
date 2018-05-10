import struct
from binascii import unhexlify
import asynctest
from asynctest import CoroutineMock, MagicMock
import bitcoin.core.serialize
import zmq
import zmq.asyncio

import pylibbitcoin.client

"""
api_interactions has all API calls.
request_id == 2 == b"\x02\x00\x00\x00"
error_code == 0 == b"\x00\x00\x00\x00"
request: [command, request_id, data]
response: [command, request_id, error_code + data]
Note that the response has the error code and the data in one frame!
"""
api_interactions = {
    "last_height": {
        "request": [b"blockchain.fetch_last_height", b"\x02\x00\x00\x00", b""],
        "response": [b"blockchain.fetch_last_height", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + b"\xe8\x03\x00\x00"],  # noqa: E501
    },
    "block_header": {
        "request_with_height": [b"blockchain.fetch_block_header", b"\x02\x00\x00\x00", b'@\r\x03\x00'],  # noqa: E501
        "request_with_hash": [b"blockchain.fetch_block_header", b"\x02\x00\x00\x00", unhexlify("0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c")],  # noqa: E501
        "response": [b"blockchain.fetch_block_header", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + bitcoin.core.CBlockHeader().serialize()],  # noqa: E501
    },
    "block_transaction_hashes": {
        "request_with_height": [b"blockchain.fetch_block_transaction_hashes", b"\x02\x00\x00\x00", b'@\r\x03\x00'],  # noqa: E501
        "request_with_hash": [b"blockchain.fetch_block_transaction_hashes", b"\x02\x00\x00\x00", unhexlify("0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c")],  # noqa: E501
        "response": [b"blockchain.fetch_block_transaction_hashes", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + unhexlify("a"*64 + "b"*64)],  # noqa: E501
    },
    "block_height": {
        "request": [b"blockchain.fetch_block_height", b"\x02\x00\x00\x00", bytes.fromhex("0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c")[::-1]],  # noqa: E501
        "response": [b"blockchain.fetch_block_height", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + struct.pack("<I", 200_000)],  # noqa: E501
    },
    "transaction": {
        "request": [b"blockchain.fetch_transaction", b"\x02\x00\x00\x00", bytes.fromhex("e400712f48693950b78aef3e298b590cfd4bc9a1a91beb0547fb25bc73d220b9")[::-1]],  # noqa: E501
        "response": [b"blockchain.fetch_transaction", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + bitcoin.core.CTransaction().serialize()],  # noqa: E501
    },
    "transaction_index": {
        "request": [b"blockchain.fetch_transaction_index", b"\x02\x00\x00\x00", bytes.fromhex("e400712f48693950b78aef3e298b590cfd4bc9a1a91beb0547fb25bc73d220b9")[::-1]],  # noqa: E501
        "response": [b"blockchain.fetch_transaction_index", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + struct.pack("<I", 200_000) + struct.pack("<I", 1)],  # noqa: E501
    },
    "spend": {
        "request": [b"blockchain.fetch_spend", b"\x02\x00\x00\x00", bitcoin.core.COutPoint(bytes.fromhex("0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09")[::-1], 0).serialize()],  # noqa: E501
        "response": [b"blockchain.fetch_spend", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + bitcoin.core.COutPoint().serialize()],  # noqa: E501
    },
    "transaction_pool_transaction": {
        "request": [b"transaction_pool.fetch_transaction", b"\x02\x00\x00\x00", bytes.fromhex("0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09")[::-1]],  # noqa: E501
        "response": [b"transaction_pool.fetch_transaction", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + bitcoin.core.CTransaction().serialize()],  # noqa: E501
    },
    "transaction2": {
        "request": [b"blockchain.fetch_transaction2", b"\x02\x00\x00\x00", bytes.fromhex("0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09")[::-1]],  # noqa: E501
        "response": [b"blockchain.fetch_transaction2", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + bitcoin.core.CTransaction().serialize()],  # noqa: E501
    },
    "broadcast": {
        "request": [b"blockchain.broadcast", b"\x02\x00\x00\x00", bytes.fromhex("00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38")],  # noqa: E501
        "response": [b"blockchain.broadcast", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + b""],  # noqa: E501
    },
    "history3": {
        "request": [b"blockchain.fetch_history3", b"\x02\x00\x00\x00", b'N\x94.\xc6W\n\xae\x02o\xc1\xac\x88 /\x07\x9e\xcb\x9b\xc3h' + b'\xa8a\x00\x00'],  # noqa: E501
        "response": [b"blockchain.fetch_history3", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + b'\x00\x14\x87\xd7\xc6\xb0\x11\xf0\xa7lf\xa6\xa6\xeb\xb1\xe5SV[\xcb\xb1?SU\x8d\xdb\xb0- \xf9\xfe\\\x04\x01\x00\x00\x00`\xca\x13\x00\xa0\x86\x01\x00\x00\x00\x00\x00\x00\xe6:L\'G5i\x90%\xd3{k\xd7\x16\xe8\x97_I\x9f\x88>\xbdj\xa9\xb8#@]\xc3\xc4\xbe\x95\x01\x00\x00\x00\x11\xca\x13\x00\xa0\x86\x01\x00\x00\x00\x00\x00\x00\xbc\n\xa8\x9c~\x8c\xac\xabP4\x97\x10\xfe\x88\xe9\xa0\x97\xf8\x00Rg\xf5\x96\xf5"^\x85c\tie\xbf\x01\x00\x00\x00|\xc9\x13\x00\xa0\x86\x01\x00\x00\x00\x00\x00\x00\xfa|\xd8\xa0\r\x1c\xc9\xa2\x1e\xb8\x94\xba\xf7\x00\x12\xf6K7D@\x80\x08t\xa4:G93gW\xa3\xbb\x00\x00\x00\x00z\xc9\x13\x00\xa0\x86\x01\x00\x00\x00\x00\x00\x00\xdf\xe7(.\xfay*\xc0\x04*\xd3S\x1a\t\x95\xed\x9d\x83;%\xa3\x12\xed\x94\xe7\xf9\x16N\x19hNJ\x00\x00\x00\x00\xee\xc6\x13\x00\xa0\x86\x01\x00\x00\x00\x00\x00\x00j\xe5\xfa\xff\xb1+\xf7\x1a\xf7\xca\x02\x0eF\xa7\xe2\x98\x84\x1d\xcb8 T$\x99q\xc9{\xcc\x91\xd7\xe0\xc9\x00\x00\x00\x00\xeb\xc6\x13\x00\xa0\x86\x01\x00\x00\x00\x00\x00\x00:mLA\x03\xabnPy\xfb\xab\x06\x02Y\xedB\'\xec\xce\xe49\xb6\xac\x11^\xec\x0b\x9c\xf2\xd1R\x89\x00\x00\x00\x00\xe9\xc6\x13\x00\xa0\x86\x01\x00\x00\x00\x00\x00\x00\xdc#_\x96\xfa\xc4\x1d\x95>$0\xb5\x8fC:4q\x88\xe8\x98\n\xce\x0c\xb4Z8\xe0\xbd\xb5p\x96\xab\x01\x00\x00\x00\xe7\xc6\x13\x00\xa0\x86\x01\x00\x00\x00\x00\x00\x00;\xe6\xe1)k\xb6A\x15\x85a\x94\xa7"\xa5-\xc9\x07d\xe3Z_\'\x82K\xf6z\xce\x88\xe9\xe1\x86B\x00\x00\x00\x00g\xc4\x13\x00\xc0\x0e\x16\x02\x00\x00\x00\x00'],  # noqa: E501
    },
    "validate": {
        "request": [b"blockchain.validate", b"\x02\x00\x00\x00", bytes.fromhex("00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38")],  # noqa: E501
        "response": [b"blockchain.validate", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + b""],  # noqa: E501
    },
    "transaction_pool_broadcast": {
        "request": [b"transaction_pool.broadcast", b"\x02\x00\x00\x00", bytes.fromhex("00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38")],  # noqa: E501
        "response": [b"transaction_pool.broadcast", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + b""],  # noqa: E501
    },
    "transaction_pool_validate2": {
        "request": [b"transaction_pool.validate2", b"\x02\x00\x00\x00", bytes.fromhex("00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38")],  # noqa: E501
        "response": [b"transaction_pool.validate2", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + b""],  # noqa: E501
    },
}

# Make sure the random ID is static
pylibbitcoin.client.create_random_id = lambda: 2


def client_with_mocked_socket():
    pylibbitcoin.client.RequestCollection = MagicMock()

    mock_zmq_socket = CoroutineMock()
    mock_zmq_socket.connect.return_value = None
    mock_zmq_socket.send_multipart = CoroutineMock()

    mock_zmq_context = MagicMock(autospec=zmq.asyncio.Context)
    mock_zmq_context.socket.return_value = mock_zmq_socket

    settings = pylibbitcoin.client.ClientSettings(
        context=mock_zmq_context,
        timeout=0.01)

    return pylibbitcoin.client.Client('irrelevant', settings)


def raw_response_to_return_type(response):
    resp = pylibbitcoin.client.Response(response)
    return resp.error_code, resp.data


class TestLastHeight(asynctest.TestCase):
    def test_correctness_of_request(self):
        c = client_with_mocked_socket()

        self.loop.run_until_complete(c.last_height())

        c._socket.send_multipart.assert_called_with(
            api_interactions["last_height"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["last_height"]["response"]))

        error_code, height = self.loop.run_until_complete(c.last_height())
        self.assertIsNone(error_code)
        self.assertEqual(height, 1000)


class TestBlockHeader(asynctest.TestCase):
    def test_correctness_of_request_with_height(self):
        c = client_with_mocked_socket()

        self.loop.run_until_complete(c.block_header(200_000))

        c._socket.send_multipart.assert_called_with(
            api_interactions["block_header"]["request_with_height"]
        )

    def test_correctness_of_request_with_hash(self):
        c = client_with_mocked_socket()

        header_hash_as_string = \
            "0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c"
        self.loop.run_until_complete(c.block_header(header_hash_as_string))

        c._socket.send_multipart.assert_called_with(
            api_interactions["block_header"]["request_with_hash"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["block_header"]["response"])
        )

        error_code, block = self.loop.run_until_complete(
            c.block_header(200_000))

        self.assertIsNone(error_code)
        self.assertIsInstance(block, bitcoin.core.CBlockHeader)


class TestBlockTransactionHashes(asynctest.TestCase):
    def test_block_transaction_hashes_by_hash(self):
        c = client_with_mocked_socket()

        header_hash_as_string = \
            "0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c"
        self.loop.run_until_complete(
            c.block_transaction_hashes(header_hash_as_string))

        c._socket.send_multipart.assert_called_with(
            api_interactions["block_transaction_hashes"]["request_with_hash"]
        )

    def test_block_transaction_hashes_by_height(self):
        c = client_with_mocked_socket()

        self.loop.run_until_complete(
            c.block_transaction_hashes(200_000))

        c._socket.send_multipart.assert_called_with(
            api_interactions["block_transaction_hashes"]["request_with_height"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["block_transaction_hashes"]["response"])
        )

        error_code, hashes = self.loop.run_until_complete(
            c.block_transaction_hashes(200_000))

        self.assertIsNone(error_code)
        self.assertEqual(len(hashes), 2)


class TestBlockHeight(asynctest.TestCase):
    def test_block_height(self):
        c = client_with_mocked_socket()
        header_hash_as_string = \
            "0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c"

        self.loop.run_until_complete(
            c.block_height(header_hash_as_string))

        c._socket.send_multipart.assert_called_with(
            api_interactions["block_height"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["block_height"]["response"])
        )
        header_hash_as_string = \
            "0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c"

        error_code, height = self.loop.run_until_complete(
            c.block_height(header_hash_as_string))

        self.assertIsNone(error_code)
        self.assertEqual(height, 200_000)


class TestTransaction(asynctest.TestCase):
    def test_transaction(self):
        c = client_with_mocked_socket()

        transaction_hash = \
            "e400712f48693950b78aef3e298b590cfd4bc9a1a91beb0547fb25bc73d220b9"
        self.loop.run_until_complete(
            c.transaction(transaction_hash))

        c._socket.send_multipart.assert_called_with(
            api_interactions["transaction"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["transaction"]["response"])
        )
        transaction_hash = \
            "e400712f48693950b78aef3e298b590cfd4bc9a1a91beb0547fb25bc73d220b9"

        error_code, transaction = self.loop.run_until_complete(
            c.transaction(transaction_hash))

        self.assertIsNone(error_code)
        self.assertIsInstance(transaction, bitcoin.core.CTransaction)


class TestTransactionIndex(asynctest.TestCase):
    def test_transaction_index(self):
        c = client_with_mocked_socket()
        transaction_hash = \
            "e400712f48693950b78aef3e298b590cfd4bc9a1a91beb0547fb25bc73d220b9"
        self.loop.run_until_complete(
            c.transaction_index(transaction_hash))

        c._socket.send_multipart.assert_called_with(
            api_interactions["transaction_index"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["transaction_index"]["response"])
        )
        transaction_hash = \
            "e400712f48693950b78aef3e298b590cfd4bc9a1a91beb0547fb25bc73d220b9"

        error_code, height = self.loop.run_until_complete(
            c.transaction_index(transaction_hash))

        self.assertIsNone(error_code)
        self.assertEqual(height, (200_000, 1))


class TestSpend(asynctest.TestCase):
    def test_spend(self):
        c = client_with_mocked_socket()
        transaction_hash = \
            "0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09"
        index = 0
        self.loop.run_until_complete(
            c.spend(transaction_hash, index))

        c._socket.send_multipart.assert_called_with(
            api_interactions["spend"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        transaction_hash = \
            "0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09"
        index = 0
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["spend"]["response"])
        )

        error_code, point = self.loop.run_until_complete(
            c.spend(transaction_hash, index))

        self.assertIsNone(error_code)
        self.assertIsInstance(point, bitcoin.core.COutPoint)


class TestTransactionPoolTransaction(asynctest.TestCase):
    def test_transaction_pool_transaction(self):
        c = client_with_mocked_socket()

        transaction_hash = \
            "0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09"
        self.loop.run_until_complete(
            c.possibly_unconfirmed_transaction(transaction_hash))

        c._socket.send_multipart.assert_called_with(
            api_interactions["transaction_pool_transaction"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()

        transaction_hash = \
            "0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09"
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["transaction_pool_transaction"]["response"])
        )

        error_code, transaction = self.loop.run_until_complete(
            c.possibly_unconfirmed_transaction(transaction_hash))

        self.assertIsNone(error_code)
        self.assertIsInstance(transaction, bitcoin.core.CTransaction)


class TestTransaction2(asynctest.TestCase):
    def test_transaction2(self):
        c = client_with_mocked_socket()

        transaction_hash = \
            "0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09"
        self.loop.run_until_complete(
            c.transaction2(transaction_hash))

        c._socket.send_multipart.assert_called_with(
            api_interactions["transaction2"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        transaction_hash = \
            "0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09"
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["transaction2"]["response"])
        )

        error_code, transaction = self.loop.run_until_complete(
            c.transaction2(transaction_hash))

        self.assertIsNone(error_code)
        self.assertIsInstance(transaction, bitcoin.core.CTransaction)


class TestBroadcast(asynctest.TestCase):
    def test_correctness_of_request(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        self.loop.run_until_complete(c.broadcast(block))

        c._socket.send_multipart.assert_called_with(
            api_interactions["broadcast"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["broadcast"]["response"])
        )

        error_code, _ = self.loop.run_until_complete(
            c.broadcast(block))

        self.assertIsNone(error_code)


class TestHistory3(asynctest.TestCase):
    def test_correctness_of_request(self):
        c = client_with_mocked_socket()

        address = "mngSWw2NC9M1ctqZQxz65DwVomCjm7TWPJ"
        self.loop.run_until_complete(c.history3(address, 25_000))

        c._socket.send_multipart.assert_called_with(
            api_interactions["history3"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()

        address = "mngSWw2NC9M1ctqZQxz65DwVomCjm7TWPJ"
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["history3"]["response"])
        )

        error_code, points = self.loop.run_until_complete(
            c.history3(address))

        self.assertIsNone(error_code)
        self.assertEqual(len(points), 9)
        point = points[0]
        self.assertEqual(point[0], 0)                            # type
        self.assertIsInstance(point[1], bitcoin.core.COutPoint)  # COutPoint
        self.assertEqual(point[2], 1296992)                      # block height
        self.assertEqual(point[3], 100000)                       # output value or spend ID  # noqa: E501


class TestValidate(asynctest.TestCase):
    def test_correctness_of_request(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        self.loop.run_until_complete(c.validate(block))

        c._socket.send_multipart.assert_called_with(
            api_interactions["validate"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["validate"]["response"])
        )

        error_code, _ = self.loop.run_until_complete(
            c.validate(block))

        self.assertIsNone(error_code)


class TestTransactionPoolBroadcast(asynctest.TestCase):
    def test_correctness_of_request(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        self.loop.run_until_complete(c.transaction_pool_broadcast(block))

        c._socket.send_multipart.assert_called_with(
            api_interactions["transaction_pool_broadcast"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["transaction_pool_broadcast"]["response"])
        )

        error_code, _ = self.loop.run_until_complete(
            c.transaction_pool_broadcast(block))

        self.assertIsNone(error_code)


class TestTransactionPoolValidate(asynctest.TestCase):
    def test_correctness_of_request(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        self.loop.run_until_complete(c.transaction_pool_validate2(block))

        c._socket.send_multipart.assert_called_with(
            api_interactions["transaction_pool_validate2"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["transaction_pool_validate2"]["response"])
        )

        error_code, _ = self.loop.run_until_complete(
            c.transaction_pool_validate2(block))

        self.assertIsNone(error_code)
