import fandom_fetcher
from lxml import etree as ET
from pathlib import Path
from time import time
import subprocess
import argparse
import confuse
import zipfile
import shutil
import sys
import os


# XML Parser and some constants
xmlparser = ET.XMLParser(remove_blank_text=True)
ext = '.cbz'
cwd = Path.cwd()
xmlfile = 'ComicInfo.xml'
validvolumes = ("Vol", "Vol.", "Volume", "Volume.")
validchapters = ("Ch", "Ch.", "Chapter", "Chapter.")
do_cleanup = False

# YAML parser
config = confuse.Configuration('BatchComicTagger', __name__)
config.set_file('ComicInfo.yaml')
yml = config.get()

# Argparse
parser = argparse.ArgumentParser(description='Batch comicinfo.xml metadata')
parser.add_argument('-d,', '--dir', default=cwd, help='Directory to run in')
parser.add_argument('-f,', '--fetch', action='store_true', help='Enable fetching data from a Fandom wiki')

args = parser.parse_args()
os.chdir(args.dir)


# Need to catch KeyError exceptions for deleted keys in the yaml file.
def checkConfig(key):
    try:
        if len(key) == 1:
            return yml[key[0]]
        if len(key) == 2:
            return yml[key[0]][key[1]]

    except KeyError:
        return False


def parse(matchingwords, filename):
    parts = filename.rstrip(ext).split()

    for i in matchingwords:

        try:
            pos = parts.index(i)
        except Exception:
            continue

        try:
            number = parts[pos + 1]
            if '.' in number:
                return float(number)

            return int(number)

        except (TypeError, ValueError):
            continue


def parseTitle(filename):
    parts = filename.rstrip(ext).split(' - ', 1)
    if len(parts) == 2:
        return parts[-1].strip()
    else:
        print("    Something was wonky with parsing the title. Skipping.")


def updateTag(key, value, root):
    existingTag = tree.find(key)
    value = str(value)

    if existingTag is not None:
        existingTag.text = value
        if value:
            print(f"    updating {key} tag from '{existingTag.text}' -> '{value}'")
        else:
            print(f"    Removing {key} tag '{existingTag.text}'")
    else:
        print(f"    creating new {key} tag -> '{value}'")
        ET.SubElement(root, key).text = value


def createComicInfo(xmlpath, file):
    defaultXML = '<ComicInfo>'
    defaultXML += "</ComicInfo>"

    with open(xmlpath, 'w', encoding='utf-8') as f:
        print(f"{xmlfile} not detected in {file}. Creating it now.")
        f.write(defaultXML)


def cleanup(extract_path=None, output_path=None):
    if extract_path and extract_path.exists():
        shutil.rmtree(extract_path)

    if output_path and output_path.exists():
        if len(os.listdir(output_path)) == 0:
            shutil.rmtree(output_path)

# ComicInfo Autotag options
autotag_autonumber = checkConfig(('autotag', 'autonumber'))
autotag_autotitle = checkConfig(('autotag', 'autotitle'))

# ComicInfo Fetch options
fetch_url = checkConfig(('fetch', 'url'))
fetch_storyarc = checkConfig(('fetch', 'StoryArc'))
fetch_characters = checkConfig(('fetch', 'Characters'))
fetch_exclude = checkConfig(('fetch', 'Exclude'))
fetch_releasedate = checkConfig(('fetch', 'ReleaseDate'))
fetch_summary = checkConfig(('fetch', 'Summary'))
fetch_volume = checkConfig(('fetch', 'Volume'))
fetch_title = checkConfig(('fetch', 'Title'))

# ComicInfo tools options
jpeg2png = checkConfig(('tools', 'jpeg2png'))
tools_runafter = checkConfig(('tools', 'runafter'))

# ComicInfo saveto options
saveto_path = checkConfig(('saveto', 'path'))
saveto_overwrite = checkConfig(('saveto', 'overwrite'))
saveto_removeoriginals = checkConfig(('saveto', 'removeoriginals'))

# Clear out any
cleanup(cwd / 'output' / 'extracted')

