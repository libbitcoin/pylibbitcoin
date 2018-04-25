import asyncio
import struct

import asynctest
from asynctest import CoroutineMock, MagicMock
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
    reply_data = b"1000"
    pylibbitcoin.client.create_random_id = MagicMock(return_value=reply_id)

    def test_block_header_by_height(self):

        mock_future = CoroutineMock(autospec=asyncio.Future)
        mock_future.return_value = [self.command, self.reply_id, self.error_code, self.reply_data]
        asyncio.Future = mock_future

        pylibbitcoin.client.RequestCollection = MagicMock()
        mock_zmq_socket = CoroutineMock()
        mock_zmq_socket.connect.return_value = None
        mock_zmq_socket.send_multipart = CoroutineMock()

        mock_zmq_context = MagicMock(autospec=zmq.asyncio.Context)
        mock_zmq_context.socket.return_value = mock_zmq_socket
        settings = pylibbitcoin.client.ClientSettings()
        settings.context = mock_zmq_context

        c = pylibbitcoin.client.Client('irrelevant', settings)
        self.loop.run_until_complete(c.block_header(1234))
        mock_zmq_socket.send_multipart.assert_called_with([self.command, struct.pack("<I", self.reply_id), struct.pack('<I', 1234)])

    def test_block_header_by_hash(self):
        pass
        #self.loop.run_until_complete(c.block_header(hexlify("0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c")))
        #mock_zmq_socket.send_multipart.assert_called_with([self.command, struct.pack("<I", self.reply_id), struct.pack('<I', 1234)])
