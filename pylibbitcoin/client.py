import random
import struct
import asyncio
from binascii import unhexlify
import zmq
import zmq.asyncio
import bitcoin.core.serialize
import bitcoin.base58
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


def decode_address(address):
    decoded_address = bitcoin.base58.decode(address)
    # pick the decoded bytes apart:
    # version_byte, data, checksum = decoded_address[0:1], decoded_address[1:-4], decoded_address[-4:]  # noqa: E501
    return decoded_address[1:-4]


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
        """Set to None for no timeout."""
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        self._timeout = timeout


class Request:
    """
    This class represents a _send_ Request.
    This is either a simple request/response affair or a subscription.
    """

    def __init__(self, command):
        """ Use 'create' instead"""
        self.id = create_random_id()
        self.command = command
        self.future = asyncio.Future()
        self.queue = None

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

    def is_subscription(self):
        """ If the request is a subscription then the response to this request
        is a notification (as defined here https://github.com/libbitcoin/libbitcoin-server/wiki/Query-Service#subscribeaddress)"""  # noqa: E501
        return self.queue is not None

    def __str__(self):
        return("Request(command, ID) %s, %d" % (self.command, self.id))


class InvalidServerResponseException(Exception):
    pass


class Response:

    def __init__(self, frame):
        if len(frame) != 3:
            raise InvalidServerResponseException(
                "Length of the frame was not 3: %d" % len(frame))

        self.command = frame[0]
        self.request_id = struct.unpack("<I", frame[1])[0]
        ec = struct.unpack("<I", frame[2][:4])[0]
        self.error_code = pylibbitcoin.error_code.make_error_code(ec)
        self.data = frame[2][4:]

    def is_bound_for_queue(self):
        return len(self.data) > 0

    def __str__(self):
        return "Response(command, request ID, error code, data):"\
            + " %s, %d, %s, %s"\
            % (self.command, self.request_id, self.error_code, self.data)


class RequestCollection:
    """
    RequestCollection carries a list of Requests and matches incoming responses
    to them.
    """
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
        response = Response(frame)

        if response.request_id in self._requests:
            self._handle_response(response)
        else:
            print(
                "Error: unhandled response %s:%s." %
                (response.command, response.request_id))

    def _handle_response(self, response):
        request = self._requests[response.request_id]

        if request.is_subscription():
            if response.is_bound_for_queue():
                request.queue.put_nowait(response.data)
            else:
                request.future.set_result(response)
        else:
            self.delete_request(request)
            request.future.set_result(response)

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

    async def _subscription_request(self, command, data):
        request = await self._request(command, data)
        request.queue = asyncio.Queue()
        ec, _ = await self._wait_for_response(request)
        return ec, request.queue

    async def _simple_request(self, command, data):
        return await self._wait_for_response(
            await self._request(command, data))

    async def _request(self, command, data):
        """Make a generic request. Both options are byte objects specified like
        b"blockchain.fetch_block_header" as an example."""
        request = await Request.create(self._socket, command, data)
        self._request_collection.add_request(request)

        return request

    async def _wait_for_response(self, request):
        try:
            response = await asyncio.wait_for(
                request.future,
                self.settings.timeout)
        except asyncio.TimeoutError:
            self._request_collection.delete_request(request)
            return pylibbitcoin.error_code.ErrorCode.channel_timeout, None

        assert response.command == request.command
        assert response.request_id == request.id
        return response.error_code, response.data

    async def last_height(self):
        """Fetches the height of the last block in our blockchain."""
        command = b"blockchain.fetch_last_height"
        ec, data = await self._simple_request(command, b"")
        if ec:
            return ec, None
        # Deserialize data
        height = struct.unpack("<I", data)[0]
        return ec, height

    async def block_header(self, index):
        """Fetches the block header by height or integer index."""
        command = b"blockchain.fetch_block_header"
        data = pack_block_index(index)
        ec, data = await self._simple_request(command, data)
        if ec:
            return ec, None
        return ec, bitcoin.core.CBlockHeader.deserialize(data)

    async def block_transaction_hashes(self, index):
        command = b"blockchain.fetch_block_transaction_hashes"
        data = pack_block_index(index)
        ec, data = await self._simple_request(command, data)
        if ec:
            return ec, None
        data = unpack_table("32s", data)
        return ec, data

    async def block_height(self, hash):
        command = b"blockchain.fetch_block_height"
        ec, data = await self._simple_request(
            command, bytes.fromhex(hash)[::-1])
        if ec:
            return ec, None
        data = struct.unpack("<I", data)[0]
        return ec, data

    async def transaction(self, hash):
        command = b"blockchain.fetch_transaction"
        ec, data = await self._simple_request(
            command, bytes.fromhex(hash)[::-1])
        if ec:
            return ec, None

        transaction = bitcoin.core.CTransaction.deserialize(data)
        return None, transaction

    async def transaction_index(self, hash):
        """Fetch the block height that contains a transaction and its index
        within that block."""
        command = b"blockchain.fetch_transaction_index"
        ec, data = await self._simple_request(
            command, bytes.fromhex(hash)[::-1])
        if ec:
            return ec, None

        data = struct.unpack("<II", data)
        return None, data

    async def spend(self, output_transaction_hash, index):
        command = b"blockchain.fetch_spend"
        ec, data = await self._simple_request(
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
        ec, data = await self._simple_request(
            command, bytes.fromhex(hash)[::-1])
        if ec:
            return ec, None

        transaction = bitcoin.core.CTransaction.deserialize(data)
        return None, transaction

    async def transaction2(self, hash):
        command = b"blockchain.fetch_transaction2"
        ec, data = await self._simple_request(
            command, bytes.fromhex(hash)[::-1])
        if ec:
            return ec, None

        transaction = bitcoin.core.CTransaction.deserialize(data)
        return None, transaction

    async def transaction_pool_transaction2(self, hash):
        command = b"transaction_pool.fetch_transaction"
        ec, data = await self._simple_request(
            command, bytes.fromhex(hash)[::-1])
        if ec:
            return ec, None

        transaction = bitcoin.core.CTransaction.deserialize(data)
        return None, transaction

    async def subscribe_address(self, address):
        command = b"subscribe.address"
        decoded_address = decode_address(address)
        ec, queue = await self._subscription_request(
            command, decoded_address)
        if ec:
            return ec, None

        return None, queue

    # TODO this call should ideally also remove the subscription request from the RequestCollection.
    # This call solicits a final call from the server with a `error::service_stopped` error code.
    async def unsubscribe_address(self, address):
        command = b"unsubscribe_address"
        decoded_address = decode_address(address)
        return await self._simple_request(
            command, decoded_address)
