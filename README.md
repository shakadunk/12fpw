# 12 Frames Per Week

Static site for the weekly photo newsletter: a signup page, an archive with **Scroll / Grid / Calendar** views, and one page per weekly post. Black by default, with a light/dark toggle. The build has no dependencies and needs Node 20 or newer.

```
issues/2024-w03/      one folder per post: 12 images, thumbnails, issue.json, text.txt
site.config.json      name, blurb, signup form URL
static/               style.css, app.js, logo.png, favicon (copied as they are)
build.mjs             generates dist/ from the above
scripts/add-post.mjs  makes a post from a folder of 12 images + a text file
vercel.json           tells Vercel to run `npm run build` and serve dist/
docs/SPEC.md          the full plan: design, sending, backfill, what is left to build
```

## What is in this version

- **SCROLL:** newest first, infinite scroll. Each post is its text, then its 12 images, with a thin rule between posts.
- **GRID:** a 3-column grid of one hero image per post, each labelled with its week number. Click one to open the post.
- **CALENDAR:** the same grid, split into months by horizontal dividers.
- A slim **VIEW / TOP** bar that slides in when you scroll up in the archive (VIEW opens a Scroll / Grid / Calendar menu; TOP glides back up through the page and keeps your view). It is a see-through, blurred strip with a feathered bottom edge, and the strip grows to hold the VIEW menu when it is open.
- The home page footer shows only today's date at the bottom right (live, from the visitor's device).
- **Post pages** at `/2024/week-3/`, the logo, and a home page with the signup form.
- A Week 3 post with real text, plus 11 demo posts that reuse the same 12 images. **Delete every folder in `issues/` before the real launch.**
- The signup form is not connected yet. See `docs/SPEC.md` for the plan (Resend).

## Run it locally

```
npm install        # adds sharp, which add-post uses to resize images
npm run dev        # builds, then serves http://localhost:3000
```

## Add a post

Put the 12 images in a folder (they are used in filename order) with a `text.txt` next to them, then:

```
npm run add-post -- ~/Desktop/week-3 --year 2025 --week 3 --hero 4 --push
```

- `--hero` is which image (1 to 12) is the thumbnail in Grid and Calendar. Default is 1.
- `--push` commits and pushes, and Vercel redeploys in about a minute. Leave it off to look at the result first.
- Images are resized to 1600px on the long edge and a thumbnail is made for each, so the repo stays small. Do not commit full-size originals.
- A post's date comes from its week: Calendar uses the Thursday of that ISO week, so Week 1 of 2025 files under January 2025. To use the real send date, add `"date": "2025-01-09"` to the post's `issue.json`.

## Put it online

1. Push this folder to the GitHub repo.
2. In Vercel: Add New, then Project, import the repo, and accept the defaults. `vercel.json` sets the build command and output folder.
3. Every push to `main` redeploys. Attach the 12fpw.com domain under Project, Settings, Domains.
