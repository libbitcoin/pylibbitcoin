import random
import struct
import asyncio
import functools
import hashlib
from binascii import unhexlify
import zmq
import zmq.asyncio
import bitcoin.core.serialize
import bitcoin.base58
import anytree
import pylibbitcoin.error_code


def merkle_branch(hash_, tree):
    tree_walker = anytree.PostOrderIter(tree)
    node = next((node for node in tree_walker if node.name == hash_), None)
    if not node:
        return None

    # TODO come up with a sane branch resprentation
    return node


def merkle_tree(hashes):
    if len(hashes) == 0:
        return None

    # It is a bit of a special case, you'd expect the len == 1 case to be
    # handled the same as the len % 2 == 1 case.
    if len(hashes) == 1:
        return anytree.Node(name=hashes[0])

    leaves = [anytree.Node(name=hash_) for hash_ in hashes]

    def next_layer(nodes):
        layer = []

        if len(nodes) % 2 == 1:
            nodes.append(anytree.Node(name=nodes[-1].name))

        while len(nodes) != 0:
            first = nodes.pop(0)
            second = nodes.pop(0)
            parent = anytree.Node(
                name=hashlib.sha256(
                    hashlib.sha256(first.name + second.name).digest()).digest()
            )
            first.parent = parent
            second.parent = parent
            layer.append(parent)

        return layer

    while len(leaves) != 1:
        leaves = next_layer(leaves)

    return leaves[0]


def checksum(hash_, index):
    """
    This method takes a transaction hash and an index and returns a checksum.

    This checksum is based on 49 bits starting from the 12th byte of the
    reversed hash. Combined with the last 15 bits of the 4 byte index.
    """

    mask = 0xffffffffffff8000
    magic_start_position = 12

    hash_bytes = bytes.fromhex(hash_)[::-1]
    last_20_bytes = hash_bytes[magic_start_position:]

    assert len(hash_bytes) == 32
    assert index < 2**32

    hash_upper_49_bits = to_int(last_20_bytes) & mask
    index_lower_15_bits = index & ~mask

    return hash_upper_49_bits | index_lower_15_bits


def to_int(some_bytes):
    return int.from_bytes(some_bytes, byteorder='little')


def to_little_endian(i):
    return struct.pack("<I", i)


def create_random_id():
    max_uint32 = 4294967295
    return random.randint(0, max_uint32)


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
    if isinstance(index, str):
        index = unhexlify(index)
        assert len(index) == 32
        return index
    elif isinstance(index, int):
        return struct.pack('<I', index)
    else:
        raise ValueError("Unknown index type, shoud be an int or a byte array")


def decode_address(address):
    decoded_address = bitcoin.base58.decode(address)
    # pick the decoded bytes apart:
    # version_byte, data, checksum = decoded_address[0:1], decoded_address[1:-4], decoded_address[-4:]  # noqa: E501
    return decoded_address[1:-4]


class ClientSettings:

    def __init__(self, timeout=2, context=None, loop=None):
        self._timeout = timeout
        self._context = context
        self._loop = loop

    @property
    def context(self):
        if not self._context:
            ctx = zmq.asyncio.Context()
            ctx.linger = 500  # in milliseconds
            self._context = ctx
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

    @property
    def loop(self):
        if not self._loop:
            self._loop = asyncio.get_event_loop()

        return self._loop

    @loop.setter
    def loop(self, loop):
        self._loop = loop


class Request:
    """
    This class represents a _send_ Request.
    This is either a simple request/response affair or a subscription.
    """

    def __init__(self, command):
        """ Use 'create' instead"""
        self.id_ = create_random_id()
        self.command = command
        self.future = asyncio.Future()
        self.queue = None

    async def create(socket, command, data):
        """ Use 'create' to create a Request object. The payload is already
        sent."""
        request = Request(command)
        await request.send(socket, data)
        return request

    async def send(self, socket, data):
        request = [
            self.command,
            to_little_endian(self.id_),
            data
        ]
        await socket.send_multipart(request)

    def is_subscription(self):
        """ If the request is a subscription then the response to this request
        is a notification (as defined here https://github.com/libbitcoin/libbitcoin-server/wiki/Query-Service#subscribeaddress)"""  # noqa: E501
        return self.queue is not None

    def __str__(self):
        return "Request(command, ID) {}, {:d}".format(self.command, self.id_)


class InvalidServerResponseException(Exception):
    pass


class Response:

    def __init__(self, frame):
        if len(frame) != 3:
            raise InvalidServerResponseException(
                "Length of the frame was not 3: %d" % len(frame))

        self.command = frame[0]
        self.request_id = struct.unpack("<I", frame[1])[0]
        error_code = struct.unpack("<I", frame[2][:4])[0]
        self.error_code = pylibbitcoin.error_code.make_error_code(error_code)
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

    def __init__(self, socket, loop):
        self._socket = socket
        self._requests = {}

        self._task = asyncio.ensure_future(self._run(), loop=loop)

    async def _run(self):
        while True:
            await self._receive()

    async def stop(self):
        """ Stops listening for incoming responses (or subscription messages).

        Returns the number of _responses_ expected but which now are dropped on
        the floor.
        """
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            return len(self._requests)

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
                # TODO decode the data into something usable
                request.queue.put_nowait(response.data)
            else:
                request.future.set_result(response)
        else:
            self.delete_request(request)
            request.future.set_result(response)

    def add_request(self, request):
        # TODO we should maybe check if the request_id is unique
        self._requests[request.id_] = request

    def delete_request(self, request):
        del self._requests[request.id_]


