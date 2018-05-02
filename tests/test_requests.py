import asyncio
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
        "request_with_hash": [b"blockchain.fetch_block_header", b"\x02\x00\x00\x00", unhexlify("4286e1e988ce7af64b82275f5ae36407c92da522a79461851541b66b29e1e63b")],  # noqa: E501
        "response": [b"blockchain.fetch_block_header", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + bitcoin.core.CBlockHeader().serialize()],  # noqa: E501
    },
}


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


def deserialize_response(frame):
    return [
            frame[0],                               # Command
            struct.unpack("<I", frame[1])[0],       # Request ID
            struct.unpack("<I", frame[2][:4])[0],   # Error Code
            frame[2][4:]                            # Data
        ]


class TestLastHeight(asynctest.TestCase):
    pylibbitcoin.client.create_random_id = lambda: 2

    def test_correctness_of_request(self):
        c = client_with_mocked_socket()

        self.loop.run_until_complete(c.last_height())

        c._socket.send_multipart.assert_called_with(
            api_interactions["last_height"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        asyncio.Future = CoroutineMock(
            autospec=asyncio.Future,
            return_value=deserialize_response(
                api_interactions["last_height"]["response"])
        )

        error_code, height = self.loop.run_until_complete(c.last_height())

        self.assertEqual(height, 1000)
        self.assertIsNone(error_code)


class TestBlockHeader(asynctest.TestCase):
    pylibbitcoin.client.create_random_id = lambda: 2

    def test_correctness_of_request_with_height(self):
        c = client_with_mocked_socket()

        self.loop.run_until_complete(c.block_header(200_000))

        c._socket.send_multipart.assert_called_with(
            api_interactions["block_header"]["request_with_height"]
        )

    def test_correctness_of_request_with_hash(self):
        c = client_with_mocked_socket()

        header_hash_as_string = \
            "4286e1e988ce7af64b82275f5ae36407c92da522a79461851541b66b29e1e63b"
        self.loop.run_until_complete(c.block_header(header_hash_as_string))

        c._socket.send_multipart.assert_called_with(
            api_interactions["block_header"]["request_with_hash"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        asyncio.Future = CoroutineMock(
            autospec=asyncio.Future,
            return_value=deserialize_response(
                api_interactions["block_header"]["response"])
        )

        error_code, block = self.loop.run_until_complete(
            c.block_header(200_000))

        self.assertIsNone(error_code)
        self.assertIsInstance(block, bitcoin.core.CBlockHeader)


class TestBlockTransactionHashes(asynctest.TestCase):
    command = b"blockchain.fetch_block_transaction_hashes"
    reply_id = 2
    error_code = 0
    reply_data = b"1000"

    def setUp(self):
        mock_future = CoroutineMock(
            autospec=asyncio.Future,
            return_value=[
                self.command,
                self.reply_id,
                self.error_code,
                self.reply_data]
        )()
        self.c = client_with_mocked_socket()
        self.c._register_future = lambda: [mock_future, self.reply_id]

    def test_block_transaction_hashes_by_hash(self):
        header_hash_as_string = \
            "0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c"
        self.loop.run_until_complete(
            self.c.block_transaction_hashes(header_hash_as_string))

        self.c._socket.send_multipart.assert_called_with(
            [
                self.command,
                struct.pack("<I", self.reply_id),
                unhexlify(header_hash_as_string)
            ]
        )

    def test_block_transaction_hashes_by_height(self):
        block_height = 1234
        self.loop.run_until_complete(
            self.c.block_transaction_hashes(block_height))

        self.c._socket.send_multipart.assert_called_with(
            [
                self.command,
                struct.pack("<I", self.reply_id),
                struct.pack('<I', block_height)
            ]
        )


class TestBlockHeight(asynctest.TestCase):
    command = b"blockchain.fetch_block_height"
    reply_id = 2
    error_code = 0
    reply_data = b"1000"

    def setUp(self):
        mock_future = CoroutineMock(
            autospec=asyncio.Future,
            return_value=[
                self.command,
                self.reply_id,
                self.error_code,
                self.reply_data]
        )()
        self.c = client_with_mocked_socket()
        self.c._register_future = lambda: [mock_future, self.reply_id]

    def test_block_height(self):
        header_hash_as_string = \
            "0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c"

        self.loop.run_until_complete(
            self.c.block_height(header_hash_as_string))

        self.c._socket.send_multipart.assert_called_with(
            [
                self.command,
                struct.pack("<I", self.reply_id),
                bytes.fromhex(header_hash_as_string)[::-1]
            ]
        )


class TestTransaction(asynctest.TestCase):
    command = b"blockchain.fetch_transaction"
    reply_id = 2
    error_code = 0
    reply_data = bitcoin.core.CTransaction().serialize()

    def setUp(self):
        mock_future = CoroutineMock(
            autospec=asyncio.Future,
            return_value=[
                self.command,
                self.reply_id,
                self.error_code,
                self.reply_data]
        )()
        self.c = client_with_mocked_socket()
        self.c._register_future = lambda: [mock_future, self.reply_id]

    def test_transaction(self):
        transaction_hash = \
            "e400712f48693950b78aef3e298b590cfd4bc9a1a91beb0547fb25bc73d220b9"
        self.loop.run_until_complete(
            self.c.transaction(transaction_hash))

        self.c._socket.send_multipart.assert_called_with(
            [
                self.command,
                struct.pack("<I", self.reply_id),
                bytes.fromhex(transaction_hash)[::-1]
            ]
        )


class TestTransactionIndex(asynctest.TestCase):
    command = b"blockchain.fetch_transaction_index"
    reply_id = 2
    error_code = 0
    reply_data = b"10001000"

    def setUp(self):
        mock_future = CoroutineMock(
            autospec=asyncio.Future,
            return_value=[
                self.command,
                self.reply_id,
                self.error_code,
                self.reply_data]
        )()
        self.c = client_with_mocked_socket()
        self.c._register_future = lambda: [mock_future, self.reply_id]

    def test_transaction_index(self):
        transaction_hash = \
            "e400712f48693950b78aef3e298b590cfd4bc9a1a91beb0547fb25bc73d220b9"
        self.loop.run_until_complete(
            self.c.transaction_index(transaction_hash))

        self.c._socket.send_multipart.assert_called_with(
            [
                self.command,
                struct.pack("<I", self.reply_id),
                bytes.fromhex(transaction_hash)[::-1]
            ]
        )


class TestSpend(asynctest.TestCase):
    command = b"blockchain.fetch_spend"
    reply_id = 2
    error_code = 0
    reply_data = bitcoin.core.COutPoint().serialize()

    def setUp(self):
        mock_future = CoroutineMock(
            autospec=asyncio.Future,
            return_value=[
                self.command,
                self.reply_id,
                self.error_code,
                self.reply_data]
        )()
        self.c = client_with_mocked_socket()
        self.c._register_future = lambda: [mock_future, self.reply_id]

    def test_spend(self):
        transaction_hash = \
            "0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09"
        index = 0
        self.loop.run_until_complete(
            self.c.spend(transaction_hash, 0))

        self.c._socket.send_multipart.assert_called_with(
            [
                self.command,
                struct.pack("<I", self.reply_id),
                bitcoin.core.COutPoint(
                    bytes.fromhex(transaction_hash)[::-1], index).serialize()
            ]
        )


class TestTransactionPoolTransaction(asynctest.TestCase):
    command = b"transaction_pool.fetch_transaction"
    reply_id = 2
    error_code = 0
    reply_data = bitcoin.core.CTransaction().serialize()

    def setUp(self):
        mock_future = CoroutineMock(
            autospec=asyncio.Future,
            return_value=[
                self.command,
                self.reply_id,
                self.error_code,
                self.reply_data]
        )()
        self.c = client_with_mocked_socket()
        self.c._register_future = lambda: [mock_future, self.reply_id]

    def test_transaction_pool_transaction(self):
        transaction_hash = \
            "0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09"
        self.loop.run_until_complete(
            self.c.possibly_unconfirmed_transaction(transaction_hash))

        self.c._socket.send_multipart.assert_called_with(
            [
                self.command,
                struct.pack("<I", self.reply_id),
                bytes.fromhex(transaction_hash)[::-1]
            ]
        )


class TestTransaction2(asynctest.TestCase):
    command = b"blockchain.fetch_transaction2"
    reply_id = 2
    error_code = 0
    reply_data = bitcoin.core.CTransaction().serialize()

    def setUp(self):
        mock_future = CoroutineMock(
            autospec=asyncio.Future,
            return_value=[
                self.command,
                self.reply_id,
                self.error_code,
                self.reply_data]
        )()
        self.c = client_with_mocked_socket()
        self.c._register_future = lambda: [mock_future, self.reply_id]

    def test_transaction2(self):
        transaction_hash = \
            "0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09"
        self.loop.run_until_complete(
            self.c.transaction2(transaction_hash))

        self.c._socket.send_multipart.assert_called_with(
            [
                self.command,
                struct.pack("<I", self.reply_id),
                bytes.fromhex(transaction_hash)[::-1]
            ]
        )
