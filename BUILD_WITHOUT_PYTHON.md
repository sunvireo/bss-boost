# Build Bss Booster without installing Python on your Windows PC

The **installed app does not need Python**. Because PyInstaller must build Windows executables on Windows, this project includes a free GitHub Actions build workflow. GitHub installs Python *on a temporary Windows build computer* and produces the **two finished Windows EXE files** for you.

1. Sign in to GitHub and create a **new repository** (private is fine). Leave it empty.
2. Unzip the project on your PC. Upload **the contents of `BssBoosterV1`** to the repository root using **Add file → Upload files**. Include the hidden `.github/workflows/windows-release.yml` file, plus `assets/`, `bss_booster/`, `main.py`, etc. Do not upload the outer `BssBoosterV1` folder as a single nested folder. If GitHub's website won't add hidden `.github` folder, use GitHub Desktop to commit/push the project instead.
3. Open **Actions → Build Bss Booster Windows EXE and Installer**. If prompted, enable Actions. Select **Run workflow**.
4. Wait for the build to finish with a green tick (usually a few minutes). Click the completed workflow run. Under **Artifacts**, download **BssBooster-Windows-EXE-and-Installer**.
5. Extract the downloaded artifact. Double-click **`BssBoosterSetup.exe`** to install. For a portable app without installing, launch **`BssBooster.exe`** instead.

**Neither installer nor portable app requires Python** or GitHub to *run*. Only GitHub needs access to download the build dependencies. The app uses Windows offline speech, so speech does not connect to a cloud service.

Windows may display a SmartScreen warning for unsigned programs. Inspect source code and run files only when you trust them. This project does not contain a pre-built Windows executable; it contains a workflow that builds it on GitHub.

## Alternative: build locally

If Python is already installed on a Windows PC, `build_installer_windows.bat` builds both EXE and setup installer directly. Python is only needed on the *build* machine, not by recipients.
