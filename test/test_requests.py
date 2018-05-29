import struct
from binascii import unhexlify
import asynctest
from asynctest import CoroutineMock, MagicMock
import bitcoin.core.serialize
import zmq
import zmq.asyncio

import pylibbitcoin.client

"""
api_interactions has all API calls.
request_id == 2 == b"\x02\x00\x00\x00"
error_code == 0 == b"\x00\x00\x00\x00"
request: [command, request_id, data]
response: [command, request_id, error_code + data]
Note that the response has the error code and the data in one frame!
"""
api_interactions = {
    "last_height": {
        "request": [b"blockchain.fetch_last_height", b"\x02\x00\x00\x00", b""],
        "response": [b"blockchain.fetch_last_height", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + b"\xe8\x03\x00\x00"],  # noqa: E501
    },
    "block_header": {
        "request_with_height": [b"blockchain.fetch_block_header", b"\x02\x00\x00\x00", b'@\r\x03\x00'],  # noqa: E501
        "request_with_hash": [b"blockchain.fetch_block_header", b"\x02\x00\x00\x00", unhexlify("0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c")],  # noqa: E501
        "response": [b"blockchain.fetch_block_header", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + bitcoin.core.CBlockHeader().serialize()],  # noqa: E501
    },
    "block_transaction_hashes": {
        "request_with_height": [b"blockchain.fetch_block_transaction_hashes", b"\x02\x00\x00\x00", b'@\r\x03\x00'],  # noqa: E501
        "request_with_hash": [b"blockchain.fetch_block_transaction_hashes", b"\x02\x00\x00\x00", unhexlify("0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c")],  # noqa: E501
        "response": [b"blockchain.fetch_block_transaction_hashes", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + unhexlify("a"*64 + "b"*64)],  # noqa: E501
    },
    "block_height": {
        "request": [b"blockchain.fetch_block_height", b"\x02\x00\x00\x00", bytes.fromhex("0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c")[::-1]],  # noqa: E501
        "response": [b"blockchain.fetch_block_height", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + struct.pack("<I", 200_000)],  # noqa: E501
    },
    "transaction": {
        "request": [b"blockchain.fetch_transaction", b"\x02\x00\x00\x00", bytes.fromhex("e400712f48693950b78aef3e298b590cfd4bc9a1a91beb0547fb25bc73d220b9")[::-1]],  # noqa: E501
        "response": [b"blockchain.fetch_transaction", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + bitcoin.core.CTransaction().serialize()],  # noqa: E501
    },
    "transaction_index": {
        "request": [b"blockchain.fetch_transaction_index", b"\x02\x00\x00\x00", bytes.fromhex("e400712f48693950b78aef3e298b590cfd4bc9a1a91beb0547fb25bc73d220b9")[::-1]],  # noqa: E501
        "response": [b"blockchain.fetch_transaction_index", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + struct.pack("<I", 200_000) + struct.pack("<I", 1)],  # noqa: E501
    },
    "spend": {
        "request": [b"blockchain.fetch_spend", b"\x02\x00\x00\x00", bitcoin.core.COutPoint(bytes.fromhex("0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09")[::-1], 0).serialize()],  # noqa: E501
        "response": [b"blockchain.fetch_spend", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + bitcoin.core.COutPoint().serialize()],  # noqa: E501
    },
    "transaction_pool_transaction": {
        "request": [b"transaction_pool.fetch_transaction", b"\x02\x00\x00\x00", bytes.fromhex("0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09")[::-1]],  # noqa: E501
        "response": [b"transaction_pool.fetch_transaction", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + bitcoin.core.CTransaction().serialize()],  # noqa: E501
    },
    "transaction2": {
        "request": [b"blockchain.fetch_transaction2", b"\x02\x00\x00\x00", bytes.fromhex("0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09")[::-1]],  # noqa: E501
        "response": [b"blockchain.fetch_transaction2", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + bitcoin.core.CTransaction().serialize()],  # noqa: E501
    },
    "broadcast": {
        "request": [b"blockchain.broadcast", b"\x02\x00\x00\x00", bytes.fromhex("00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38")],  # noqa: E501
        "response": [b"blockchain.broadcast", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + b""],  # noqa: E501
    },
    "history3": {
        "request": [b"blockchain.fetch_history3", b"\x02\x00\x00\x00", b'N\x94.\xc6W\n\xae\x02o\xc1\xac\x88 /\x07\x9e\xcb\x9b\xc3h' + b'\xa8a\x00\x00'],  # noqa: E501
        "response": [b"blockchain.fetch_history3", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + b'\x00\xaa\xdb\x03\xfe\x1bZ\xbc\xc5\x17\xc6CS]\x01\x07R\xbc\xa7\x8d\x03\x99\x89<\x0e\x14/\xda7\x9aB\xfa\xcd\x00\x00\x00\x00d\x02\x08\x00\x80J]\x05\x00\x00\x00\x00\x00\n"~\x99\r\xbc\x89\xbe\xde\xb6N\x06w?\xb6\xfa\xee\xab\xb2\x84\xa0\xf4\xe7\x88xnG\xcf\xc4\xdf\x05\x1f\x05\x00\x00\x00_\x02\x08\x00\x00\xb4\xc4\x04\x00\x00\x00\x00\x00\xf8\xb8\n\xb4\x14\x1c|\xc0\xe5$#\x16z\xa4\x91\xa3\n\xff\x05\xd3\xa3\xd6\xd2\x18\x99d\x0fAR\n?\x87\x00\x00\x00\x00\xe5\x01\x08\x00\x00\xb4\xc4\x04\x00\x00\x00\x00\x01\x16&V\x9c\xa4\xa0\x0b\xc7\x81%\x1cb\t\xd542\xc3\'\xf5\x1e.Lb\x91\xe7\x995\xc7J\x08\x00\n\x00\x00\x00\x00\xe0\x01\x08\x00\x00\x00\xbb\xc4\xe3\xa7\x87\xc4\x00Fu\x9f\xb7c\xc0\xfdzpmW1o@%N\xb6p\n\xdcL\xfc\x9c\xa1\xc9nH\xc5z\x12b\x96\x03\x00\x00\x00\xb9\x01\x08\x00\x00\xb4\xc4\x04\x00\x00\x00\x00\x00\x9e\xd2\\\x1a\n(u\x97\xc8`K\x81\xbd\xc9\xaa\x08\xc0\x8e\xfcV\x19*\xca\x8b\x02w]z7\xf9g\xed\x00\x00\x00\x00\xb4\x01\x08\x00\x00\xb4\xc4\x04\x00\x00\x00\x00\x00\x18G\xf4\xd4\xf51\xfc\xde\xec\xedD\xdf\x04\x89\'w:\xbds(\\\x1ek;2\x15\xcd\xca\x1fK\xd4\x0c\x03\x00\x00\x00\xa3\x01\x08\x00\x80\x1d,\x04\x00\x00\x00\x00\x00:&\x90}\xf2!\x96\x1b\x9b\x16U\xd22I\x05\xd3\xdbR\xe2\xa4R\x99\xc7\x82\xe7\x19*\xf0\xc9L3>\x02\x00\x00\x00\x8e\x01\x08\x00\x80\x1d,\x04\x00\x00\x00\x00\x00:\xc9a\x15\\\xe9c\xd9/\x98\xef\xdeqM\xbb\xc4\xe3\xa7\x87\xc4\xafN:c\xd9)t\xe30\x89\x16\x1c\x00\x00\x00\x00j\x01\x08\x00\x00\xe1\xf5\x05\x00\x00\x00\x00\x00\xf4\x19\x9e6\x02\xc7\'*>\x16\xd3\xe5\xd8\x89\x12\xb4\xdf\x84\x7fY\xb7\x15})wp\xb4\x8e\x96Vk\xa7\x03\x00\x00\x00Y\x01\x08\x00\x80\x1d,\x04\x00\x00\x00\x00\x00\x99\x89<\xa0\x8b\xeb\x90F\x16]\xf0\xbb\xe6\xef\x8bb\xd0\xa1C\x0fI\xf1\x13\x8d\rK\x9dUD\x1bR\xcf\x01\x00\x00\x00N\x01\x08\x00\x80\x1d,\x04\x00\x00\x00\x00\x00=G|}\xe2F\xac\x976<\xd1\xc0<\xf1\xa0d{m#\x80\x17\x11\x7f<\xd2\xb0\xcb4f\xb4\xcd^\x00\x00\x00\x00=\x01\x08\x00\x80\x1d,\x04\x00\x00\x00\x00\x00\x0e\xd8\x15\xd8B\xa7\x0f\xd6G\xf7T\x97+:\x83\xa89\xd5\x17\xaco\xa3&\xc0\xb1\xdd4"\x81\xecc\xc4\x00\x00\x00\x004\x01\x08\x00\x80\x1d,\x04\x00\x00\x00\x00\x00n\xd4 s\xb2\n\xaf\x07\xafDh\x0b\xe4\xdd<E\xf9\xd9\xc56\xca\xd1[\xab\\L\xa0\xd87m\x16\n\x01\x00\x00\x00\x15\x01\x08\x00\x00\x87\x93\x03\x00\x00\x00\x00\x00\xa6\xd6\x13\x97\xd3\x98\x05\xe7\x9b\xe4\x8c\x9b!\x98O<\xb7\xd0\xf15X\xee\x1eQ\x06.\x87\xe3\xedu\x90\xc3\x00\x00\x00\x00\x8d\x00\x08\x00\x00\x87\x93\x03\x00\x00\x00\x00\x00\xacC\xea\x10\x94\xba\xf8~L\x95c\xf6\xe6\xd6\xbc\xd7\xfc\x0f0\x938\xdd\xbf\xdf\xf7\xdd\xb2b\xbdi\xabh\x03\x00\x00\x00}\x00\x08\x00\x80\x1d,\x04\x00\x00\x00\x00\x00l%\xc5\x8d\xc1\xeb\xda\xa0\'\xd6i\xde=Me!\x80L\xb6\xb9*\xcaRl\x91tZh\x90i+\x14\x02\x00\x00\x00s\x00\x08\x00\x80\x1d,\x04\x00\x00\x00\x00\x00("\xb0\xfe\xd5\x05\x9b\x0b\xc9\xbe\x03\xd3\x92\x05!\xb6J\x91\xbd\x80T\xc3\x91\xa4B3\x17\xcc\x9c2\xdb>\x00\x00\x00\x00j\x00\x08\x00\x00\x87\x93\x03\x00\x00\x00\x00\x00\xed!P\x18\'\x97\xd4\xaa3a>\xc2\xb2\xfb1\x9ebA,\xaf\xcb\x95r\xd7%5\xf7\x9ab\x92K\xad\x00\x00\x00\x00M\x00\x08\x00\x00\x87\x93\x03\x00\x00\x00\x00\x00\x01\xf2\xe2\x1b\x9ed\xd5\xc8\\b\x93\x15S\xe7\x14\x0b\x93Gb\xceMW\xbcs\xb9"\x92\xe6f\xb4\x8c3\x01\x00\x00\x00:\x00\x08\x00\x00\x87\x93\x03\x00\x00\x00\x00\x01W\xc1\xf3\x129\xe9\nup\x0f\xca<\xdcR\xb6\xec\x8edu\x08!\xb0\xa3\xe7\xfc1\xdc4\x9b\x06>\xca\x07\x00\x00\x00\xd6\xff\x07\x00\x00\x004f\x06\xfd\x1c\xbf\x00b&hB\xef\x99\xa6R!\x15\x12\x0e\x84=4f\x06\xfd\x1c\xbf\xeex\x80\x82Zz\x17\x0c\x98`V\xde\x00\x00\x00\x00\xb1\xff\x07\x00\x00\x87\x93\x03\x00\x00\x00\x00\x01(\xf7"\x8fq\xd2g\\\xfbw\xf2\xf3\x9b7\xc5\xf8\xb9\xac\x9f]\x15\xaa\xa1(\xdf\xcc\xcd\xcc\xd8\xbe1~\x04\x00\x00\x00\x94\xff\x07\x00\x02\x80m\xb7\x9c!\xf8\xbf\x01+TH\xe3\x95Q\xe5\x97\x1b3\xc0\xa5\x92<\x96oz,e\xd5\xec\x8f4\x96\'\xdd|\xb0\x87B\xbe\xb6\xe1\x00\x00\x00\x8f\xff\x07\x00\x01\x00\xf6\x80*/8\x00\x00w2\xe0\xc6\x17\x0b\x98\xd8\xcf\xad\x0e}\r\xcdm\xb7\x9c!\xf8\xbflr]\xfe\x1f\xaf\x940\xd0.\xb5\xea\x02\x00\x00\x00\x87\xff\x07\x00\x00\x87\x93\x03\x00\x00\x00\x00\x01;8\x13\xd2\x8a\r \x98:/c\x06J\x90\xd97\xb0\xf6\xe1\xa9\x1b\xf9\x10\xd2\xcc\xc0\xb3\xb3\xf0P\xc5|\x0e\x01\x00\x00\x81\xff\x07\x00\x00\x00v\x1c\xea\xf8S\xa6\x00^C\xa95&\t\x0c\xd2\xddV\x8d\xa7\x929\xf6\x80*/8\x001\x82\xe1\xe0\x87\\\xe8Pn\xb7\xda\xe8\x01\x00\x00\x00\x81\xff\x07\x00\x00\x87\x93\x03\x00\x00\x00\x00\x01\xfa\xe7E5\xd6b\x0c\xfcuB\xbfd\x137\xb8E\xf6y\xca\x1d\x0c8\xd2\x8f#\xb8\x82\xab\xafV\xc6\xecy\x00\x00\x00z\xff\x07\x00\x01\x80u\xdb\x92~\xe0\x16\x00\xd9R\xce-\xbd\xbd\xa2\xa3w\x93/\xd5\xf3\x7fv\x1c\xea\xf8S\xa6\x8d\xd1^\xc7W\x16*B{\xa6\x90\xa1\x00\x00\x00\x00x\xff\x07\x00\x00\x87\x93\x03\x00\x00\x00\x00\x01s\xb7h<\xc8\xc9\xa7Zi\x07q:FT\xf8G\x8fkX&\xb10\xc3\xd7\xc1jqQz\x8d\xb5\x0b\xea\x00\x00\x00q\xff\x07\x00\x02\x00\xc3\xaa\xb1\x9a[\xe8\x01s\xb7h<\xc8\xc9\xa7Zi\x07q:FT\xf8G\x8fkX&\xb10\xc3\xd7\xc1jqQz\x8d\xb5\x0b\xd7\x00\x00\x00q\xff\x07\x00\x01\x80\xc3O\x85\xad\xfe\xbb\x00\xfa{+\xbf\xb1\xc8\xce\'\xb6*q\xa9\xde&\xc3\xaa\xb1\x9a[\xe8:\x8b\x08\xb7\x06\xb2\xe8\xcf\xf6\x1b,\x12\x02\x00\x00\x00j\xff\x07\x00\x00\x87\x93\x03\x00\x00\x00\x00\x00\xe7\x93\x9a\x8eS\xc9v=\xdd\xbfmR7\xce\xc3O\x85\xad\xfe\xbb_\xd0f\x92\xb36\ttN\xd3\xeeT\x01\x00\x00\x00g\xff\x07\x00\x00\x87\x93\x03\x00\x00\x00\x00\x00\xfaiS{m\xc0c^\x9e\x92\t\xbb\xe1\xa5u\xdb\x92~\xe0\x16\xfd=\xf7\xe9h\xdf\xc3\x9e\x13\xcb\x90\xae\x01\x00\x00\x00R\xff\x07\x00\x00\x87\x93\x03\x00\x00\x00\x00\x014\xdd\xbbs\x86]\x8a\x93t\x14"l&\x08\x1d\xd9\x00\xef\x1e\xf2\xd9\xb0\xdf!%9\xc6a\xc2\x99/AM\x00\x00\x00F\xff\x07\x00\n\x80o\xde\xbd1<\xed\x01\x11W\xc1\xcb]k8\x86\xe4\xc1W\xd9\xd5\x06\x98\xd1\x91!\xd3C\t\xd2\xb6\xca2\xd3\x98q\x0f\x829\x98\x10\x00\x00\x00C\xff\x07\x00\x02\x80`\xa9n\xc7;%\x01\x11W\xc1\xcb]k8\x86\xe4\xc1W\xd9\xd5\x06\x98\xd1\x91!\xd3C\t\xd2\xb6\xca2\xd3\x98q\x0f\x829\x98\x02\x00\x00\x00C\xff\x07\x00\x00\x80\xc0\xca\xc6Y\xd9\xbe\x01\x1f@:\xed*5I\x8d\xf3-\x19\x13\x0e\x88\xe7\x0e\xe5i&\x8d\xcd\xcf\xa3\xa9y1\xf0\x0f\xb2\xdc\xd7\xf0\x12\x00\x00\x00>\xff\x07\x00\x00\x00F\xd0\x18\xef\xf6|\x00\x1ciu\xe6t\xbd:W5\x1c\x15\x9f\x9d\xe3o\xde\xbd1<\xed\x15\x10\x81ZB\x8c\xda\t\xb9\x1a.-\n\x00\x00\x00>\xff\x07\x00\x00\x87\x93\x03\x00\x00\x00\x00\x00s\x85+\xa8\x82R\x14\x96`\xa6\xda\x18I\xdd`\xa9n\xc7;%L\xb8TW[eg\xc8\x9dO\xec\x9f\x02\x00\x00\x00:\xff\x07\x00\x00\x87\x93\x03\x00\x00\x00\x00\x00\x17:\xdf\xa5i*\xd0\xcb\xe9\xf7\x1e,(\xe5\xc0\xca\xc6Y\xd9\xbeU1\x0e\xed\xed\x03-q\xd5y\x13l\x00\x00\x00\x00\x1b\xff\x07\x00\x00\x87\x93\x03\x00\x00\x00\x00\x00\x8d\x9e\'\xb9\xcc\xabl\x95\xe4\xfcSu{\tF\xd0\x18\xef\xf6|\xd2\x84\x85~2\xc5\x84k!\x96\xf2\xdd\x00\x00\x00\x00\x10\xff\x07\x00\x00\x87\x93\x03\x00\x00\x00\x00\x01\xd1\xdf\x98\x1f\xdb\xc3I\x088\xcb\xed\x9d+\xfb\x11\xeb5\xdfk\x9e:L8K\xeb\xdf\xf0\xd4\xbd\n\xd0\x99N\x00\x00\x00\xdb\xfe\x07\x00\x00\x00 \r\xc4\xc1\xff\x87\x01\xe2\x0f\xf0\xd9\x9f\x1a\xe4vu\xfaB\x1cYN\xcf\xda\xe6\xe9\x97\x9ee\xd7a\xdcxN\xaf\xf9\xc5fU\xb9\x1b\x00\x00\x00\xd9\xfe\x07\x00\x00\x00\xc8\xaf\xdfH\xd7\xbf\x00p\xa3\xbeWss\xf0\x92\xc0p\x13\x95wA \r\xc4\xc1\xff\x87Y\xd8\xc91%\xc5$\x8a\x8e\x90\x02\xbc\x00\x00\x00\x00\xd4\xfe\x07\x00\x00\x87\x93\x03\x00\x00\x00\x00\x017\xd2C\x8b\xf8<BF\x06\xbd\xa0\x08\xa2r\xff\xd9`{\xca\xc4\tJpM\x03_\xe4\x00\x89h~[\x84\x01\x00\x00\xc7\xfe\x07\x00\x01\x808\xa7\xf3\xc0\xbeg\x00\xceY\x08\xb9k\xc6:\x83\xbf]\xfa\xbe\xf7\x18\xc8\xaf\xdfH\xd7\xbf\x93\xfa\xde\x1c\xdb\x8c\n\xefp\xd0=\'\x00\x00\x00\x00\xbe\xfe\x07\x00\x80\xf0\xfa\x02\x00\x00\x00\x00\x01S\xe5?e9L\\\x8fn\x16\xe80V\xe3\xbe\xf1G\xedrU\x93\xcf\x86,<\x18\x92\xb6X\xc9\xd9\xb3\x04\x00\x00\x00\xb8\xfe\x07\x00\x01\x00]\xacCD6\xc0\x00\xdd~\xb7LY9\x93\xf6\xae\xea\xd1Tz\xdc8\xa7\xf3\xc0\xbegYT\x06\xd4\x84\xbd\xc3\x1d_f\xe5\n\x01\x00\x00\x00\xb6\xfe\x07\x00\x80\xf0\xfa\x02\x00\x00\x00\x00\x00.\xf7B}R\xa3\xcd}\xd4;\xbe\\Pt]\xacCD6\xc00\xa1Q$V#G\xe8\xd0\x10\xd3\x9f\x01\x00\x00\x00\xa8\xfe\x07\x00\x80\xf0\xfa\x02\x00\x00\x00\x00\x012~\x9b@\xec\xcaFC\x86\x96,f&\xa1\x9fr\xd9\xd4\xd2\x10N\xba):\xbe<\xbb~\x149\xb5Y\x1d\x00\x00\x00J\xfe\x07\x00\x00\x00N\xb7\x9a\xcb\xdb!\x01\xc4\xcd\x9b~W\xb1e\x9a\xc9\xfb\xd1\x93\xea\x83\x91\x00\x8d\x11\x1cV]\x9a\xac}&\xa4"`\x1f\xdf\xe0\xb4\r\x00\x00\x00/\xfe\x07\x00\x00\x00Y\x9e6V\xc4p\x01T\x0e\x17P\xe3X\x19\x0b\xcc\x8a0\xcc\x08"\xd3\xd6k#n\xc8\x07_\xbb\xb8\x05G\xde\xdd\xe5:\xe5\x0e\x1f\x01\x00\x00.\xfe\x07\x00\x00\x80@\x13?\xad"\x9c\x00/\x00V\xf9:{f\xe4c\xcfoY\xb0LN\xb7\x9a\xcb\xdb!W\xc4^p\xa0\x08CO\xae\xc0a\xc8\x00\x00\x00\x00.\xfe\x07\x00\xa0\\\xf6\x02\x00\x00\x00\x00\x01\xe9}d\x8fp\xa9\xd9t\xde\xa0\x88A\xeb\xdd\xdb\xbf\xcfe#\x98J\xb6yz\xfc\xf4w\xd0oTr f\x00\x00\x00\x10\xfe\x07\x00\x00\x00!\xfb\xf2\x00\xf2\x04\x01+=\x0ev\xcc\xb0\xf7\x91\x99\x17 1Df\xfcDN\x14\x85<\x03x\xb1\\\x18\xb6\xb5{*+\\\xe7x\x00\x00\x00\x0f\xfe\x07\x00\x00\x80\x9fAx\xbb\xb8\n\x00v8\x13\xa32\x1c\xb6\xf6\xf2D\xc3\xfb\x93\xcd@\x13?\xad"\x9c\xfbf\xde{\x0b,\xfe\x8dX\x86m\xd7\x00\x00\x00\x00\x0b\xfe\x07\x00\xe0\xa7B\x03\x00\x00\x00\x00\x01\xa5\xd9>\x1f\x82wI\x1f\xbb41\x1eL\xb2\xaa\xb9\xa0\xa7f\xc8=m).\xa6\xdeQ#\x0c\xe1\x8b\x16\n\x00\x00\x00\t\xfe\x07\x00\x00\x80\xd1\x08+\xce\xba\x83\x00,\x98\x82\x92\x0bn\x04y1\xc3!\xb0EwY\x9e6V\xc4ps\xa3\xd4\x1f!\x1eI7\xc9D1\xfe\x00\x00\x00\x00\x00\xfe\x07\x00 w\xfc\x02\x00\x00\x00\x00\x01b\x10\xfezl\x04\x0b\xdb\xdc\xf3\x0b\xc6\xa4\x00x$\x0c\x85\xc6C=\x06\xf4\x02\xdd\x06\xa8\x8eC\x8b^\x92 \x01\x00\x00\xe0\xfd\x07\x00\x00\x00\xe9\x8f\xbdnb\x01\x00\xadz\x99\xb9PE\xb79\xe6\x00\xe4\xaf\x88\r\xe9\x8f\xbdnb\x01\xc0\xba\x0b\x92W\xe0\x91(\x85k\xcfB\x00\x00\x00\x00\xda\xfd\x07\x00\xc0\xf4\xc0\x02\x00\x00\x00\x00\x009\xb2-JG\x7fQ\x04N\x97\x02T\xd7\x8e\x9fAx\xbb\xb8\n\x15\x93\x95:\x0fC\xbf\x8b\xb4VxB\x00\x00\x00\x00\xd2\xfd\x07\x00\x00\xd6\xf4\x02\x00\x00\x00\x00\x00\x10\xafph\x18\x91;i-\x01\xad\xd2m\xa5\xd1\x08+\xce\xba\x83\x82\xe5\x13\xec\xebAS\xc0\x08*\x1eg\x00\x00\x00\x00\xbb\xfd\x07\x00\x80$\xa5\x01\x00\x00\x00\x00\x00\x81\xd4\xc0\x0f\x12L73,~l\xbb"Z!\xfb\xf2\x00\xf2\x04\x80\x89H\x86\xd4\xa2\x07\n\xa6\x19*=\x00\x00\x00\x00\xb4\xfd\x07\x00\x00\x1c\x19\x02\x00\x00\x00\x00\x01+,\xcc\xbc\xa8\x94\xd6\x8fH\x8a\'2\xa7Y\x06\xc9df\xd4\xa5\xa2\xa7\xd2\xda}\x99\x13#\x82\xa5\xe9\'\x1b\x00\x00\x00l\xfd\x07\x00\x00\x80$\x9bj\xb7\x16v\x01\xb4GvB\x9a\xadL\xfc\xa9-S\x8e\xdc\xd6\x8bf\xb0\xb3\xdd9\xb1|\xca\xa4\x04\x11\x17:\xb2\x8fH\x01\x03\x00\x00\x00-\xfd\x07\x00\x00\x80\xc8O\x88R\xd9\xa8\x00\xce\x88\t\x84\xd1\x07\xc2\xfa\xa3,4\xbf\xfd\xe6$\x9bj\xb7\x16v\xec|\x1a\xea\r\xd6D\xbb\x8a\xa0o\x81\x00\x00\x00\x00\xc5\xfc\x07\x00\x80\xf0\xfa\x02\x00\x00\x00\x00\x00L\xd5\xcf\xcc\xe4n^\x97\xec\xec\xb3\x83\x14\x83\xc8O\x88R\xd9\xa8\x8e\xcd\xb2mmfg2g\xff|~\x00\x00\x00\x00\xc0\xfc\x07\x00\x80\xf0\xfa\x02\x00\x00\x00\x00\x01\xf7\xc6\x19zv\':.\xfd\xc8&u\x16DE\xbbD!\xef\x1d\xd1y\x82h\x01N\xac\xd7SiY\xa4\x15\x00\x00\x00\xbd\xfc\x07\x00\x00\x00\xd5M\xca\xee~u\x01:tW\xc9\xc5\xeb\xf7L\xeb\xb9\xe7\xf7\x88\x0b2S\x83S\xfc\xf1\x8aJ\xb1#\x80O\xc6\xa51\xf9\x8c\x95\x00\x00\x00\x00\x8a\xfc\x07\x00\x00\x00\xd4\x8bT\xe1w\xe4\x00ZK7\xda\xc7\'\xa6\x1cZR\xf0\x92\nt\xd5M\xca\xee~u\xd5\xb5?\xeeRA\xa1\x0f"\xd4v\x17\x00\x00\x00\x00\x89\xfc\x07\x00\x80\xf0\xfa\x02\x00\x00\x00\x00\x00\x00\xc6\x878\x89\x1c\xf3\x8b\xfe@?\xd3\xfdN\xd4\x8bT\xe1w\xe4U\x05\xdf\xdd\xe8D\x08\xa92\xd1M\xb2\x00\x00\x00\x00\x84\xfc\x07\x00\x80\xf0\xfa\x02\x00\x00\x00\x00\x01\xd3O\x82\x8e\xc7\xfa]\x8e\xa8\x150\xca\x8f\xc0\x97\xa0A\xa9\x1a\xea\xb0\x968{\x1d\xc7\xd9\xc0u\xafM\xb2\x0f\x00\x00\x00F\xfc\x07\x00\x00\x801\xff\x95`\x98\xfa\x01\xd3O\x82\x8e\xc7\xfa]\x8e\xa8\x150\xca\x8f\xc0\x97\xa0A\xa9\x1a\xea\xb0\x968{\x1d\xc7\xd9\xc0u\xafM\xb2\x0c\x00\x00\x00F\xfc\x07\x00\x00\x00\x8e\x141\xfa\x0c\x9c\x00b\xfb\xe2\xd6\xfdQ\x9a*f\x9e}S\xe7\xc01\xff\x95`\x98\xfa7\xa903\x84p\xe6\x13\xdb\x96\xa3M\x00\x00\x00\x001\xfc\x07\x00\x80\xf0\xfa\x02\x00\x00\x00\x00\x00V\x11\x1a\x02Og\x11\xa9\x8c\x85\xaa\xfb\xe7&\x8e\x141\xfa\x0c\x9cJk"\x83/\xec\x03!\x96\x1b^\xac\x00\x00\x00\x00&\xfc\x07\x00\x80\xf0\xfa\x02\x00\x00\x00\x00\x00\x9e\x98\xb1\x0c\x80\x0e\\n\xc0c\x83\xa9\xb2nD(\xfaA\x7f\x10\x998\xe8"\xfc%\xd1\xda\xba\x95\xb7\xf5\x00\x00\x00\x00\xef\xf1\x07\x00@B\x0f\x00\x00\x00\x00\x00\x00\xac3\xbd\xfcq\xfe.\xb2&\xc7\xafP!\t\x1b\x93@\x8c\x9c\xfaL=\xce\x9d\xb1\xc3\xc3\xa6\xa3a\x8cW\x00\x00\x00\x00b\xf1\x07\x00\xa0\x86\x01\x00\x00\x00\x00\x00'],  # noqa: E501
    },
    "validate": {
        "request": [b"blockchain.validate", b"\x02\x00\x00\x00", bytes.fromhex("00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38")],  # noqa: E501
        "response": [b"blockchain.validate", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + b""],  # noqa: E501
    },
    "transaction_pool_broadcast": {
        "request": [b"transaction_pool.broadcast", b"\x02\x00\x00\x00", bytes.fromhex("00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38")],  # noqa: E501
        "response": [b"transaction_pool.broadcast", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + b""],  # noqa: E501
    },
    "transaction_pool_validate2": {
        "request": [b"transaction_pool.validate2", b"\x02\x00\x00\x00", bytes.fromhex("00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38")],  # noqa: E501
        "response": [b"transaction_pool.validate2", b"\x02\x00\x00\x00", b"\x00\x00\x00\x00" + b""],  # noqa: E501
    },
}

