[![Deployed to Pages](https://github.com/petarov/amapi-feed/actions/workflows/static.yml/badge.svg)](https://github.com/petarov/amapi-feed/actions/workflows/static.yml)

Android Management API Updates Feed
===================================

Google Android Management API [release notes](https://developers.google.com/android/management/release-notes) and [SDK release notes](https://developers.google.com/android/management/sdk-release-notes) feeds. 

Follow the feed to get notified about changes and new releases.

Auto-updated at `06:00 (UTC)` every `Monday`, `Wednesday`, and `Friday`.

Feed | Type | Source
-----|------|-------
[amapi-rel-notes.rss](https://petarov.github.io/amapi-feed/amapi-rel-notes.rss) | RSS | API release notes
[amapi-rel-notes.atom](https://petarov.github.io/amapi-feed/amapi-rel-notes.atom) | Atom | API release notes
[amapi-sdk.rss](https://petarov.github.io/amapi-feed/amapi-sdk.rss) | RSS | SDK release notes
[amapi-sdk.atom](https://petarov.github.io/amapi-feed/amapi-sdk.atom) | Atom | SDK release notes

# Usage

Run locally using [uv](https://github.com/astral-sh/uv):

    uv run build.py [amapi|sdk] [rss|atom] > feed.xml

# License 

[MIT License](LICENSE)
