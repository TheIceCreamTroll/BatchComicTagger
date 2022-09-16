import fandom_fetcher
from lxml import etree as ET
from pathlib import Path
import argparse
import confuse
import zipfile
import shutil
import sys
import os


# XML Parser and some constants
xmlparser = ET.XMLParser(remove_blank_text=True)
ext = '.cbz'
cwd = os.getcwd()
xmlfile = 'ComicInfo.xml'
validvolumes = ("Vol", "Vol.", "Volume", "Volume.")
validchapters = ("Ch", "Ch.", "Chapter", "Chapter.")

# YAML parser
config = confuse.Configuration('BatchComicTagger', __name__)
config.set_file('ComicInfo.yaml')
yml = config.get()

# Argparse
parser = argparse.ArgumentParser(description='Batch comicinfo.xml metadata')
parser.add_argument('-d,', '--dir', default=os.getcwd(), help='Directory to run in')
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
    #existingTag = tree.find(key) # TODO - Consider enabling/disabling overwriting existing titles
    parts = filename.rstrip(ext).split(' - ', 1)
    if len(parts) == 2:
        return parts[-1].strip()
    else:
        print("    Something was wonkey with parsing the title. Skipping.")

def updateTag(key, value, root):
    existingTag = tree.find(key)

    if existingTag is not None:
        existingTag.text = str(value)
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


for file in os.listdir(cwd):
    if file.endswith(ext):
        ext_dest = os.path.join(cwd, 'output', 'extracted', file.rsplit('.', 1)[0])

        if not os.path.exists(ext_dest):
            os.makedirs(ext_dest)

        with zipfile.ZipFile(os.path.join(cwd, file), 'r') as f:
            f.extractall(ext_dest)

        file_list = list(Path(ext_dest).rglob('*'))
        xmlpath = os.path.join(ext_dest, xmlfile)

        for jpeg in file_list:
            #print(jpeg)
            if str(jpeg).endswith('.xml'):
                print(f"{xmlfile} found in {file}")
                break # There should only be one .xml file per cbz
        else:
            createComicInfo(xmlpath, file)

        # Process the xml
        xmlfilepath = os.path.join(ext_dest, xmlfile)
        tree = ET.parse(xmlfilepath, xmlparser)
        root = tree.getroot() # gets the parent tag of the xml document

        skipvol = False

        if checkConfig(('fetch', 'url')) and args.fetch:
            fetch_url = yml['fetch']['url']
            chapter = parse(validchapters, file)

            # TODO - add a zfill function for the chapter
            soup = fandom_fetcher.make_soup(fetch_url, chapter)

            if checkConfig(('fetch', 'StoryArc')):
                chapter = parse(validchapters, file)
                value = fandom_fetcher.get_story_arc(soup)

                if value:
                    updateTag('StoryArc', value, root)
                else:
                    print("    Couldn't scrape story arc. Leaving blank")

            if checkConfig(('fetch', 'Characters')):
                chapter = parse(validchapters, file)

                if checkConfig(('fetch', 'Exclude')):
                    exclude = yml['fetch']['Exclude']
                    if isinstance(exclude, str):
                        exclude = yml['fetch']['Exclude'].split(',')

                else:
                    exclude = []

                characters = fandom_fetcher.get_characters(soup, exclude)
                value = ', '.join(characters)
                #if "(" in value:
                #    if input(f"{value}\nParenthesis detected. Should we keep going? (Y/n)").lower() == "n":
                #        sys.exit(0)

                if value:
                    updateTag('Characters', value, root)

            if checkConfig(('fetch', 'ReleaseDate')):
                chapter = parse(validchapters, file)
                skip = False

                try:
                    value = fandom_fetcher.get_release_date(soup)
                except AttributeError:
                    print(f"Couldn't scrape release date. Go to\n{fetch_url}{chapter}\nand verify the date exists\n\n")
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

            if checkConfig(('fetch', 'Summary')):
                chapter = parse(validchapters, file)
                try:
                    value = fandom_fetcher.get_summary(soup)
                    updateTag('Summary', value, root)
                except AttributeError:
                    print("Summary not found. Either doesn't exist, or needs webscraping modified.")


            if checkConfig(('fetch', 'Volume')):
                skipvol = True
                chapter = parse(validchapters, file)
                value = fandom_fetcher.get_volume(soup)

                if value:
                    updateTag('Volume', value, root)

            if checkConfig(('fetch', 'Title')):
                chapter = parse(validchapters, file)
                value = fandom_fetcher.get_title(soup)
                if value:
                    updateTag('Title', value, root)

        if checkConfig(('autotag','autonumber')):
            if not skipvol:
                volume = parse(validvolumes, file)
            chapter = parse(validchapters, file)

            if not skipvol and volume is not None:
                updateTag("Volume", str(volume).lstrip("0"), root) # TODO - Volume 0 currently saves as nothing (probably bc strip())
            if chapter:
                updateTag("Number", str(chapter).lstrip("0"), root) # TODO - Chapter 0 currently saves as nothing (probably bc strip())

        if checkConfig(('autotag','autotitle')):
            updateTag("Title", parseTitle(file), root)

        for key in yml['ComicInfo']:
            value = yml['ComicInfo'][key]
            if value or isinstance(value, str):
                updateTag(key, value, root)

        print("")

        ET.ElementTree(root).write(xmlfilepath, pretty_print=True, xml_declaration=True, encoding="utf-8")

        # Create final file and cleanup
        root_dir = os.path.join(cwd, 'output')  # Location of the final archive

        # Can't change the compression to Store. Much slower than calling zipfile manually
        shutil.make_archive(ext_dest, 'zip', ext_dest)

        # with zipfile.ZipFile(f'{ext_dest}.zip', 'w', zipfile.ZIP_STORED) as new_zip:
            # for new_file in Path(ext_dest).iterdir(): # Doesn't do subdirs :(
            # for new_file in glob.glob(os.path.join(ext_dest, '**'), root_dir=ext_dest, recursive=True):
                # new_zip.write(new_file, arcname=new_file.name)

        os.rename(f'{ext_dest}.zip', f'{ext_dest + ext}')
        shutil.move(f'{ext_dest + ext}', root_dir)  # If the final file already exists, an exception will be thrown.
        shutil.rmtree(os.path.join(cwd, 'output', 'extracted', ext_dest))

shutil.rmtree(os.path.join(cwd, 'output', 'extracted'))

print("Done")