# Make sure the random ID is static
pylibbitcoin.client.create_random_id = lambda: 2


def client_with_mocked_socket():
    pylibbitcoin.client.RequestCollection = MagicMock()

    mock_zmq_socket = CoroutineMock()
    mock_zmq_socket.connect.return_value = None
    mock_zmq_socket.send_multipart = CoroutineMock()

    mock_zmq_context = MagicMock(autospec=zmq.asyncio.Context)
    mock_zmq_context.socket.return_value = mock_zmq_socket

    settings = pylibbitcoin.client.ClientSettings(
        context=mock_zmq_context,
        timeout=0.01)

    return pylibbitcoin.client.Client('irrelevant', settings)


def raw_response_to_return_type(response):
    resp = pylibbitcoin.client.Response(response)
    return resp.error_code, resp.data


class TestLastHeight(asynctest.TestCase):
    def test_correctness_of_request(self):
        c = client_with_mocked_socket()

        self.loop.run_until_complete(c.last_height())

        c._socket.send_multipart.assert_called_with(
            api_interactions["last_height"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["last_height"]["response"]))

        error_code, height = self.loop.run_until_complete(c.last_height())
        self.assertIsNone(error_code)
        self.assertEqual(height, 1000)


class TestBlockHeader(asynctest.TestCase):
    def test_correctness_of_request_with_height(self):
        c = client_with_mocked_socket()

        self.loop.run_until_complete(c.block_header(200_000))

        c._socket.send_multipart.assert_called_with(
            api_interactions["block_header"]["request_with_height"]
        )

    def test_correctness_of_request_with_hash(self):
        c = client_with_mocked_socket()

        header_hash_as_string = \
            "0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c"
        self.loop.run_until_complete(c.block_header(header_hash_as_string))

        c._socket.send_multipart.assert_called_with(
            api_interactions["block_header"]["request_with_hash"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["block_header"]["response"])
        )

        error_code, block = self.loop.run_until_complete(
            c.block_header(200_000))

        self.assertIsNone(error_code)
        self.assertIsInstance(block, bitcoin.core.CBlockHeader)


