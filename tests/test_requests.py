import unittest
import asyncio
import struct

from asynctest import CoroutineMock, MagicMock
import zmq
import zmq.asyncio

import pylibbitcoin.client


class TestLastHeight(unittest.TestCase):
    def test_last_height(self):
        reply_id = 2
        command = b"blockchain.fetch_last_height"
        error_code = 0
        reply_data = b"1000"

        pylibbitcoin.client.create_random_id = MagicMock(return_value=reply_id)
        mock_future = CoroutineMock(autospec=asyncio.Future)
        mock_future.return_value = [command, reply_id, error_code, reply_data]
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
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(c.last_height())
        finally:
            loop.close()

        mock_zmq_socket.send_multipart.assert_called_with([command, struct.pack("<I", reply_id), b""])
