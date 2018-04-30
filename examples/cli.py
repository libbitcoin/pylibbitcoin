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


commands = {
    "last_height": last_height,
    "block_header": block_header,
    "block_height": block_height,
    "transaction": transaction,
    "transaction_index": transaction_index,
    "spend": spend,
}


async def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: %s last_height|block_header|<cmd>" % sys.argv[0])
    command = sys.argv[1]
    if command not in commands:
        sys.exit("Command can be %s" % str.join(", ", iter(commands)))

    client = pylibbitcoin.client.Client("tcp://mainnet.libbitcoin.net:9091")

    ec, result = await commands[sys.argv[1]](client)
    # print(bitcoin.core.CBlockHeader.deserialize(result))
    # unpack according to
    # https://en.bitcoin.it/wiki/Protocol_documentation#Block_Headers
    # version, prev, root, timestamp, bits, nounce = \
    #     struct.unpack('<I32s32sIII', result)
    # print(binascii.hexlify(prev[::-1]).decode('utf8'))
    # print(binascii.hexlify(root[::-1]).decode('utf8'))
    print("Error code: %s" % ec)
    print(result)
    client.stop()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
