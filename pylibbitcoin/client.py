import random
import struct
import asyncio
import sys
from binascii import unhexlify
import zmq
import zmq.asyncio
import bitcoin.core.serialize
import pylibbitcoin.error_code


def create_random_id():
    MAX_UINT32 = 4294967295
    return random.randint(0, MAX_UINT32)


def unpack_table(row_fmt, data):
    # get the number of rows
    row_size = struct.calcsize(row_fmt)
    nrows = len(data) // row_size

    # unpack
    rows = []
    for idx in range(nrows):
        offset = idx * row_size
        row = struct.unpack_from(row_fmt, data, offset)
        rows.append(row)
    return rows


def pack_block_index(index):
    if type(index) == str:
        index = unhexlify(index)
        assert len(index) == 32
        return index
    elif type(index) == int:
        return struct.pack('<I', index)
    else:
        raise ValueError("Unknown index type, shoud be an int or a byte array")


class ClientSettings:

    def __init__(self, timeout=2, context=None):
        self._timeout = timeout
        self._context = context

    @property
    def context(self):
        if not self._context:
            self._context = zmq.asyncio.Context()
        return self._context

    @context.setter
    def context(self, context):
        self._context = context

    @property
    def timeout(self):
        """The timeout for a query in seconds. If this time expires
        then the blockchain method will return libbitcoin.server.ErrorCode
        Set to None for no timeout."""
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        self._timeout = timeout


class Request:
    """
    This class represents a _send_ Request
    """

    def __init__(self, command):
        """ Use 'create' instead"""
        self.id = create_random_id()
        self.command = command
        self.future = asyncio.Future()

    async def create(socket, command, data):
        """ Use 'create' to create a Request object. The payload is already
        sent."""
        request = Request(command)
        await request._send(socket, data)
        return request

    async def _send(self, socket, data):
        request = [
            self.command,
            struct.pack("<I", self.id),
            data
        ]
        await socket.send_multipart(request)

    # TODO
    def is_subscription(self):
        """ If the request is a subscription then the response to this request
        is a notification (as defined here https://github.com/libbitcoin/libbitcoin-server/wiki/Query-Service#subscribeaddress)""" # noqa: E501,E261
        return False

    def __str__(self):
        return("Request %d: %s" % (self.id, self.command))


class RequestCollection:

    def __init__(self, socket):
        self._socket = socket
        self._requests = {}

        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._run())

    async def _run(self):
        while True:
            await self._receive()

    def stop(self):
        self._task.cancel()

    async def _receive(self):
        frame = await self._socket.recv_multipart()
        response = self._deserialize(frame)
        if response is None:
            print("Error: bad response sent by server. Discarding.",
                  file=sys.stderr)
            return

        command, response_id, *_ = response
        if response_id in self._requests:
            # Lookup the future based on request ID
            request = self._requests[response_id]
            self.delete_request(request)
            # Set the result for the future
            try:
                request.future.set_result(response)
            except asyncio.InvalidStateError:
                # Future timed out.
                pass
        else:
            print("Error: unhandled frame %s:%s." % (command, response_id))

    def _deserialize(self, frame):
        if len(frame) != 3:
            return None
        return [
            frame[0],                               # Command
            struct.unpack("<I", frame[1])[0],       # Request ID
            struct.unpack("<I", frame[2][:4])[0],   # Error Code
            frame[2][4:]                            # Data
        ]

    def add_request(self, request):
        # TODO we should maybe check if the request_id is unique
        self._requests[request.id] = request

    def delete_request(self, request):
        del self._requests[request.id]


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

    async def _request(self, command, data):
        """Make a generic request. Both options are byte objects specified like
        b"blockchain.fetch_block_header" as an example."""
        request = await Request.create(self._socket, command, data)
        self._request_collection.add_request(request)

        return await self._wait_for_response(request)

    def _register_future(self):
        future = asyncio.Future()
        request_id = create_random_id()
        self._request_collection.add_request(request_id, future)
        return future, request_id

    async def _wait_for_response(self, request):
        expiry_time = self.settings.timeout
        try:
            response = await asyncio.wait_for(request.future, expiry_time)
        except asyncio.TimeoutError:
            self._request_collection.delete_request(request.id)
            return pylibbitcoin.error_code.ErrorCode.channel_timeout, None

        response_command, response_id, ec, data = response
        assert response_command == request.command
        assert response_id == request.id
        ec = pylibbitcoin.error_code.make_error_code(ec)
        return ec, data

    async def last_height(self):
        """Fetches the height of the last block in our blockchain."""
        command = b"blockchain.fetch_last_height"
        ec, data = await self._request(command, b"")
        if ec:
            return ec, None
        # Deserialize data
        height = struct.unpack("<I", data)[0]
        return ec, height

    async def block_header(self, index):
        """Fetches the block header by height or integer index."""
        command = b"blockchain.fetch_block_header"
        data = pack_block_index(index)
        ec, data = await self._request(command, data)
        if ec:
            return ec, None
        return ec, bitcoin.core.CBlockHeader.deserialize(data)

    async def block_transaction_hashes(self, index):
        command = b"blockchain.fetch_block_transaction_hashes"
        data = pack_block_index(index)
        ec, data = await self._request(command, data)
        if ec:
            return ec, None
        data = unpack_table("32s", data)
        return ec, data

    async def block_height(self, hash):
        command = b"blockchain.fetch_block_height"
        ec, data = await self._request(command, bytes.fromhex(hash)[::-1])
        if ec:
            return ec, None
        data = struct.unpack("<I", data)[0]
        return ec, data

    async def transaction(self, hash):
        command = b"blockchain.fetch_transaction"
        ec, data = await self._request(command, bytes.fromhex(hash)[::-1])
        if ec:
            return ec, None

        transaction = bitcoin.core.CTransaction.deserialize(data)
        return None, transaction

    async def transaction_index(self, hash):
        command = b"blockchain.fetch_transaction_index"
        ec, data = await self._request(command, bytes.fromhex(hash)[::-1])
        if ec:
            return ec, None

        data = struct.unpack("<II", data)
        return None, data

    async def spend(self, output_transaction_hash, index):
        command = b"blockchain.fetch_spend"
        ec, data = await self._request(
            command,
            bitcoin.core.COutPoint(
                bytes.fromhex(output_transaction_hash)[::-1],
                index).serialize()
        )
        if ec:
            return ec, None

        # An CInPoint is just an other name for COutPoint
        point = bitcoin.core.COutPoint.deserialize(data)
        return None, point

    async def possibly_unconfirmed_transaction(self, hash):
        command = b"transaction_pool.fetch_transaction"
        ec, data = await self._request(command, bytes.fromhex(hash)[::-1])
        if ec:
            return ec, None

        transaction = bitcoin.core.CTransaction.deserialize(data)
        return None, transaction

    async def transaction2(self, hash):
        command = b"blockchain.fetch_transaction2"
        ec, data = await self._request(command, bytes.fromhex(hash)[::-1])
        if ec:
            return ec, None

        transaction = bitcoin.core.CTransaction.deserialize(data)
        return None, transaction

    async def transaction_pool_transaction2(self, hash):
        command = b"transaction_pool.fetch_transaction"
        ec, data = await self._request(command, bytes.fromhex(hash)[::-1])
        if ec:
            return ec, None

        transaction = bitcoin.core.CTransaction.deserialize(data)
        return None, transaction
