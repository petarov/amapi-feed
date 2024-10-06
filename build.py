#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import html
import re
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

url = 'https://developers.google.com/android/management/release-notes'

response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

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

expandable_sections = soup.find_all('section', class_='expandable')

feed = ET.Element("feed", xmlns="http://www.w3.org/2005/Atom")

title = ET.SubElement(feed, "title")
title.text = "Google Android Management API Release Notes"

link = ET.SubElement(feed, "link", href=url)

updated = ET.SubElement(feed, "updated")
updated.text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

author = ET.SubElement(feed, "author")
author_name = ET.SubElement(author, "name")
author_name.text = "Google Developers"

# Base URL for the ID and link
base_url = "https://developers.google.com/android/management/release-notes"

for index, section in enumerate(expandable_sections):
    h2_element = section.find('h2')
    title_text = h2_element['data-text'] if h2_element and 'data-text' in h2_element.attrs else ""

    date = parse_date(title_text)

    h3_element = section.find('h3')
    subtitle_text = h3_element['data-text'] if h3_element and 'data-text' in h3_element.attrs else ""

    subtitle_paragraph = section.find('p').get_text().strip() if section.find('p') else ""

    notes_list = section.find('ul')
    release_notes_html = [
        html.escape(re.sub(r'\s+', ' ', li.decode_contents().strip().replace('\n', ' '))) for li in notes_list.find_all('li')
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
print(atom_feed)
