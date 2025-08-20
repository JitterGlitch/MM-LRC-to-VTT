# Lyrics-Generator

This script is used to bulk-generate many VTT lyrics files from a single `mod_pv_db.txt` file and their referenced DSC files.
VTT lyrics require the [Subtitle](https://divamodarchive.com/post/128) mod

## Requirements

- Python 3.10 or higher.

## Build using

- [Typer](https://typer.tiangolo.com/)

## Usage

1. Place DSC files in the `rom/script` folder. (They have to match the path of the `mod_pv_db.txt` file)
1. Place the `mod_pv_db.txt` in the main directory
1. Run `python -m venv venv && venv\Scripts\activate.bat` to create and enter a virtual environment (Optional, but recommended)
1. Run `pip install -r requirements.txt` to install requirements
1. Run `python lyrics-generator convert-all --db mod_pv_db.txt --destination subtitles .`
1. The lyrics will be generated in the newly created `subtitles` folder

_Can also do single files using `python lyrics-generator convert 4939 --dsc rom/script/pv_4939_hard.dsc --db mod_pv_db.txt --destination subtitles`_

_Tip: Try `python lyrics-generator convert-all --help`_
