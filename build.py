#!/usr/bin/env python3

import requests
import argparse
from bs4 import BeautifulSoup
import html
import re
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

feed_title = "Google Android Management API Release Notes"
url = 'https://developers.google.com/android/management/release-notes'
date_formats = [
    "%B %Y",
    "%d %B %Y"
]
last_parsed_date = None

def subtract_one_month(date):
    month = date.month
    year = date.year
    if month == 1:
        month = 12
        year -= 1
    else:
        month -= 1
    return date.replace(month=month, year=year)

def parse_date(title):
    global last_parsed_date
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
        # if nothing could be parsed, return the current date and time
        current_date = datetime.now(timezone.utc)
        return current_date.strftime("%Y-%m-%dT%H:%M:%SZ")

def create_atom(sections):
    feed = ET.Element("feed", xmlns="http://www.w3.org/2005/Atom")

    title = ET.SubElement(feed, "title")
    title.text = feed_title

    link = ET.SubElement(feed, "link", href=url)

    updated = ET.SubElement(feed, "updated")
    updated.text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    author = ET.SubElement(feed, "author")
    author_name = ET.SubElement(author, "name")
    author_name.text = "Google Developers"

    # Base URL for the ID and link
    base_url = url

    for index, section in enumerate(sections):
        h2_element = section.find('h2')
        title_text = h2_element['data-text'] if h2_element and 'data-text' in h2_element.attrs else ""

        date = parse_date(title_text)

        h3_element = section.find('h3')
        subtitle_text = h3_element['data-text'] if h3_element and 'data-text' in h3_element.attrs else ""

        subtitle_paragraph = section.find('p').get_text().strip() if section.find('p') else ""

        notes_list = section.find('ul')
        #html.escape
        release_notes_html = [
            (re.sub(r'\s+', ' ', li.decode_contents().strip().replace('\n', ' '))) for li in notes_list.find_all('li')
        ] if notes_list else []

        entry = ET.SubElement(feed, "entry")

        section_id = section.get('id', f"release-{index + 1}")
        
        entry_id = ET.SubElement(entry, "id")
        entry_id.text = f"{base_url}/{section_id}"

        entry_link = ET.SubElement(entry, "link", href=f"{base_url}#{section_id}")

        entry_title = ET.SubElement(entry, "title")
        entry_title.text = title_text

        entry_updated = ET.SubElement(entry, "updated")
        entry_updated.text = date

        entry_subtitle = ET.SubElement(entry, "subtitle")
        entry_subtitle.text = subtitle_text + " " + subtitle_paragraph

        entry_content = ET.SubElement(entry, "content", type="html")
        entry_content.text = "<ul>" + "".join([f"<li>{note}</li>" for note in release_notes_html]) + "</ul>"

    atom_feed = ET.tostring(feed, encoding="utf-8", method="xml").decode("utf-8")
    
    return atom_feed

def create_rss(sections):
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    title = ET.SubElement(channel, "title")
    title.text = feed_title

    link = ET.SubElement(channel, "link")
    link.text = url

    # description = ET.SubElement(channel, "description")
    # description.text = feed_title

    author = ET.SubElement(channel, "author")
    author.text = "Google Developers"

    last_build_date = ET.SubElement(channel, "lastBuildDate")
    last_build_date.text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

    # Base URL for the ID and link
    base_url = url

    for index, section in enumerate(sections):
        h2_element = section.find('h2')
        title_text = h2_element['data-text'] if h2_element and 'data-text' in h2_element.attrs else ""

        date = parse_date(title_text)

        h3_element = section.find('h3')
        subtitle_text = h3_element['data-text'] if h3_element and 'data-text' in h3_element.attrs else ""

        subtitle_paragraph = section.find('p').get_text().strip() if section.find('p') else ""

        notes_list = section.find('ul')
        #html.escape
        release_notes_html = [
            (re.sub(r'\s+', ' ', li.decode_contents().strip().replace('\n', ' '))) for li in notes_list.find_all('li')
        ] if notes_list else []

        section_id = section.get('id', f"release-{index + 1}")

        item = ET.SubElement(channel, "item")

        item_title = ET.SubElement(item, "title")
        item_title.text = title_text

        item_link = ET.SubElement(item, "link")
        item_link.text = f"{base_url}#{section_id}"

        item_description = ET.SubElement(item, "description")
        #item_description.text = "<![CDATA[<ul>" + "".join([f"<li>{note}</li>" for note in release_notes_html]) + "</ul>]]>"
        item_description.text = f"<p>{subtitle_text} {subtitle_paragraph}</p>" + "<ul>" + "".join([f"<li>{note}</li>" for note in release_notes_html]) + "</ul>"

        # item_guid = ET.SubElement(item, "guid")
        # item_guid.text = "{base_url}/{section_id}"
        # item_guid.set('isPermaLink', 'true')

        item_pub_date = ET.SubElement(item, "pubDate")
        item_pub_date.text = date

    rss_feed = ET.tostring(rss, encoding='utf-8', method='xml').decode('utf-8')

    return rss_feed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Atom or RSS 2.0 feed")
    parser.add_argument("format", choices=["atom", "rss"], help="Specify output format (atom or rss)")
    args = parser.parse_args()

    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    expandable_sections = soup.find_all('section', class_='expandable')

    if args.format == "atom":
        output = create_atom(expandable_sections)
    else:
        output = create_rss(expandable_sections)

    print(output)