class TestBlockTransactionHashes(asynctest.TestCase):
    def test_block_transaction_hashes_by_hash(self):
        c = client_with_mocked_socket()

        header_hash_as_string = \
            "0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c"
        self.loop.run_until_complete(
            c.block_transaction_hashes(header_hash_as_string))

        c._socket.send_multipart.assert_called_with(
            api_interactions["block_transaction_hashes"]["request_with_hash"]
        )

    def test_block_transaction_hashes_by_height(self):
        c = client_with_mocked_socket()

        self.loop.run_until_complete(
            c.block_transaction_hashes(200_000))

        c._socket.send_multipart.assert_called_with(
            api_interactions["block_transaction_hashes"]["request_with_height"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["block_transaction_hashes"]["response"])
        )

        error_code, hashes = self.loop.run_until_complete(
            c.block_transaction_hashes(200_000))

        self.assertIsNone(error_code)
        self.assertEqual(len(hashes), 2)


class TestBlockHeight(asynctest.TestCase):
    def test_block_height(self):
        c = client_with_mocked_socket()
        header_hash_as_string = \
            "0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c"

        self.loop.run_until_complete(
            c.block_height(header_hash_as_string))

        c._socket.send_multipart.assert_called_with(
            api_interactions["block_height"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["block_height"]["response"])
        )
        header_hash_as_string = \
            "0000000000000000000aea04dcbdd6a8f16e7ddcc9c43e3701c99308343f493c"

        error_code, height = self.loop.run_until_complete(
            c.block_height(header_hash_as_string))

        self.assertIsNone(error_code)
        self.assertEqual(height, 200_000)


