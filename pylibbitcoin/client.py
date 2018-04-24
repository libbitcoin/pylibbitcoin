import random
import struct
import asyncio
import sys
import zmq
import zmq.asyncio
import pylibbitcoin.error_code


def create_random_id():
    MAX_UINT32 = 4294967295
    return random.randint(0, MAX_UINT32)


class ClientSettings:

    def __init__(self):
        self._renew_time = 5 * 60
        self._query_expire_time = None
        self._socks5 = None
        self._context = None

    @property
    def context(self):
        if not self._context:
            self._context = zmq.asyncio.Context()
        return self._context

    @context.setter
    def context(self, context):
        self._context = context

    @property
    def renew_time(self):
        """The renew time for address or stealth subscriptions.
        This number should be lower than the setting for the blockchain
        server. A good value is server_renew_time / 2"""
        return self._renew_time

    @renew_time.setter
    def renew_time(self, renew_time):
        self._renew_time = renew_time

    @property
    def query_expire_time(self):
        """The timeout for a query in seconds. If this time expires
        then the blockchain method will return libbitcoin.server.ErrorCode
        Set to None for no timeout."""
        return self._query_expire_time

    @query_expire_time.setter
    def query_expire_time(self, query_expire_time):
        self._query_expire_time = query_expire_time


class RequestCollection:

    def __init__(self, socket):
        self._socket = socket
        self._futures = {}

        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._run())

    async def _run(self):
        while True:
            await self._receive()

    def stop(self):
        self._task.cancel()

    async def _receive(self):
        # Get the reply
        frame = await self._socket.recv_multipart()
        reply = self._deserialize(frame)
        if reply is None:
            print("Error: bad reply sent by server. Discarding.",
                  file=sys.stderr)
            return

        command, reply_id, *_ = reply
        if reply_id in self._futures:
            # Lookup the future based on request ID
            future = self._futures[reply_id]
            del self._futures[reply_id]
            # Set the result for the future
            try:
                future.set_result(reply)
            except asyncio.InvalidStateError:
                # Future timed out.
                pass
        else:
            print("Error: unhandled frame %s:%s." % (command, reply_id))

    def _deserialize(self, frame):
        if len(frame) != 3:
            return None
        return [
            frame[0],                               # Command
            struct.unpack("<I", frame[1])[0],       # Request ID
            struct.unpack("<I", frame[2][:4])[0],   # Error Code
            frame[2][4:]                            # Data
        ]

    def add_future(self, request_id, future):
        self._futures[request_id] = future

    def delete_future(self, request_id):
        del self._futures[request_id]


class Client:

    def __init__(self, url, settings=ClientSettings()):
        self._url = url
        self.settings = settings
        self._socket = self._create_socket()

        self._request_collection = RequestCollection(self._socket)

    def stop(self):
        self._request_collection.stop()
        self._socket.close()

    def _create_socket(self):
        socket = self.settings.context.socket(zmq.DEALER)
        socket.connect(self._url)
        return socket

    async def _send_request(self, command, request_id, data):
        request = [
            command,
            struct.pack("<I", request_id),
            data
        ]
        await self._socket.send_multipart(request)

    async def request(self, request_command, request_data):
        """Make a generic request. Both options are byte objects specified like
        b"blockchain.fetch_block_header" as an example."""
        future = asyncio.Future()
        request_id = create_random_id()
        self._request_collection.add_future(request_id, future)

        await self._send_request(request_command, request_id, request_data)

        expiry_time = self.settings.query_expire_time
        try:
            reply = await asyncio.wait_for(future, expiry_time)
        except asyncio.TimeoutError:
            self._request_collection.delete_future(request_id)
            return pylibbitcoin.error_code.ErrorCode.channel_timeout, None

        reply_command, reply_id, ec, data = reply
        assert reply_command == request_command
        assert reply_id == request_id
        ec = pylibbitcoin.error_code.make_error_code(ec)
        return ec, data

    async def last_height(self):
        """Fetches the height of the last block in our blockchain."""
        command = b"blockchain.fetch_last_height"
        ec, data = await self.request(command, b"")
        if ec:
            return ec, None
        # Deserialize data
        height = struct.unpack("<I", data)[0]
        return ec, height
