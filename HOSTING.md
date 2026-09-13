# Hosting LoveFlix on Render

This Blueprint creates a paid Python web service and a 1 GB persistent disk. Review the price in Render before deploying.

1. Sign in to Render and choose New → Blueprint.
2. Connect the GitHub repository suhanashr28/sabal, branch main.
3. Review the service and disk cost, then deploy.
4. Open the HTTPS address Render provides and create an account.

The service uses the assigned HTTPS hostname, secure session cookies, the platform port, and /var/data/loveflix for its SQLite database and uploads. Local npm start and Go Live still work.

The online service starts with the images/videos committed to Git and a new database. Existing local accounts, text edits and uploads are not automatically transferred. Keep backend/data out of Git. Transfer a backup privately if you want the local saved state online.

All registered accounts share the profiles, memories, and editing access. Custom domains require PUBLIC_ORIGIN to be set to the exact HTTPS origin (no trailing slash).
