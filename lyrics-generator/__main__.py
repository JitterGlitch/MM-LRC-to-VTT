"""
Start using `py lyrics-generator convert-all --db mod_pv_db.txt --destination subtitles .` or
`py lyrics-generator convert 4939 --dsc rom/scripts/pv_4939_hard.dsc --db mod_pv_db.txt --destination subtitles`
"""

from typing import Annotated, Optional
from collections import defaultdict
from pathlib import Path
from string import whitespace
from dsc import parse_dsc

import typer
#import tomlkit
import datetime
import os
#import webvtt-py


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


#


def create_lyrics_vtt(
        lyrics: dict[datetime.time, str],
        name: str | None = None,
        *,
        offset: float = 0,
        header: str = None,
) -> str:
    vtt_lines = ["WEBVTT"]
    if header:
        vtt_lines.append(f"NOTE {header}")
    if name:
        vtt_lines.append(f"NOTE {name}")
    if offset != 0:
        vtt_lines.append(f"NOTE Offset: {offset} seconds")

    vtt_lines.append("")

    sorted_lyrics = sorted(lyrics.items(), key=lambda x: x[0])

    for i, (time, text) in enumerate(sorted_lyrics):
        start_total_seconds = (time.hour * 3600 + time.minute * 60 +
                               time.second + time.microsecond / 1e6 + offset)
        start_total_seconds = max(0, start_total_seconds)

        if i < len(sorted_lyrics) - 1:
            next_time = sorted_lyrics[i + 1][0]
            end_total_seconds = (next_time.hour * 3600 + next_time.minute * 60 +
                                 next_time.second + next_time.microsecond / 1e6 + offset)
        else:
            end_total_seconds = start_total_seconds + 5  # 5 second duration for last entry

        end_total_seconds = max(0, end_total_seconds)

        start_time = format_time(start_total_seconds)
        end_time = format_time(end_total_seconds)

        if text == "": continue

        vtt_lines.extend([
            f"{start_time} --> {end_time}",
            text,
            ""
        ])

    return "\n".join(vtt_lines)


def format_time(total_seconds: float) -> str:
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int(round((total_seconds - int(total_seconds)) * 1000))

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


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
        document = create_lyrics_vtt(
            lyrics[lang],
            song_name,
            offset=offset,
            #header=f'This file was autogenerated on {now}.',
        )

        file_path = os.path.join(destination, f'pv_{song_id}_{lang}.vtt')
        with open(file_path, mode='w', encoding='utf8') as f:
            contents = document
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
            document = create_lyrics_vtt(
                lyrics[lang],
                song_name,
                #header=f'This file was autogenerated on {now}.',
            )

            file_path = os.path.join(destination, f'pv_{song_id}_{lang}.vtt')
            with open(file_path, mode='w', encoding='utf8') as f:
                contents = document
                f.write(contents)


if __name__ == '__main__':
    cli()
