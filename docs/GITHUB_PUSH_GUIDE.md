# Submit your code on GitHub (due 13/11/2026 12:00)

Only you can do the sign-in step. Never share your GitHub password/token with anyone (including me).

## One-time setup
1. Make a free account at github.com (if you do not have one). Verify your e-mail.
2. Click **New repository**. Name: `mindsync-fyp`. Choose **Private** (ask your supervisor which they need - they may require you to add them as a collaborator, or make it public). Do NOT tick "Add README".
3. Install Git for Windows (git-scm.com) if `git --version` does not work in a terminal.

## Push (VS Code terminal, inside the MindSync folder)
```
git init
git add .
git status
```
CHECK the list: it must NOT show `backend/.env`, `.venv`, `node_modules`. (`.gitignore` already blocks them. If `.env` appears, STOP and tell Claude.)
```
git commit -m "MindSync final year project"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/mindsync-fyp.git
git push -u origin main
```
GitHub will open a browser window to sign you in - do that yourself.

## Before the final push
- Run `run-tests.bat` (all tests pass) and `run-security-test.bat`, `run-benchmark.bat` so `docs/` has the latest results.
- Add your signed meeting notes in a `meeting-notes/` folder.
- Rotate the secret: the JWT secret in `.env` is not pushed, but if you ever pasted a real API key anywhere public, delete that key and make a new one.
- Add your supervisor as a collaborator (Settings -> Collaborators) if the repo is private.
- Copy the repository link into your report (Appendix) and Turnitin submission note if required.
