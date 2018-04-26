import asyncio
import sys
import pylibbitcoin.client
import binascii
import struct


def block_header(client):
    index = sys.argv[2]
    return client.block_header(int(index))


def last_height(client):
    return client.last_height()


commands = {
    "last_height": last_height,
    "block_header": block_header
}


async def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: %s last_height|block_header|<cmd>" % sys.argv[0])
    command = sys.argv[1]
    if command not in commands:
        sys.exit("Command can be %s" % str.join(", ", iter(commands)))

    client = pylibbitcoin.client.Client("tcp://mainnet.libbitcoin.net:9091")

    ec, result = await commands[sys.argv[1]](client)
    # unpack according to
    # https://en.bitcoin.it/wiki/Protocol_documentation#Block_Headers
    version, prev, root, timestamp, bits, nounce = \
        struct.unpack('<I32s32sIII', result)
    print(binascii.hexlify(prev[::-1]).decode('utf8'))
    print(binascii.hexlify(root[::-1]).decode('utf8'))

    client.stop()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
