import asyncio
import struct
from binascii import unhexlify
import asynctest
from asynctest import CoroutineMock, MagicMock
import bitcoin.core.serialize
import zmq
import zmq.asyncio

import pylibbitcoin.client


def client_with_mocked_socket():
    pylibbitcoin.client.RequestCollection = MagicMock()

    mock_zmq_socket = CoroutineMock()
    mock_zmq_socket.connect.return_value = None
    mock_zmq_socket.send_multipart = CoroutineMock()

    mock_zmq_context = MagicMock(autospec=zmq.asyncio.Context)
    mock_zmq_context.socket.return_value = mock_zmq_socket

    settings = pylibbitcoin.client.ClientSettings(context=mock_zmq_context)

    return pylibbitcoin.client.Client('irrelevant', settings)


class TestLastHeight(asynctest.TestCase):
    command = b"blockchain.fetch_last_height"
    reply_id = 2
    error_code = 0
    reply_data = b"1000"

    def test_last_height(self):
        mock_future = CoroutineMock(
            autospec=asyncio.Future,
            return_value=[
                self.command,
                self.reply_id,
                self.error_code,
                self.reply_data]
        )()

        c = client_with_mocked_socket()
        c._register_future = lambda: [mock_future, self.reply_id]

        self.loop.run_until_complete(c.last_height())

        c._socket.send_multipart.assert_called_with(
            [self.command, struct.pack("<I", self.reply_id), b""]
        )


class TestBlockHeader(asynctest.TestCase):
    command = b"blockchain.fetch_block_header"
    reply_id = 2
    error_code = 0
    reply_data = bitcoin.core.CBlockHeader().serialize()

    def test_block_header_by_height(self):
        mock_future = CoroutineMock(
            autospec=asyncio.Future,
            return_value=[
                self.command,
                self.reply_id,
                self.error_code,
                self.reply_data]
        )()

        c = client_with_mocked_socket()
        c._register_future = lambda: [mock_future, self.reply_id]

        block_height = 1234
        self.loop.run_until_complete(c.block_header(block_height))

        c._socket.send_multipart.assert_called_with(
            [
                self.command,
                struct.pack("<I", self.reply_id),
                struct.pack('<I', block_height)
            ]
        )

    def test_block_header_by_hash(self):
        mock_future = CoroutineMock(
            autospec=asyncio.Future,
            return_value=[
                self.command,
                self.reply_id,
                self.error_code,
                self.reply_data]
        )()

        c = client_with_mocked_socket()
        c._register_future = lambda: [mock_future, self.reply_id]

        header_hash_as_string = \
            "0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c"
        self.loop.run_until_complete(c.block_header(header_hash_as_string))

        c._socket.send_multipart.assert_called_with(
            [
                self.command,
                struct.pack("<I", self.reply_id),
                unhexlify(header_hash_as_string)
            ]
        )


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
        index = 0
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
        index = 0
        self.loop.run_until_complete(
            self.c.transaction2(transaction_hash))

        self.c._socket.send_multipart.assert_called_with(
            [
                self.command,
                struct.pack("<I", self.reply_id),
                bytes.fromhex(transaction_hash)[::-1]
            ]
        )
