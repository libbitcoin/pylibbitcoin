import unittest
import asyncio

from asynctest import CoroutineMock, MagicMock
import zmq
import zmq.asyncio

import pylibbitcoin.client


class TestLastHeight(unittest.TestCase):
    def test_last_height(self):
        mock_future = CoroutineMock(autospec=asyncio.Future)
        mock_future.return_value = [1, 2, 3, 4]
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

        mock_zmq_socket.send_multipart.assert_called_with()
