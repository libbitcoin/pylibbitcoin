import asyncio
import sys
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

commands = {
    "last_height": last_height,
    "block_header": block_header,
    "block_height": block_height,
    "transaction": transaction,
    "transaction_index": transaction_index,
    "spend": spend,
    "subscribe_address": subscribe_address,
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

    ec, result = loop.run_until_complete(commands[sys.argv[1]](client))
    print("Error code: %s" % ec)
    print("Result: %s" % result)

    if type(result) == asyncio.queues.Queue:
        loop.run_until_complete(_read_from(result))

    client.stop()
    loop.close()


if __name__ == '__main__':
    main()