class TestTransaction(asynctest.TestCase):
    def test_transaction(self):
        c = client_with_mocked_socket()

        transaction_hash = \
            "e400712f48693950b78aef3e298b590cfd4bc9a1a91beb0547fb25bc73d220b9"
        self.loop.run_until_complete(
            c.transaction(transaction_hash))

        c._socket.send_multipart.assert_called_with(
            api_interactions["transaction"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["transaction"]["response"])
        )
        transaction_hash = \
            "e400712f48693950b78aef3e298b590cfd4bc9a1a91beb0547fb25bc73d220b9"

        error_code, transaction = self.loop.run_until_complete(
            c.transaction(transaction_hash))

        self.assertIsNone(error_code)
        self.assertIsInstance(transaction, bitcoin.core.CTransaction)


class TestTransactionIndex(asynctest.TestCase):
    def test_transaction_index(self):
        c = client_with_mocked_socket()
        transaction_hash = \
            "e400712f48693950b78aef3e298b590cfd4bc9a1a91beb0547fb25bc73d220b9"
        self.loop.run_until_complete(
            c.transaction_index(transaction_hash))

        c._socket.send_multipart.assert_called_with(
            api_interactions["transaction_index"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["transaction_index"]["response"])
        )
        transaction_hash = \
            "e400712f48693950b78aef3e298b590cfd4bc9a1a91beb0547fb25bc73d220b9"

        error_code, height = self.loop.run_until_complete(
            c.transaction_index(transaction_hash))

        self.assertIsNone(error_code)
        self.assertEqual(height, (200_000, 1))


