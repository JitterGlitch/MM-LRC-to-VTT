# Lyrics-Generator

This script is used to bulk-generate many TOML lyrics files from a single `pv_db.txt` file and their referenced DSC files.
TOML lyrics require the [LyricsPatch](https://gamebanana.com/mods/414986) mod

## Requirements

- Python 3.10 or higher.

## Build using

- [Typer](https://typer.tiangolo.com/)
- [TOML Kit](https://tomlkit.readthedocs.io/en/latest/)

## Usage

1. Place DSC files in the `rom/script` folder. (They have to match the path of the `pv_db.txt` file)
1. Place the `pv_db.txt` in the main directory
1. Run `python -m venv venv && venv\Scripts\activate.bat` to create and enter a virtual environment (Optional, but recommended)
1. Run `pip install -r requirements.txt` to install requirements
1. Run `python lyrics-generator convert-all --db pv_db.txt --destination generated .`
1. The lyrics will be generated in the newly created `generated` folder

_Can also do single files using `python lyrics-generator convert 888 --dsc rom/script/pv_888_easy.dsc --db mdata_pv_db.txt --destination generated`_

_Tip: Try `python lyrics-generator convert-all --help`_