for file in os.listdir(cwd):
    if file.endswith(ext):
        ext_dest = cwd / 'output' / 'extracted' / file.rsplit('.', 1)[0]

        if not ext_dest.exists():
            os.makedirs(ext_dest)

        with zipfile.ZipFile(cwd / file, 'r') as f:
            f.extractall(ext_dest)

        do_cleanup = True
        file_list = list(Path(ext_dest).rglob('*'))
        xmlpath = ext_dest / xmlfile

        if jpeg2png:
            print('starting jpeg2png')
            start = time()

        for jpeg in file_list:
            if jpeg.suffix in (('.jpeg', '.jpg')) and jpeg2png:
                res = subprocess.run([jpeg2png, '-f', '-s', '-i 100', jpeg], capture_output=True)
                if res.returncode == 0:
                    jpeg.unlink()
                else:
                    print(f"Warning! [{jpeg}] couldn't be processed by jpeg2png\nError: {res.stderr.decode().strip()}")

            # print(jpeg)
            if jpeg.suffix == '.xml':
                print(f"{xmlfile} found in {file}")
                break  # There should only be one .xml file per cbz
        else:
            createComicInfo(xmlpath, file)

        if jpeg2png:
            print(f'jpeg2png finished. {round(time() - start, 2)}s elapsed')

        # Process the xml
        xmlfilepath = ext_dest / xmlfile
        tree = ET.parse(xmlfilepath, xmlparser)
        root = tree.getroot()  # gets the parent tag of the xml document

        skipvol = False

        if fetch_url and args.fetch:
            url = yml['fetch']['url']
            chapter = parse(validchapters, file)

            # TODO - add a zfill function for the chapter
            soup = fandom_fetcher.make_soup(url, chapter)

            if fetch_storyarc:
                chapter = parse(validchapters, file)
                value = fandom_fetcher.get_story_arc(soup)

                if value:
                    updateTag('StoryArc', value, root)
                else:
                    print("    Couldn't scrape story arc. Leaving blank")

            if fetch_characters:
                chapter = parse(validchapters, file)

                if fetch_exclude:
                    exclude = yml['fetch']['Exclude']
                    if isinstance(exclude, str):
                        exclude = yml['fetch']['Exclude'].split(',')

                else:
                    exclude = []

                characters = fandom_fetcher.get_characters(soup, exclude)
                value = ', '.join(characters)
                # if "(" in value:
                #    if input(f"{value}\nParenthesis detected. Should we keep going? (Y/n)").lower() == "n":
                #        sys.exit(0)

                if value:
                    updateTag('Characters', value, root)

            if fetch_releasedate:
                chapter = parse(validchapters, file)
                skip = False

                try:
                    value = fandom_fetcher.get_release_date(soup)
                except AttributeError:
                    print(f"Couldn't scrape release date. Go to\n{url}{chapter}\nand verify the date exists\n\n")
                    choice = input("Ignore this file and continue to tag?\n"
                                   "i = ignore file\n"
                                   "b = leave day, month and year blank\n"
                                   #"a = add {thinginparenthesis} to exclusion list\n"
                                   "q = quit\n").lower()
                    if choice == 'i':
                        continue
                    if choice == 'b':
                        skip = True
                    elif choice == 'q':
                        sys.exit(0)

                if not skip:
                    updateTag('Day', value[0], root)
                    updateTag('Month', value[1], root)
                    updateTag('Year', value[2], root)

            if fetch_summary:
                chapter = parse(validchapters, file)
                try:
                    value = fandom_fetcher.get_summary(soup)
                    updateTag('Summary', value, root)
                except AttributeError:
                    print("Summary not found. Either doesn't exist, or needs webscraping modified.")

            if fetch_volume:
                skipvol = True
                chapter = parse(validchapters, file)
                value = fandom_fetcher.get_volume(soup)

                if value:
                    updateTag('Volume', value, root)

            if fetch_title:
                chapter = parse(validchapters, file)
                value = fandom_fetcher.get_title(soup)
                if value:
                    updateTag('Title', value, root)

        if autotag_autonumber:
            if not skipvol:
                volume = parse(validvolumes, file)
            chapter = parse(validchapters, file)

            if not skipvol and volume is not None:
                updateTag("Volume", volume, root)
            if chapter:
                updateTag("Number", chapter, root)

        if autotag_autotitle:
            updateTag("Title", parseTitle(file), root)

        for key in yml['ComicInfo']:
            value = yml['ComicInfo'][key]
            if value or isinstance(value, str):
                updateTag(key, value, root)

        print("")

        ET.ElementTree(root).write(xmlfilepath, pretty_print=True, xml_declaration=True, encoding="utf-8")

        # Save the new file
        root_dir = cwd / 'output'

        if saveto_path:
            save_to = Path(saveto_path)
            if not save_to.exists():
                save_to.mkdir(parents=True)
            output_dir = save_to.resolve() / file
        else:
            output_dir = root_dir / file

        if output_dir.exists() and not saveto_overwrite:
            raise Exception(f"Destination file [{output_dir}] already exists")

        # Create final file
        with zipfile.ZipFile(output_dir, 'w', zipfile.ZIP_STORED) as archive:
            for file_path in ext_dest.rglob("*"):
                archive.write(file_path, arcname=file_path.relative_to(ext_dest))

        # Cleanup
        if saveto_removeoriginals:
            Path(file).resolve().unlink()

        shutil.rmtree(cwd / 'output' / 'extracted' / ext_dest)

if do_cleanup:
    cleanup(cwd / 'output' / 'extracted', cwd / 'output')

if tools_runafter:
    subprocess.run(tools_runafter)
print("Done")