class TestSpend(asynctest.TestCase):
    def test_spend(self):
        c = client_with_mocked_socket()
        transaction_hash = \
            "0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09"
        index = 0
        self.loop.run_until_complete(
            c.spend(transaction_hash, index))

        c._socket.send_multipart.assert_called_with(
            api_interactions["spend"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        transaction_hash = \
            "0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09"
        index = 0
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["spend"]["response"])
        )

        error_code, point = self.loop.run_until_complete(
            c.spend(transaction_hash, index))

        self.assertIsNone(error_code)
        self.assertIsInstance(point, bitcoin.core.COutPoint)


class TestTransactionPoolTransaction(asynctest.TestCase):
    def test_transaction_pool_transaction(self):
        c = client_with_mocked_socket()

        transaction_hash = \
            "0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09"
        self.loop.run_until_complete(
            c.mempool_transaction(transaction_hash))

        c._socket.send_multipart.assert_called_with(
            api_interactions["transaction_pool_transaction"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()

        transaction_hash = \
            "0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09"
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["transaction_pool_transaction"]["response"])
        )

        error_code, transaction = self.loop.run_until_complete(
            c.mempool_transaction(transaction_hash))

        self.assertIsNone(error_code)
        self.assertIsInstance(transaction, bitcoin.core.CTransaction)


