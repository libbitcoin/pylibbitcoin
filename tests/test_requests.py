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
