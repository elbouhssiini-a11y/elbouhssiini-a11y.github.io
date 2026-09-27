# elbouhssiini-a11y.github.io

## Automatic App Store updates

Selected Work reads `apps.json`. GitHub Actions regenerates that file from App Store Connect. The private key never goes in the repository, in `apps.json`, or in the browser.

### GitHub Secrets

Create these in the repository: **Settings → Secrets and variables → Actions → New repository secret**.

| Name | Value |
| --- | --- |
| `APP_STORE_CONNECT_ISSUER_ID` | Issuer ID from App Store Connect → Users and Access → Integrations → App Store Connect API |
| `APP_STORE_CONNECT_KEY_ID` | Key ID of the API key |
| `APP_STORE_CONNECT_PRIVATE_KEY` | Full contents of the downloaded `.p8` file, including the `BEGIN PRIVATE KEY` and `END PRIVATE KEY` lines |

Create the API key in App Store Connect with the **Developer** role. That role can read apps and version metadata. Do not commit the `.p8` file, and do not paste it into any site file.

If a push from the Action is rejected, set **Settings → Actions → General → Workflow permissions** to **Read and write**. The workflow itself only requests `contents: write`.

### How a run works

The workflow `.github/workflows/update-apps.yml` runs every day at 06:17 UTC, and you can start it from **Actions → Update apps → Run workflow**.

It signs in to the App Store Connect API, keeps iOS apps that have a version in `READY_FOR_SALE`, and writes `apps.json`. It commits only when that public list actually changes. The site then loads `apps.json` in the browser. No App Store Connect request is made from the visitor's browser.

`data/app-copy.json` is optional public wording for apps you already described. It is not a credential file. A new app does not need an entry. If an entry exists, its name, short description, icon path, and App Store URL are kept. Delete an entry when you want the Action to use the App Store text instead.

### Limitations

- Drafts, apps in review, and apps removed from sale are not listed. Only iOS versions in `READY_FOR_SALE` are included. Mac-only and visionOS-only apps are not included.
- App Store Connect does not return a public icon file. The Action downloads artwork from the public iTunes listing, or keeps the local icon named in `data/app-copy.json`. A brand-new app can appear before Apple publishes that artwork; the icon is added on a later run.
- Short text comes from `data/app-copy.json` when that app has an entry. Otherwise it uses promotional text, then the subtitle, then the first two sentences of the App Store description. If none of those exist, the text is the app name plus "is available on the App Store."
- Ratings, download counts, awards, and bundle IDs are never written.
- An empty API result does not wipe an existing `apps.json`.
- App names are inserted by JavaScript, so they are not in the initial HTML. The page title and description are unchanged.
- The Action cannot be executed until these files are on GitHub and the three secrets exist. A local run without the secrets stops before calling the API and does not rewrite `apps.json`.
