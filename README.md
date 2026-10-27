# 12 Frames Per Week

Static site for the weekly photo newsletter: the home page is the most recent post, an archive has **Scroll / Grid / Calendar** views, and every week has its own page. Black by default, with a light/dark toggle. The build has no dependencies and needs Node 20 or newer.

```
issues/2024-w03/      one folder per post: 12 images, thumbnails, issue.json, text.txt
site.config.json      name, blurb, signup form URL (the form is parked, see below)
static/               style.css, app.js, favicon (copied as they are)
assets/               logo-white.png, logo-black.png (the old stacked logo, not used by the site, kept for the email or print)
build.mjs             generates dist/ from the above
scripts/add-post.mjs  makes a post from a folder of 12 images + a text file
vercel.json           tells Vercel to run `npm run build` and serve dist/
docs/SPEC.md          the full plan: design, sending, backfill, what is left to build
tests/                browser tests (Python + Playwright): `python3 tests/test_nav.py` (also test_footer.py, test_seam.py, test_balance.py, test_links.py, test_wide.py)
```

## What is in this version

- **SCROLL:** newest first, infinite scroll. Each post is its text, then its 12 images, with a thin rule between posts.
- **GRID:** a 3-column grid of one hero image per post, each labelled with its week number. Click one to open the post.
- **CALENDAR:** the same grid, split into months by horizontal dividers.
- **Header:** the name as plain text (**12 FRAMES PER WEEK**, or 12FPW on phones, always a link to the home page), **ARCHIVE** and **LIGHT/DARK**. ARCHIVE is a dropdown with SCROLL / GRID / CALENDAR: on desktop it opens when you hover over it (click pins it open), on phones you tap. On the archive it switches the view in place, anywhere else it opens the archive in that view.
- **Wide desktop screens (1200px and up):** LIGHT/DARK stands alone in the bottom-left corner; ARCHIVE is the far-right item in the header and in the scroll-up bar (TOP appears to its left in the bar), so it never moves. Narrower screens keep ARCHIVE, TOP and LIGHT together.
- **Scroll-up bar (every page):** scroll down and the header goes away; scroll back up and **ARCHIVE, TOP and LIGHT/DARK** slide in as one frosted (blurred, see-through) band across the top, feathered at its bottom edge: **12 FRAMES PER WEEK** at the left (a link home; 12FPW on phones), ARCHIVE / TOP / LIGHT at the right. It lingers for a second after you start scrolling down (and stays while the mouse is on it), so it does not vanish abruptly. TOP glides back up through the page, and while the ARCHIVE menu is open the same frosted layer extends down under it, so the bar and the menu read as one piece, with softly rounded bottom corners.
- **Home page** = the most recent post. An older week opened from the archive has a back-to-archive link at the top.
- The home page footer shows only today's date at the bottom right (live, from the visitor's device), as 26 OCTOBER 2026.
- Post pages live at `/2024/week-3/`.
- Real posts only: the placeholder demo posts were deleted on 2026-10-27 once the backfill started (2023 Weeks 1 to 14 so far).
- The **signup form is parked**: it is not shown on any page right now (a new spot is still to be chosen), and it is not connected to a mailing service yet. See `docs/SPEC.md` for the plan (Resend).

## Run it locally

```
npm install        # adds sharp, which add-post uses to read image sizes and make grid thumbnails
npm run dev        # builds, then serves http://localhost:3000
```

## Add a post

Put the 12 images in a folder (they are used in filename order) with a `text.txt` next to them, then:

```
npm run add-post -- ~/Desktop/week-3 --year 2025 --week 3 --hero 4 --push
```

- The hero (thumbnail in Grid and Calendar) is always image 1. `--hero N` still exists but is not used.
- `--push` commits and pushes, and Vercel redeploys in about a minute. Leave it off to look at the result first.
- Images are kept at FULL SIZE (copied byte for byte; HEIC/TIFF become a high-quality JPEG) and a 700px thumbnail is made for the grid. Each image links to a Google reverse-image search. A paragraph wrapped in asterisks in `text.txt` shows in italic grey, and `[words](https://address)` makes a link (underlined, slightly heavier). `python3 scripts/clipping_to_text.py clip.textClipping > text.txt` converts a Mac text clipping, keeping its links.
- A post's date comes from its week: Calendar uses the Thursday of that ISO week, so Week 1 of 2025 files under January 2025. To use the real send date, add `"date": "2025-01-09"` to the post's `issue.json`.

## Put it online

1. Push this folder to the GitHub repo.
2. In Vercel: Add New, then Project, import the repo, and accept the defaults. `vercel.json` sets the build command and output folder.
3. Every push to `main` redeploys. Attach the 12fpw.com domain under Project, Settings, Domains.
