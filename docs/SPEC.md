# 12 Frames Per Week: site and sending pipeline spec (updated 2026-10-26)

Replaces the old Mailchimp-based plan. The site and the email come from the same post data.
Repo: github.com/shakadunk/12fpw. Domain: 12fpw.com (currently serving the Mailchimp archive).

## Status
- DONE (demo, live on Vercel at 12fpw.vercel.app): black site with SCROLL, GRID and CALENDAR views, post pages, signup form (not connected), light/dark toggle, slim VIEW/TOP bar in the archive, `scripts/add-post.mjs` to make a post from 12 images + text. Demo posts reuse 12 sample images; delete them before launch.
- WORKFLOW: Shaka describes a change, Claude confirms details, edits, tests, and pushes to the GitHub repo; Vercel redeploys automatically. Claude can push to shakadunk/12fpw (the Claude GitHub App is installed on the repo).
- TO BUILD: backfill of the old posts, private upload page, email rendering, sending via Resend, signup endpoint, moving 12fpw.com to Vercel.

## Old template (from Week 3 and Week 4)
- White background, one centered column about 600px wide, Helvetica/Arial.
- Logo top-left: "12 / FRAMES / PER WEEK", bold, three stacked lines, with the "1" in 12 hanging to the left of FRAMES and PER (deliberate kerning). The logo was a PNG; a white-on-transparent copy is at static/logo.png. Open to a new logo.
- Centered "Week N" in small gray with a short thin rule under it.
- Body text about 15px, line height about 1.7, short paragraphs, then a sign-off such as "In blue," / "SD" on separate lines.
- 12 images stacked at full column width, uncropped, no captions.
- Footer: "12FPS 2024", a Boston postal address, an underlined Unsubscribe link.
- Week number is week of the year.

## Design (new)
- Pure black (#000) background, white text, full-color images floating on black. Light/dark toggle kept as a secondary option.
- Each post = "Week N" label with rule, text, then exactly 12 images. One of the 12 is the hero.
- SCROLL: newest first, infinite scroll, thin horizontal rule between posts.
- GRID: Instagram-style grid of hero images (3 columns, square crops), each labelled with its week number. Click opens the post.
- CALENDAR: the GRID, split into months with horizontal dividers.
- Footer: on the home page the footer is just today's date at the bottom right (e.g. OCTOBER 26, 2026), shown in small uppercase type and filled in live from the visitor's device, so it rolls over at midnight if the page stays open. No copyright line, because most of the images are not Shaka's. The archive and post pages keep the older footer (site name plus Archive / Subscribe links) for now.
- A post's calendar month comes from the Thursday of its ISO week (Week 1 of 2025 starts Dec 30, 2024 but files under January 2025). A post's issue.json can carry a real "date" to override.

## Email
- Colorless on purpose: just text and images, no background or text colors set, so it follows each reader's light/dark setting.
- A black PNG logo would vanish in dark mode, so use live text for the logo in the email (indent the other two lines to keep the hanging "1"), or switch to a new logo.
- Footer keeps the postal address and an unsubscribe link (both legally required).

## Process
1. Shaka submits raw text + 12 images on a private, password-protected upload page on the site.
2. The pipeline builds the post, publishes a preview, and sends a test email to Shaka.
3. Shaka approves. Nothing reaches subscribers before that.
4. On approval the post goes live and the email goes to subscribers.
5. The email uses the site's hosted image URLs. No Mailchimp.

## Sending
- Expected list: under 100 subscribers.
- Resend free plan: 3,000 emails/month, 100/day cap, can also receive email. Check audience and contact limits at setup.
- Past 100 subscribers: upgrade or switch (Brevo free is 300/day with its branding; Amazon SES is about $0.16 per 1,000). Keep the sending code provider-agnostic.
- Sending from 12fpw.com needs SPF/DKIM records.
- The signup form adds people to the provider's list; the provider handles unsubscribe links.

## Archive backfill (about 60 posts)
- Week 1 was in 2024, and posts ran through the first few weeks of 2025.
- Plan: Shaka has the original images grouped by week in Adobe Bridge. He uploads zips (about 8 to 10 weeks each; start with a batch of 3 or 4) with one folder per week named `<year>-w<NN>`, 12 images numbered in order, a `text.txt`, and an optional `hero.txt` holding the hero image number. Claude processes each batch with `scripts/add-post.mjs`, pushes, and the site fills in.
- Fallback: the Mailchimp archive pages block automated readers, but Safari "Print as PDF" works: a script can pull the text and the 12 images from each PDF (tested on Week 3). Extracted images are only the emailed size (about 750px wide), so originals are better.
- PDFs say "Week N" but not the year. Posts were weekly from Week 1 of 2024, so year plus week determines the date. Ask about any skipped weeks.
- Old Mailchimp links will break once 12fpw.com moves; that is accepted as long as the posts are in the new archive.

## Technical notes
- Uploads must go straight to storage, not through a serverless function: Vercel's per-request size limit (about 4.5 MB, to verify) is too small for 12 photos.
- Source of truth is the GitHub repo (issues/<year>-w<week>/); Vercel redeploys on push. If the portal needs to publish without a git push, fall back to Vercel Blob with the site reading from it.
- Shaka does not want to install Claude (Claude Code) on his work computer, so everything must run in the browser and on Vercel. The cloud sandbox cannot reach the npm registry, so the portal and sending code should use only what Node already includes, or be built so Vercel installs any packages at deploy time.
- Repo size: about 2 MB per post after resizing, so 60 posts is roughly 120 MB. Commit only resized images.

## Archive slim bar (added 2026-10-26)
- In the archive (all three views), a slim text-only bar slides in when the reader scrolls up: VIEW on the left (opens a menu: Scroll / Grid / Calendar) and TOP on the right (glides back to the top and keeps the current view). TOP animates: ease in-out, about 0.45s for a short climb up to a cap of 1.4s for long ones, the bar stays on screen during the trip and hides on arrival, any wheel/touch/key/mouse press stops the glide where you are, and readers with reduced-motion settings get an instant jump. It hides again on scroll down and is not shown at the top of the page, on post pages or on the home page.
- Look: see-through blurred bar (about 30% black tint in the dark theme, 30% white in the light theme, 14px blur) that stays slim (about 37px) and feathers out over its last ~18px, so it dissolves into the photo instead of ending in a hard edge. On desktop, VIEW and TOP sit about 520px apart (pulled in toward the middle); on phones they sit at the screen margins. The VIEW menu has no panel of its own: when it opens, the bar's see-through blurred area grows downward to hold it (one continuous block, feathered at the bottom), with the current view in full white and the others dimmed. In the light theme the tint is firmer (about 55%) while the menu is open so the labels stay readable.
- REVISIT once the backfill starts: with 60+ posts, decide whether the bar should also appear on post pages or the home page, and whether the bar's behavior and size feel right.

## Still open
- Revisit the slim bar (see above) once the backfill is in
- Any skipped weeks in 2024 and early 2025
- How to get the 60 posts' content out (PDF per post, or original files)
- Approval UX: preview link plus an Approve button on the upload page
- Logo: keep the current one (hanging "1") or try new options
