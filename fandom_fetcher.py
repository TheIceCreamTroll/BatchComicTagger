from bs4 import BeautifulSoup
import requests


def month_to_number(month):
    m = {'jan': 1,'feb': 2,'mar': 3,'apr': 4,'may': 5,'jun': 6,'jul': 7,'aug': 8,'sep': 9,'oct': 10,'nov': 11,'dec': 12}

    try:
        return m[month.strip()[:3].lower()]
    except:
        raise ValueError('Not a month')

def make_soup(baseurl, chapter):
    url = f'{baseurl}{chapter}'

    print(url)
    req = requests.get(url)

    if req.status_code != 200:
        raise Exception("Url returned something other than 200")

    return BeautifulSoup(req.content, "lxml")


def get_datasource(soup, data_sources=None, tag=None):
    for source in data_sources:
        try:
            data = soup.find(tag, {"data-source": source})
            return data.find(tag).text.strip()
        except AttributeError:
            continue

def get_id(soup, ids=None, next_tag=None):
    for id in ids:
        try:
            data = soup.find(id=id)
            if next_tag:
                return data.find_next(next_tag)
            else:
                return data.find_next()
        except AttributeError:
            continue

# Consider allowing data_sources / ids to be passed in ComicInfo.yaml
def get_characters(soup, exclude_list=[]):
    section_data = get_id(soup, ('Characters', 'character', 'Characters_in_Order_of_Appearance', 'Characters_in_Appearance')).text.strip()

    character_list = section_data.split('\n')
    #character_list = []
    #for tag in section_data:
    #        character_list.append(tag.text.strip())

    # Remove excluded entries from character_list
    if len(exclude_list) > 0:

        filtered_list = []
        exclude_list_lower = [x.lower() for x in exclude_list]

        for i in character_list:
            #print("")
            should_add = True
            #print("charact: " + i)

            for exclude in exclude_list_lower:
                #print("exclude: " + exclude)

                if exclude in i.lower():
                    should_add = False

            if should_add and len(i) > 0:
                #print("Added: " + i)
                filtered_list.append(i)
            #else:
                #print("Not added!")

    return filtered_list


def get_summary(soup):
    return get_id(soup, ids=('Summary', 'summary'), next_tag='p').text.strip()


def get_release_date(soup):
    results = get_datasource(soup, data_sources=('Release Date', 'release date', 'date'), tag='div').replace(',', ' ')

    # Day and month are sometimes swapped
    if results.split()[0].isnumeric():
        day = results.split()[0]
        month = results.split()[1]
    else:
        day = results.split()[1]
        month = results.split()[0]

    if len(results.split()[2]) == 4:
        year = results.split()[2]
    else:
        raise Exception("Year wasn't as expected...")

    try:
        month = str(month_to_number(month))
    except:
        raise Exception(f"Error converting the month to a number due to the dev's skill issue. \n{Exception}")
    return day, month, year


def get_story_arc(soup):
    return get_datasource(soup, data_sources=('Story Arc', 'arc', 'story arc', 'Arc'), tag='div')


def get_volume(soup):
    return get_datasource(soup, data_sources=('Volume', 'volume'), tag='div')


def get_title(soup):
    section_tag = soup.find("aside")

    try:
        section_data = section_tag.find_next()
        return section_data.text.strip()
    except AttributeError:
        return