class TestTransaction2(asynctest.TestCase):
    def test_transaction2(self):
        c = client_with_mocked_socket()

        transaction_hash = \
            "0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09"
        self.loop.run_until_complete(
            c.transaction2(transaction_hash))

        c._socket.send_multipart.assert_called_with(
            api_interactions["transaction2"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()
        transaction_hash = \
            "0530375a5bf4ea9a82494fcb5ef4a61076c2af807982076fa810851f4bc31c09"
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["transaction2"]["response"])
        )

        error_code, transaction = self.loop.run_until_complete(
            c.transaction2(transaction_hash))

        self.assertIsNone(error_code)
        self.assertIsInstance(transaction, bitcoin.core.CTransaction)


class TestBroadcast(asynctest.TestCase):
    def test_correctness_of_request(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        self.loop.run_until_complete(c.broadcast(block))

        c._socket.send_multipart.assert_called_with(
            api_interactions["broadcast"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["broadcast"]["response"])
        )

        error_code, _ = self.loop.run_until_complete(
            c.broadcast(block))

        self.assertIsNone(error_code)


class TestHistory3(asynctest.TestCase):
    def test_correctness_of_request(self):
        c = client_with_mocked_socket()

        address = "mngSWw2NC9M1ctqZQxz65DwVomCjm7TWPJ"
        self.loop.run_until_complete(c.history3(address, 25_000))

        c._socket.send_multipart.assert_called_with(
            api_interactions["history3"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()

        address = "mngSWw2NC9M1ctqZQxz65DwVomCjm7TWPJ"
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["history3"]["response"])
        )

        error_code, points = self.loop.run_until_complete(
            c.history3(address))

        self.assertIsNone(error_code)
        self.assertEqual(len(points), 49)
        receive_wo_spent = points[0]
        self.assertEqual(receive_wo_spent["received"]["index"], 0)
        self.assertEqual(receive_wo_spent["received"]["height"], 524900)
        self.assertIsNotNone(receive_wo_spent["received"]["hash"])
        self.assertEqual(receive_wo_spent["value"], 90000000)
        self.assertNotIn("spent", receive_wo_spent)

        receive_w_spent = points[-3]
        self.assertIn("spent", receive_w_spent)


class TestValidate(asynctest.TestCase):
    def test_correctness_of_request(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        self.loop.run_until_complete(c.validate(block))

        c._socket.send_multipart.assert_called_with(
            api_interactions["validate"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["validate"]["response"])
        )

        error_code, _ = self.loop.run_until_complete(
            c.validate(block))

        self.assertIsNone(error_code)


class TestTransactionPoolBroadcast(asynctest.TestCase):
    def test_correctness_of_request(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        self.loop.run_until_complete(c.transaction_pool_broadcast(block))

        c._socket.send_multipart.assert_called_with(
            api_interactions["transaction_pool_broadcast"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["transaction_pool_broadcast"]["response"])
        )

        error_code, _ = self.loop.run_until_complete(
            c.transaction_pool_broadcast(block))

        self.assertIsNone(error_code)


class TestTransactionPoolValidate(asynctest.TestCase):
    def test_correctness_of_request(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        self.loop.run_until_complete(c.transaction_pool_validate2(block))

        c._socket.send_multipart.assert_called_with(
            api_interactions["transaction_pool_validate2"]["request"]
        )

    def test_response_handling(self):
        c = client_with_mocked_socket()

        block = "00000020a15e218f5f158a31053ea101b917a6113c807f6bcdc85a000000000000000000cc7cf9eab23c2eae050377375666cd7862c1dfeb81abd3198c3a3f8e045d91484a39225af6d00018659e5e8a0101000000010000000000000000000000000000000000000000000000000000000000000000ffffffff64030096072cfabe6d6d08d1c2f6d904f4e1cd10c6558f8e5aed5d6a89c43bb22862464ebb819dd8813404000000f09f909f104d696e6564206279206a6f73656d7372000000000000000000000000000000000000000000000000000000000000000000007f06000001807c814a000000001976a914c825a1ecf2a6830c4401620c3a16f1995057c2ab88acefebcf38"  # noqa: E501
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["transaction_pool_validate2"]["response"])
        )

        error_code, _ = self.loop.run_until_complete(
            c.transaction_pool_validate2(block))

        self.assertIsNone(error_code)


class TestBalance(asynctest.TestCase):
    def test_utxo_summation(self):
        c = client_with_mocked_socket()

        address = "mngSWw2NC9M1ctqZQxz65DwVomCjm7TWPJ"
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["history3"]["response"])
        )

        error_code, balance = self.loop.run_until_complete(
            c.balance(address))

        self.assertEqual(balance, 1271100000)


class TestUnspend(asynctest.TestCase):
    def test_utxo(self):
        c = client_with_mocked_socket()

        address = "mngSWw2NC9M1ctqZQxz65DwVomCjm7TWPJ"
        c._wait_for_response = CoroutineMock(
            return_value=raw_response_to_return_type(
                api_interactions["history3"]["response"])
        )

        error_code, unspends = self.loop.run_until_complete(
            c.unspend(address))

        self.assertIsNone(error_code)
        self.assertEqual(len(list(unspends)), 20)