class Client:
    """This class represents a connection to a remote Libbitcoin server.

    hostname -- the server DNS name to connect to.
    ports -- a dictionary containing four keys: query/heartbeat/block/tx
    """

    def __init__(self, hostname, ports, settings=ClientSettings()):
        self._hostname = hostname
        self._ports = ports
        self._settings = settings
        self._query_socket = self._create_query_socket()
        self._block_socket = self._create_block_socket()
        self._request_collection = RequestCollection(
            self._query_socket,
            self._settings.loop)

    async def stop(self):
        self._query_socket.close()
        self._block_socket.close()
        return await self._request_collection.stop()

    def _create_block_socket(self):
        socket = self._settings.context.socket(
            zmq.SUB, io_loop=self._settings.loop)
        socket.connect(self.__server_url(self._hostname, self._ports["block"]))
        socket.setsockopt_string(zmq.SUBSCRIBE, '')
        return socket

    def _create_query_socket(self):
        socket = self._settings.context.socket(
            zmq.DEALER, io_loop=self._settings.loop)
        socket.connect(self.__server_url(self._hostname, self._ports["query"]))
        return socket

    async def _subscription_request(self, command, data):
        request = await self._request(command, data)
        request.queue = asyncio.Queue()
        error_code, _ = await self._wait_for_response(request)
        return error_code, request.queue

    async def _simple_request(self, command, data):
        return await self._wait_for_response(
            await self._request(command, data))

    async def _request(self, command, data):
        """Make a generic request. Both options are byte objects specified like
        b"blockchain.fetch_block_header" as an example."""
        request = await Request.create(self._query_socket, command, data)
        self._request_collection.add_request(request)

        return request

    async def _wait_for_response(self, request):
        try:
            response = await asyncio.wait_for(
                request.future,
                self._settings.timeout)
        except asyncio.TimeoutError:
            self._request_collection.delete_request(request)
            return pylibbitcoin.error_code.ErrorCode.channel_timeout, None

        assert response.command == request.command
        assert response.request_id == request.id_
        return response.error_code, response.data

    async def last_height(self):
        """Fetches the height of the last block in our blockchain."""
        command = b"blockchain.fetch_last_height"
        error_code, data = await self._simple_request(command, b"")
        if error_code:
            return error_code, None
        # Deserialize data
        height = struct.unpack("<I", data)[0]
        return error_code, height

    async def block_header(self, index):
        """Fetches the block header by height or integer index."""
        command = b"blockchain.fetch_block_header"
        data = pack_block_index(index)
        error_code, data = await self._simple_request(command, data)
        if error_code:
            return error_code, None
        return error_code, bitcoin.core.CBlockHeader.deserialize(data)

    async def block_transaction_hashes(self, index):
        command = b"blockchain.fetch_block_transaction_hashes"
        data = pack_block_index(index)
        error_code, data = await self._simple_request(command, data)
        if error_code:
            return error_code, None
        data = unpack_table("32s", data)
        return error_code, data

    async def block_height(self, hash_):
        command = b"blockchain.fetch_block_height"
        error_code, data = await self._simple_request(
            command, bytes.fromhex(hash_)[::-1])
        if error_code:
            return error_code, None
        data = struct.unpack("<I", data)[0]
        return error_code, data

    async def transaction(self, hash_):
        command = b"blockchain.fetch_transaction"
        error_code, data = await self._simple_request(
            command, bytes.fromhex(hash_)[::-1])
        if error_code:
            return error_code, None

        transaction = bitcoin.core.CTransaction.deserialize(data)
        return None, transaction

    async def transaction_index(self, hash_):
        """Fetch the block height that contains a transaction and its index
        within that block."""
        command = b"blockchain.fetch_transaction_index"
        error_code, data = await self._simple_request(
            command, bytes.fromhex(hash_)[::-1])
        if error_code:
            return error_code, None

        data = struct.unpack("<II", data)
        return None, data

    async def spend(self, output_transaction_hash, index):
        command = b"blockchain.fetch_spend"
        error_code, data = await self._simple_request(
            command,
            bitcoin.core.COutPoint(
                bytes.fromhex(output_transaction_hash)[::-1],
                index).serialize()
        )
        if error_code:
            return error_code, None

        # An CInPoint is just an other name for COutPoint
        point = bitcoin.core.COutPoint.deserialize(data)
        return None, point

    async def mempool_transaction(self, hash_):
        command = b"transaction_pool.fetch_transaction"
        error_code, data = await self._simple_request(
            command, bytes.fromhex(hash_)[::-1])
        if error_code:
            return error_code, None

        transaction = bitcoin.core.CTransaction.deserialize(data)
        return None, transaction

    async def transaction2(self, hash_):
        command = b"blockchain.fetch_transaction2"
        error_code, data = await self._simple_request(
            command, bytes.fromhex(hash_)[::-1])
        if error_code:
            return error_code, None

        transaction = bitcoin.core.CTransaction.deserialize(data)
        return None, transaction

    async def transaction_pool_transaction2(self, hash_):
        command = b"transaction_pool.fetch_transaction"
        error_code, data = await self._simple_request(
            command, bytes.fromhex(hash_)[::-1])
        if error_code:
            return error_code, None

        transaction = bitcoin.core.CTransaction.deserialize(data)
        return None, transaction

    async def subscribe_address(self, address):
        command = b"subscribe.address"
        decoded_address = decode_address(address)
        error_code, queue = await self._subscription_request(
            command, decoded_address)
        if error_code:
            return error_code, None

        return None, queue

    # TODO this call should ideally also remove the subscription request from
    # the RequestCollection.
    # This call solicits a final call from the server with a
    # `error::service_stopped` error code.
    async def unsubscribe_address(self, address):
        command = b"unsubscribe.address"
        decoded_address = decode_address(address)
        return await self._simple_request(
            command, decoded_address)

    async def broadcast(self, block):
        command = b"blockchain.broadcast"
        return await self._simple_request(command, unhexlify(block))

    async def history3(self, address, height=0):
        command = b"blockchain.fetch_history3"
        decoded_address = decode_address(address)
        error_code, raw_points = await self._simple_request(
            command,
            decoded_address + to_little_endian(height))
        if error_code:
            return error_code, None

        def make_tuple(row):
            kind, tx_hash, index, height, value = row
            return (
                kind,
                bitcoin.core.COutPoint(tx_hash, index),
                height,
                value,
                checksum(tx_hash[::-1].hex(), index),
            )

        rows = unpack_table("<B32sIIQ", raw_points)
        points = [make_tuple(row) for row in rows]

        correlated_points = Client.__correlate(points)

        return None, correlated_points

    async def validate(self, block):
        command = b"blockchain.validate"
        return await self._simple_request(command, unhexlify(block))

    async def transaction_pool_broadcast(self, block):
        command = b"transaction_pool.broadcast"
        return await self._simple_request(command, unhexlify(block))

    async def transaction_pool_validate2(self, transaction):
        command = b"transaction_pool.validate2"
        return await self._simple_request(command, unhexlify(transaction))

    async def balance(self, address):
        error, history = await self.history3(address)
        if error:
            return error, None

        utxo = Client.__receives_without_spends(history)

        return None, functools.reduce(
            lambda accumulator, point: accumulator + point['value'], utxo, 0)

    async def unspend(self, address):
        error, history = await self.history3(address)
        if error:
            return error, None

        return None, Client.__receives_without_spends(history)

    async def merkle_branch(self, hash_, block_index):
        error_code, hashes = self.block_transaction_hashes(block_index)
        if error_code:
            return error_code, None

        return None, merkle_branch(hash_, merkle_tree(hashes))

    async def subscribe_to_headers(self):
        queue = asyncio.Queue()
        asyncio.ensure_future(self._listen_for_headers(queue))
        return queue

    async def _listen_for_headers(self, queue):
        while True:
            frame = await self._block_socket.recv_multipart()
            seq = struct.unpack("<H", frame[0])[0]
            height = struct.unpack("<I", frame[1])[0]
            block_data = frame[2]
            queue.put_nowait(
                (seq, height, bitcoin.core.CBlock.deserialize(block_data)))

    @staticmethod
    def __server_url(hostname, port):
        return "tcp://" + hostname + ":" + str(port)

    @staticmethod
    def __receives_without_spends(history):
        return (point for point in history if 'spent' not in point)

    @staticmethod
    def __correlate(points):
        transfers, checksum_to_index = Client.__find_receives(points)
        transfers = Client.__correlate_spends_to_receives(
            points,
            transfers,
            checksum_to_index
        )

        return transfers

    @staticmethod
    def __correlate_spends_to_receives(points, transfers, checksum_to_index):
        for point in points:
            if point[0] == 0:  # receive
                continue

            spent = {
                "hash": point[1].hash,
                "height": point[2],
                "index": point[1].n,
            }
            if point[3] not in checksum_to_index:
                transfers.append({
                    "spent": spent
                })
            else:
                transfers[checksum_to_index[point[3]]]["spent"] = spent

        return transfers

    @staticmethod
    def __find_receives(points):
        transfers = []
        checksum_to_index = {}

        for point in points:
            if point[0] == 1:  # spent
                continue

            transfers.append({
                "received": {
                    "hash": point[1].hash,
                    "height": point[2],
                    "index": point[1].n,
                },
                "value": point[3],
            })

            checksum_to_index[point[4]] = len(transfers) - 1

        return transfers, checksum_to_index
