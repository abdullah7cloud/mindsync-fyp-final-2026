# Photo credits

All photographs are free to use under the [Unsplash License](https://unsplash.com/license) (free for commercial and
non-commercial use, no permission needed; credit is not required but is given here as good practice).
Photos were downloaded on 22 October 2026 from images.unsplash.com (resized to at most 2400 px wide), then resized again
and converted to WebP for fast loading (no other changes except cropping for the page layout). Only photos marked
"Free" on Unsplash were used (not Unsplash+ photos). Each photo carries camera data from a real camera (Canon or Fujifilm),
which is how it was checked that they are photographs and not computer-generated pictures.

| File | Used on | Photo | Photographer | Source |
|---|---|---|---|---|
| hero-*.webp | Welcome page: full-width main picture | "Three men and laughing two women walking side by side" | Eliott Reyna | https://unsplash.com/photos/jCEpN62oWL4 |
| friends-*.webp | Student Toolkit banner; welcome page ("three steps"), log-in and sign-up pages | "Three people sitting in front of table laughing together" | Brooke Cagle | https://unsplash.com/photos/g1Kr4Ozfoac |
| grass-*.webp | AI Learning Studio banner; welcome page ("a calmer way to get your work done") | "A couple of women sitting on the grass" | Meredith Spencer | https://unsplash.com/photos/yKLkWKjDlYw |
| wellbeing-*.webp | How Are You Feeling? banner; welcome page band | "Silver laptop on woman's lap" | Brooke Cagle | https://unsplash.com/photos/n1m25jvupEU |
| planner-*.webp | Smart Planner banner | "Two woman sitting near table using Samsung laptop" | Brooke Cagle | https://unsplash.com/photos/tLG2hcpITZE |
| dashboard-*.webp | Dashboard banner | "Man in black crew neck t-shirt using MacBook" | Good Faces | https://unsplash.com/photos/DSj40n6beGk |
| progress-*.webp | My Tasks banner (and the old My Progress page, now merged into the Dashboard) | "A girl sitting on a bench in front of a building" | Zoshua Colah | https://unsplash.com/photos/BatAPzG65yk |

The people in the photographs are models or private individuals; they are not MindSync users and the photographs do not
imply that they endorse MindSync. The photographs are for illustration only. The welcome page footer names the photographers.
Photos from the previous design (update 17) are kept only in the backup folder `_update_backup\before_premium18`.

## Weight
Every photo is a WebP in two or three sizes (640 and 1100 px; the hero also 800, 1280 and 1920 px); the browser picks the size
for the screen. About 560 KB for all 15 image files. Measured in the browser test environment: the welcome page downloads
99 KB of photos on a phone and 197 KB on a desktop; the app pages 9-18 KB on a phone and 18-36 KB on a desktop
(`e2e/browser_e2e.py` fails if the budgets are exceeded).
