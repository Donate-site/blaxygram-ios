# Blaxygram iOS IPA

Native gramsrv-compatible iPhone client, built using the workflow that successfully produced LunaGram build 3. This is a separate Blaxygram configuration: its own server, public RSA key, bundle ID, name and approved coral icon.

Upload this folder, including `.github/workflows/build.yml`, into a GitHub repository. Open **Actions → Build Blaxygram IPA → Run workflow**. After success, download **Blaxygram-IPA-N**. The job validates ZIP integrity, ARM64/iPhone platform and app identity before uploading the IPA.

The IPA is unsigned. Sign it with your own certificate in ESign before installing. Apple credentials are not required by this workflow and must not be committed. App Groups have a private-container fallback for externally signed installs. APNs is not configured; no claim is made that push or device runtime has been tested.

The source commit is pinned in source.json and the workflow. prepare.py applies all changes with source-shape assertions. Build artifacts include the changes and preparation script. Original source/license notices are retained upstream. No production bot tokens, private RSA keys or user data are included.

Check the Actions tab for the current build status. Local patch application was validated against the pinned upstream source before upload.
