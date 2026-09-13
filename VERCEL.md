# Deploy LoveFlix on Vercel + Supabase

Vercel runs the site and Python API. Supabase provides a persistent Postgres database and a private S3-compatible media bucket. GitHub Pages is not used. Local `npm start` and Go Live still use SQLite and local uploads.

## 1. Create storage

Create a Supabase project in your account. Under Storage, create a **private** bucket named `loveflix`. Keep the database schema `loveflix` out of Supabase's exposed API schemas; only the backend connects to it.

Copy the transaction-pooler PostgreSQL connection string from **Connect**. Use SSL (`sslmode=require`). Under Storage settings, enable S3 and generate server-side S3 credentials. Copy the exact endpoint and region shown there.

Use the six settings in `.env.example`: `DATABASE_URL`, `S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, and `S3_BUCKET`. Keep their values out of Git, browser code, and chat.

Review the current Supabase plan's storage quota and file-size limit. Set the bucket limit to the size you need (the application allows up to 250 MB, subject to the storage plan). Browser uploads use signed S3 PUT requests. If using another S3 provider, configure CORS for your site's exact origins, allowing PUT, GET, HEAD, and Content-Type. Supabase handles storage CORS itself.

## 2. Initialize the cloud data once

On your computer, create a Python virtual environment and install `requirements.txt`. Load the six settings into that terminal's environment, then run:

```sh
python scripts/setup_cloud.py
```

This creates the schema and copies the project's original media into the private bucket. It uses a temporary empty SQLite seed, so it does not read or publish your local accounts or edits.

If you explicitly want to migrate your saved local accounts, profile edits, favorites, and uploaded media too, stop the local server and run this instead, **before the cloud database is initialized**:

```sh
python scripts/setup_cloud.py --local-data backend/data
```

That option sends your saved data to your configured Supabase project. Existing password hashes are preserved; active sessions are not copied. The initialization script refuses to overwrite a populated cloud media library. Keep a backup of `backend/data`.

## 3. Import into Vercel

1. Sign in to Vercel and import `suhanashr28/sabal`, branch `main`.
2. Choose **Other** as the framework. The checked-in `vercel.json` supplies the build and routing settings.
3. Add the same six settings as server environment variables. Only enable Preview access to the production database if you intentionally want previews to share live edits.
4. Deploy and open the generated HTTPS address.
5. Create your first account, or sign in with a migrated account.

The API accepts the deployment and production hostnames supplied by Vercel. For a custom domain, set `PUBLIC_ORIGIN` to its exact HTTPS origin, without a path.

All pages and original media pass through the API's authentication checks. Media bytes go directly to private storage through temporary signed links so playback and uploads avoid Vercel's 4.5 MB payload limit. A signed media link remains usable for up to one hour after issuance. Accounts share the site's profiles, memories, and editing access.

## Verification after deployment

Check account creation/login, password visibility, favorites, uploading a photo and video, replacing a file, refreshing after an edit, video seeking, and access after a redeploy. Verify that a signed-out request to `/images/us-1.jpeg` is rejected and `/.env` and `/backend/cloud.py` are not served.

The repository tests exercise the HTTP cloud flow with isolated database/storage stand-ins. Actual Postgres, S3 browser CORS, and Vercel routing must also be verified once the accounts are connected.

## Storage maintenance

Completed uploads preserve replaced files for recovery. Temporary files under `pending/` are not published to the media library. Remove abandoned pending objects only after their signed upload URLs expire (at least one hour); keep `uploads/` and original media. Review quotas and provider billing before increasing limits or adding a paid service.
