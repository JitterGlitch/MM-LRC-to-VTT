import os
import struct

from typing import Generator
from .opcodes import get_opcodes


DscGenerator = Generator[tuple[int, str, bytes], None, None]


class DscException(Exception):
    def __init__(self, message):            
        super(DscException, self).__init__(message)


class DscInvalidData(DscException):
    def __init__(self, id_, name, length, data):            
        super(DscInvalidData, self).__init__(
            f'Invalid data found. '
            f'Command {id_} ({name}) requires {length} bytes, '
            f'got {len(data)} instead.'
        )
        self.command_id = id_
        self.name = name
        self.length = length
        self.data = data


class DscUnknownCommand(DscException):
    def __init__(self, id_):            
        super(DscUnknownCommand, self).__init__(f'Command {id_} is unknown.')
        self.command_id = id_


def parse_dsc(dsc) -> DscGenerator:
    codes = get_opcodes()
    magic = dsc.read(4)

    while command_bytes := dsc.read(4):
        command_id = struct.unpack('<i', command_bytes)[0]

        if command_id not in codes:
            raise DscUnknownCommand(command_id)

        name, length = codes.get(command_id)
        data = dsc.read(length * 4)
        yield command_id, name, data


def enumerate_dsc(path: str | os.PathLike) -> DscGenerator:
    with open(path, mode='rb') as dsc:
        yield from parse_dsc(dsc)


def read_dsc(path: str | os.PathLike) -> list[tuple[int, str, bytes]]:
    return list(enumerate_dsc(path))


def save_dsc(path: str | os.PathLike,
             commands: list[tuple[int, str, bytes]]) -> None:
    codes = get_opcodes()

    with open(path, mode='wb') as dsc:
        for command_id, name, data in commands:
            if command_id not in codes:
                raise DscUnknownCommand(command_id)

            bytes_id = struct.pack('<i', command_id)
            name, length = codes.get(command_id)

            if len(data) == length:
                raise DscInvalidData(command_id, name, length, data)

            dsc.write(bytes_id)
            dsc.write(data)
