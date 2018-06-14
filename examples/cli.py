import asyncio
import sys
import binascii
import bitcoin.core
import pylibbitcoin.client


def block_header(client):
    index = sys.argv[2]
    return client.block_header(int(index))


def last_height(client):
    return client.last_height()


def block_height(client):
    hash = sys.argv[2]
    return client.block_height(hash)


def transaction(client):
    hash = sys.argv[2]
    return client.transaction(hash)


def transaction_index(client):
    hash = sys.argv[2]
    return client.transaction_index(hash)


def block_transaction_hashes(client):
    height = int(sys.argv[2])
    return client.block_transaction_hashes(height)


def spend(client):
    hash = sys.argv[2]
    index = int(sys.argv[3])
    return client.spend(hash, index)


async def subscribe_address(client):
    address = sys.argv[2]
    return await client.subscribe_address(address)


async def _read_from(queue):
    while True:
        print(await queue.get())


def unsubscribe_address(client):
    address = sys.argv[2]
    return client.unsubscribe_address(address)


def broadcast(client):
    # Grab a raw block from https://blockchain.info/block/000000000000000000a7b4999c723ed9f308425708577c76827ade51062e135a?format=hex  # noqa: E501
    # This might seem odd but this is a sanity check a client should probably do.  # noqa: E501
    block = bitcoin.core.CBlock.deserialize(binascii.unhexlify(sys.argv[2]))
    return client.broadcast(binascii.hexlify(block.serialize()))


async def history3(client):
    address = sys.argv[2]
    start_height = 10_000
    return await client.history3(address, start_height)


commands = {
    "last_height": last_height,
    "block_header": block_header,
    "block_height": block_height,
    "transaction": transaction,
    "transaction_index": transaction_index,
    "spend": spend,
    "subscribe_address": subscribe_address,
    "unsubscribe_address": unsubscribe_address,
    "broadcast": broadcast,
    "history3": history3,
    "block_transaction_hashes": block_transaction_hashes,
}


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: %s last_height|block_header|<cmd>" % sys.argv[0])
    command = sys.argv[1]
    if command not in commands:
        sys.exit("Command can be %s" % str.join(", ", iter(commands)))

    # client = pylibbitcoin.client.Client("tcp://127.0.0.1:9999", settings=pylibbitcoin.client.ClientSettings(timeout=5))
    # client = pylibbitcoin.client.Client("tcp://mainnet.libbitcoin.net:9091")

    client = pylibbitcoin.client.Client("tcp://testnet1.libbitcoin.net:19091")

    loop = asyncio.get_event_loop()

    error_code, result = loop.run_until_complete(commands[sys.argv[1]](client))
    print("Error code: {}".format(error_code))
    print("Result: {}".format(result))

    if type(result) == asyncio.queues.Queue:
        loop.run_until_complete(_read_from(result))

    number_of_pending_responses = loop.run_until_complete(client.stop())
    print("Number of pending responses lost: {}".format(number_of_pending_responses))
    loop.close()


if __name__ == '__main__':
    main()
