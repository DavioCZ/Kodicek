# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-06-06

### Changed
- Enhanced `get_stream_link` function in `kodicek.py`:
  - Tries multiple parameter combinations (`video_stream`, `file_download`, no `download_type`) when requesting a stream link from the Webshare API.
  - Added detailed logging for request parameters and raw XML responses.
  - Displays a Kodi notification if a stream link cannot be obtained after all attempts.
- Enhanced `play` action in `kodicek.py`:
  - Added more verbose logging throughout the playback initiation process, with a `[PLAY]` prefix for easier log filtering.
  - Ensures user credentials and Webshare token are re-validated or re-fetched before attempting to get a stream link.
  - Displays Kodi notifications for errors encountered during the play action (e.g., missing ident, login failure, failure to get stream link).
- Improved `ListItem` handling in `kodicek.py` for better playback compatibility:
  - Added a `get_mimetype(filename)` helper function to determine common video MIME types based on file extensions.
  - Set `IsPlayable` property to `true` for `ListItem` objects in search results.
  - In the `play` action, the `ListItem` passed to `xbmcplugin.setResolvedUrl()` now:
    - Includes necessary HTTP headers (User-Agent, Cookie with Webshare token) appended to the stream URL, separated by `|`.
    - Has its `MimeType` property set using the `get_mimetype` function.
    - Has its `IsPlayable` property set to `true`.

## [Unreleased]

### Added
- Initial project setup.
