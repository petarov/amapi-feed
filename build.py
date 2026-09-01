
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "beautifulsoup4"]
# ///

import argparse
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

SOURCES = {
    "amapi": {
        "title": "Google Android Management API Release Notes",
        "url": "https://developers.google.com/android/management/release-notes",
    },
    "sdk": {
        "title": "Google Android Management API SDK Release Notes",
        "url": "https://developers.google.com/android/management/sdk-release-notes",
    },
}

def subtract_one_month(date):
    month = date.month
    year = date.year
    if month == 1:
        month = 12
        year -= 1
    else:
        month -= 1
    return date.replace(month=month, year=year)

def first_of_month():
    # if nothing could be parsed, return the first day of the month
    # this fixes a problem where new items without post date linger
    # for too long at the top of the list, and have their pubDate
    # constantly generated anew
    current_date = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    return current_date.strftime("%Y-%m-%dT%H:%M:%SZ")

def collapse(html):
    return re.sub(r'\s+', ' ', html.strip().replace('\n', ' '))

def parse_amapi(soup):
    """Release notes grouped in <section class="expandable"> blocks, titled by month."""
    date_formats = [
        "%B %Y",
        "%d %B %Y"
    ]
    last_parsed_date = None

    def parse_date(title):
        nonlocal last_parsed_date
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(title, fmt)
                last_parsed_date = parsed_date
                return parsed_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                continue
        if last_parsed_date:
            last_parsed_date = subtract_one_month(last_parsed_date)
            return last_parsed_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            return first_of_month()

    entries = []

    for index, section in enumerate(soup.find_all('section', class_='expandable')):
        h2_element = section.find('h2')
        title_text = h2_element['data-text'] if h2_element and 'data-text' in h2_element.attrs else ""

        date = parse_date(title_text)

        h3_element = section.find('h3')
        subtitle_text = h3_element['data-text'] if h3_element and 'data-text' in h3_element.attrs else ""

        subtitle_paragraph = section.find('p').get_text().strip() if section.find('p') else ""

        notes_list = section.find('ul')
        release_notes_html = [
            collapse(li.decode_contents()) for li in notes_list.find_all('li')
        ] if notes_list else []

        entries.append({
            "section_id": section.get('id', f"release-{index + 1}"),
            "title": title_text,
            "updated": date,
            "summary": subtitle_text + " " + subtitle_paragraph,
            "content_html": "<ul>" + "".join([f"<li>{note}</li>" for note in release_notes_html]) + "</ul>",
        })

    return entries

def parse_sdk(soup):
    """SDK release notes: flat <h2 data-text="Version x.y.z"> headings, each followed
    by an <em> date paragraph and a body of mixed <p>/<ul>/<aside> elements."""
    date_formats = [
        "%B %d, %Y",
        "%b %d, %Y"
    ]

    def parse_date(elements):
        for element in elements:
            if element.name != 'p':
                continue
            em = element.find('em')
            if not em or em.get_text(strip=True) != element.get_text(strip=True):
                continue
            text = em.get_text(strip=True)
            for fmt in date_formats:
                try:
                    return element, datetime.strptime(text, fmt).strftime("%Y-%m-%dT%H:%M:%SZ")
                except ValueError:
                    continue
        return None, first_of_month()

    entries = []

    for h2_element in soup.find_all('h2'):
        title_text = h2_element.get('data-text', "")
        if not title_text.startswith("Version"):
            # skips "Latest Update", which repeats the newest version, and
            # "Declare dependencies"
            continue

        body = []
        for element in h2_element.next_siblings:
            if getattr(element, 'name', None) is None:
                continue
            if element.name == 'h2':
                break
            body.append(element)

        date_element, date = parse_date(body)

        content_html = "".join(
            collapse(str(element)) for element in body if element is not date_element
        )

        entries.append({
            "section_id": h2_element.get('id', ""),
            "title": title_text,
            "updated": date,
            "summary": "",
            "content_html": content_html,
        })

    return entries

def create_atom(source, entries):
    feed = ET.Element("feed", xmlns="http://www.w3.org/2005/Atom")

    title = ET.SubElement(feed, "title")
    title.text = source["title"]

    ET.SubElement(feed, "link", href=source["url"])

    updated = ET.SubElement(feed, "updated")
    updated.text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    author = ET.SubElement(feed, "author")
    author_name = ET.SubElement(author, "name")
    author_name.text = "Google Developers"

    # base URL for the ID and link
    base_url = source["url"]

    for entry_data in entries:
        entry = ET.SubElement(feed, "entry")

        section_id = entry_data["section_id"]

        entry_id = ET.SubElement(entry, "id")
        entry_id.text = f"{base_url}/{section_id}"

        ET.SubElement(entry, "link", href=f"{base_url}#{section_id}")

        entry_title = ET.SubElement(entry, "title")
        entry_title.text = entry_data["title"]

        entry_updated = ET.SubElement(entry, "updated")
        entry_updated.text = entry_data["updated"]

        if entry_data["summary"]:
            entry_subtitle = ET.SubElement(entry, "subtitle")
            entry_subtitle.text = entry_data["summary"]

        entry_content = ET.SubElement(entry, "content", type="html")
        entry_content.text = entry_data["content_html"]

    atom_feed = ET.tostring(feed, encoding="utf-8", method="xml").decode("utf-8")

    return atom_feed

def create_rss(source, entries):
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    title = ET.SubElement(channel, "title")
    title.text = source["title"]

    link = ET.SubElement(channel, "link")
    link.text = source["url"]

    # description = ET.SubElement(channel, "description")
    # description.text = source["title"]

    author = ET.SubElement(channel, "author")
    author.text = "Google Developers"

    last_build_date = ET.SubElement(channel, "lastBuildDate")
    last_build_date.text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

    # base URL for the ID and link
    base_url = source["url"]

    for entry_data in entries:
        item = ET.SubElement(channel, "item")

        item_title = ET.SubElement(item, "title")
        item_title.text = entry_data["title"]

        item_link = ET.SubElement(item, "link")
        item_link.text = f"{base_url}#{entry_data['section_id']}"

        summary_html = f"<p>{entry_data['summary']}</p>" if entry_data["summary"] else ""

        item_description = ET.SubElement(item, "description")
        item_description.text = summary_html + entry_data["content_html"]

        # item_guid = ET.SubElement(item, "guid")
        # item_guid.text = "{base_url}/{section_id}"
        # item_guid.set('isPermaLink', 'true')

        item_pub_date = ET.SubElement(item, "pubDate")
        item_pub_date.text = entry_data["updated"]

    rss_feed = ET.tostring(rss, encoding='utf-8', method='xml').decode('utf-8')

    return rss_feed

SOURCES["amapi"]["parse"] = parse_amapi
SOURCES["sdk"]["parse"] = parse_sdk

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Atom or RSS 2.0 feed")
    parser.add_argument("source", choices=list(SOURCES), help="Specify which release notes page to parse")
    parser.add_argument("format", choices=["atom", "rss"], help="Specify output format (atom or rss)")
    args = parser.parse_args()

    source = SOURCES[args.source]

    response = requests.get(source["url"])
    soup = BeautifulSoup(response.content, 'html.parser')
    entries = source["parse"](soup)

    if args.format == "atom":
        output = create_atom(source, entries)
    else:
        output = create_rss(source, entries)

    print(output)
