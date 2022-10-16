# BatchComicTagger

To tag a folder of cbz files, place them in a folder with `ComicInfo.yaml`

If you want to try to scrape metadata from a Fandom wiki, make sure the url for each chapter's page follows this naming
scheme:
 - [example.fandom.com/wiki/Chapter_1]()
 - [example.fandom.com/wiki/Chapter_2]()
 - ...
 - [example.fandom.com/wiki/Chapter_10]()

If the url doesn't follow this pattern, don't use `--fetch`

## ComicInfo.yaml
 - Keys left blank or deleted will result in no to change to `ComicInfo.xml`
 - Keys are split into three sections as follows:
### ComicInfo
 - Every key in this section takes a string as a value. 
 - Setting the value of a key to `''` or `""` will remove that key from `ComicInfo.xml`
 - Setting the value of a key to anything other than a blank string will write that key to `ComicInfo.xml`
### autotag
 - `autotag` and `autotitle` take a bool (`true`, `on`, `yes`)
 - `autotag` will try to parse the volume and chapter from the filename
 - `autotitle` will try to parse the chapter title from the filename by assuming whatever is after the first " - " is the title. If the title has more than one " - ", title parsing will be skipped
### fetch
 - Fetching will only be done if `url` is not blank **and** the `--fetch` CLI arg is passed
 - `url` should be set to `example.fandom.com/wiki/Chapter_`. The chapter number will be parsed from the filename and appended to the end of the url
 - `Exclude` takes either a string of comma-separated values or a yaml list. See the included `ComicInfo.yaml` file for an example of both
 - Every other key takes a bool (`true`, `on`, `yes`)

Due to the inconsistencies between various Fandom wikis, you may need to modify `fandom_fetcher.py` to fetch the correct data. If your change doesn't considerably break existing functionality, feel free to open a PR

Also, make sure to double-check the fetched data. If, for example, chapter 30 was initially released, then re-ordered to be chapter 31 in its volume release, the wiki may use either 30 or 31 for the url, potentially causing the wrong data to be fetched

### tools
 - `jpeg2png` should be set to the path of the [jpeg2png](https://github.com/victorvde/jpeg2png) executable. It can be downloaded from [here](https://github.com/TheIceCreamTroll/jpeg2png) (a fork with some fixes - recommended) or [here](https://github.com/victorvde/jpeg2png) (the original)
 - `runafter` should be set to the absolute path of a script you want to run after BatchComicTagger has finished
### saveto
 - `path` sets the files will be saved to. Can be relative or absolute. If left blank, it will default to `current_directory/output`
 - `overwrite` allows new files to overwrite old ones. Takes a bool and defaults to `false`
 - `removeoriginals` removes the original file after creating the new one. Takes a bool and defaults to `false`

## Installation
 1. Clone the repository `git clone https://github.com/TheIceCreamTroll/BatchComicTagger.git`
 2. Enter the project's directory `cd BatchComicTagger`
 3. Install the Python requirements `pip install -r requirements.txt`

### CLI Arguments
 - `dir` sets the current working directory. Use this if `BatchComicTagger.py` is in a different folder from the files you are tagging. Defaults to the current working directory of `BatchComicTagger.py`
 - `fetch` enables metadata fetching from a Fandom wiki. Defaults to `false`

## Running
1. Place and edit a `ComicInfo.yaml` file into the folder with the .cbz files you wish to tag
2. Run `BatchComicTagger.py`
3. Processed files will be placed in (by default) `current_directory/output`

I recommend keeping `BatchComicTagger.py` in the folder you cloned it to and calling it from a `.bat` / `.sh` script alongside `ComicInfo.yaml`. Here are some examples:
 - Windows: `python "PATH_TO_BatchComicTagger.py" --dir "%CD%" --fetch`
 - Linux / MacOS: `python "PATH_TO_BatchComicTagger.py" --dir "$(pwd)" --fetch` (haven't tested, but it probably works)
