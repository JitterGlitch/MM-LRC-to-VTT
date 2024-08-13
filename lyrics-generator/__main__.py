"""
Start using `py lyrics-generator convert-all --db pv_db.txt --destination generated .` or
`py lyrics-generator convert 888 --dsc rom/scripts/pv_888_easy.dsc --db mdata_pv_db.txt --destination generated`
"""

from typing import Annotated, Optional
from collections import defaultdict
from pathlib import Path
from string import whitespace
from dsc import parse_dsc

import typer
import tomlkit
import datetime
import os


cli = typer.Typer()


class PvDb:
    def __init__(self, data: list[tuple[list[str], str]]):
        self.data = data

    @staticmethod
    def parse(items: list[str]) -> list[tuple[list[str], str]]:
        """
        Parses a list of db entries into a list of tuples representing its keys and values.
        """
        def handle_line(line: str) -> tuple[str, str]:
            """
            This function parses a line like this:
            `a.b.c=val`
            into a tuple like this:
            (['a','b','c'], 'val')
            """
            line = line.strip(whitespace)
            key, value = line.split('=', 1)
            return key.split('.'), value

        def is_comment(line: str) -> bool:
            """
            Checks if the line is a comment.
            A comment is a line that starts with a '#' ignoring whitespaces.
            """
            line = line.strip(whitespace)
            return not len(line) or line.startswith('#')

        return [handle_line(line) for line in items if not is_comment(line)]

    @classmethod
    def from_file_text(cls, file_text):
        return cls(cls.parse(list(file_text)))

    def get_song_data(self, song_id: int) -> list[tuple[list[str], str]]:
        """
        Filter db data for a specific song.
        """
        data = [(key, value) for key, value in self.data if int(key[0].replace('pv_', '')) == song_id]
        return data

    def get_song_name(self, song_id: int, postfix: str = '_en') -> str:
        """
        Retrieve a song name from a db.
        """
        data = self.get_song_data(song_id)
        song_name = next((value for key, value in data if key[-1] == f'song_name{postfix}'), None)
        return song_name

    def get_dsc_files(self) -> list[str]:
        return [(key[0], value) for key, value in self.data if key[-1] == 'script_file_name']

    def get_lyrics(self, song_id: int) -> dict[tuple[str, int], list[str]]:
        data = self.get_song_data(song_id)

        data = [
            (key[1].replace('lyric', '').strip('_'), int(key[2]), value)
            for key, value in data if key[1].startswith('lyric')
        ]

        return {
            (item[0] if len(item[0]) else 'jp', item[1]): item[2]
            for item in sorted(data, key=lambda item: item[1])
        }


