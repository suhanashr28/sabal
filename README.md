# LoveFlix — local app

Run `npm start`, double-click **Start LoveFlix.command**, or run `python3 backend/server.py` from this folder, then open http://localhost:8787.

On the first visit, create your username and password (at least 10 characters). Choose a profile. Keep the Terminal window running while using the site. To stop the server, press Control-C. Start it again with the same command; saved changes remain.

## Everyday use

- **Gallery and memory albums:** Add photos or videos, click a photo to view its caption, or use **Edit** to change the title, caption, album, or file.
- **Settings → Photos & videos:** Search and manage all existing and uploaded files. **Recently removed** contains recoverable items. Restore them there.
- **Home Play Movie:** In Settings, filter this album and choose **Edit → Replace file** to replace the home movie. It stays separate from the Video library.
- **Settings → Your profile:** Change the name and picture, then **Save profile**.
- **Settings → Our relationship:** Save your date and time zone. The counter uses the computer's clock in that zone and updates the anniversary countdown every second while visible.
- **Hearts:** Favorites are saved separately for the two profiles.
- **Edit page text:** Edit highlighted text, add a paragraph, then **Save text**. Clear a field to remove its text. **Cancel** discards unsaved changes.
- **Sign out:** In Settings. All registered accounts share the two profiles, memories, and editing access. Use **Create account** on the login page to register.

Uploads support JPEG, PNG, GIF, WebP, MP4, WebM, and MOV, up to 250 MB each. MP4 with H.264/AAC is the most compatible video format; MOV playback depends on its codec and browser.

## Storage and backup

The SQLite database is `backend/data/loveflix.sqlite3`. New files are in `backend/data/uploads/`. Existing photos and videos remain in their original folders. Removed files are kept for restoration; replacing a file also keeps its previous bytes in storage.

To back up the app, stop the server and copy this entire project folder, including `backend/data/`, `images/`, `videos/`, and `play/`. Do not delete `backend/data/`; it contains the account and all saved edits. Private database and upload files are excluded from Git.

This version runs only on this computer at localhost. Opening the HTML files directly or using a static preview server does not provide the backend. Online access requires separate hosting work.

## Development checks

Python 3.11 or newer is required. No external Python packages are needed.

Run: `python3 -m unittest discover -s backend/tests -v`

Tests use a separate temporary database and do not change your memories. For a separate browser test instance, run `python3 backend/server.py --port 8788 --data-dir /tmp/loveflix-test`.

## VS Code Go Live

Open this folder in VS Code and allow the automatic task when prompted. The task starts the Python backend. Click **Go Live** to use http://127.0.0.1:5500. Live Server forwards requests to the backend on port 8787. Keep the backend task running. If automatic tasks are disabled, use **Terminal → Run Task → Start LoveFlix backend**. Restart Live Server after changing its settings.
