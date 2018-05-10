This library exposes the Query Service of [libbitcoin-server](https://github.com/libbitcoin/libbitcoin-server).

# Requirements

- `python3-dev`


# Tests

The project uses `unittest` and can be run with:

```
$ python3 -m unittest
```

# Example

The project contains a trivial CLI example. Set `$PYTHONPATH` to include the project root (typically `cd <path-to-project> && export PYTHONPATH=.`).
Then run with:

```
$ python3 examples/cli.py last_height
```