def time_from_timestamp(ts: int) -> datetime.time:
    seconds = max(0, ts / 100000)
    hours = int(seconds // 3600)
    seconds %= 3600
    minutes = int(seconds // 60)
    seconds %= 60
    microseconds = int((seconds - int(seconds)) * 1000000)
    seconds = int(seconds)

    return datetime.time(hour=hours, minute=minutes, second=seconds, microsecond=microseconds)


def get_times(dsc) -> dict[int, int]:
    time = 0
    times = {}

    for id_, _, params in dsc:
        if id_ == 1: # 'TIME'
            time = int.from_bytes(params, 'little')
            time = time_from_timestamp(time)

        elif id_ == 24: # 'LYRIC'
            lyric_id = int.from_bytes(params[:4], 'little')
            times[time] = lyric_id

    return times


def create_lyrics(dsc, db: PvDb, song_id: int) -> dict[str, dict[datetime.time, str]]:
    lyrics = db.get_lyrics(song_id)
    times = get_times(dsc)

    languages = {lang for lang, _ in lyrics.keys()}

    def join_lyrics(times, lyrics, lang):
        return {t: lyrics.get((lang, idx), '') for t, idx in times.items()}

    return {lang: join_lyrics(times, lyrics, lang) for lang in languages}


def create_lyrics_toml(
    lyrics: dict[datetime.time, str],
    name: str | None = None,
    *,
    offset: float = 0,
    header: str = None,
    aot: bool = False,
) -> tomlkit.document:
    document = tomlkit.document()

    if header:
        document.add(tomlkit.comment(header))
        if not name:
            document.add(tomlkit.nl())

    if name:
        document.add(tomlkit.comment(name))
        document.add(tomlkit.nl())
        
    if offset != 0:
        document.add('offset', time_from_timestamp(offset))
        document.add(tomlkit.nl())

    lyrics_array = tomlkit.aot() if aot else tomlkit.array().multiline(True)

    for time, text in lyrics.items():
        item = tomlkit.table() if aot else tomlkit.inline_table()
        item.add('time', time)
        item.add('text', text)

        # if time.microsecond == 0:
        #     item.get('time').trivia.trail = '.000000'

        lyrics_array.append(item) if aot else lyrics_array.add_line(item)

    document.add('lyrics', lyrics_array)

    return document


@cli.command()
def convert(
    song_id: Annotated[int, typer.Argument(min=1)],
    db: Annotated[typer.FileText, typer.Option(encoding='utf8')],
    dsc: Annotated[typer.FileBinaryRead, typer.Option()],
    destination: Annotated[Optional[Path], typer.Option()] = '.',
    offset: Annotated[Optional[float], typer.Option()] = 0,
    aot: Annotated[Optional[bool], typer.Option('--aot/--inline')] = False,
):
    dsc = list(parse_dsc(dsc))
    db = PvDb.from_file_text(db)

    song_name = db.get_song_name(song_id)
    lyrics = create_lyrics(dsc, db, song_id)
    now = datetime.datetime.now(datetime.timezone.utc)

    for lang in lyrics:
        document = create_lyrics_toml(
            lyrics[lang],
            song_name,
            offset=offset,
            header=f'This file was autogenerated on {now}.',
            aot=aot,
        )

        file_path = os.path.join(destination, f'{song_id}_{lang}.toml')
        with open(file_path, mode='w', encoding='utf8') as f:
            contents = tomlkit.dumps(document)
            f.write(contents)


@cli.command()
def convert_all(
    source: Annotated[Optional[Path], typer.Argument()],
    db: Annotated[typer.FileText, typer.Option(encoding='utf8')],
    destination: Annotated[Optional[Path], typer.Option()] = '.',
    aot: Annotated[Optional[bool], typer.Option('--aot/--inline')] = False,
):
    db = PvDb.from_file_text(db)

    items = db.get_dsc_files()
    files = defaultdict(list)

    print('Found', len(items), 'references in db file.')

    for pv, value in items:
        pv = int(pv.replace('pv_', ''))
        value = os.path.join(source, *value.replace('\\', '/').rsplit('/'))

        if os.path.exists(value):
            files[pv].append(value)

    if not os.path.exists(destination):
        os.makedirs(destination)

    print('Found', len(files), 'unique songs.')

    for song_id, dsc_files in files.items():
        selected_dsc = next((file for file in dsc_files if os.path.exists(file)), None)

        print('Converting', song_id, 'using', selected_dsc)
        with open(selected_dsc, mode='rb') as f:
            dsc = list(parse_dsc(f))

        song_name = db.get_song_name(song_id)
        lyrics = create_lyrics(dsc, db, song_id)
        now = datetime.datetime.now(datetime.timezone.utc)

        for lang in lyrics:
            document = create_lyrics_toml(
                lyrics[lang],
                song_name,
                header=f'This file was autogenerated on {now}.',
                aot=aot,
            )

            file_path = os.path.join(destination, f'{song_id}_{lang}.toml')
            with open(file_path, mode='w', encoding='utf8') as f:
                contents = tomlkit.dumps(document)
                f.write(contents)


if __name__ == '__main__':
    cli()
