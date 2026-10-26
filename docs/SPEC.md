# 12 Frames Per Week: site and sending pipeline spec (updated 2026-10-26)

Replaces the old Mailchimp-based plan. The site and the email come from the same post data.
Repo: github.com/shakadunk/12fpw. Domain: 12fpw.com (currently serving the Mailchimp archive).

## Status
- DONE (demo): black site with SCROLL, GRID and CALENDAR views, post pages, signup form (not connected), light/dark toggle, `scripts/add-post.mjs` to make a post from 12 images + text. Demo posts reuse 12 sample images; delete them before launch.
- TO BUILD: private upload page, email rendering, sending via Resend, signup endpoint, backfill of the old posts, moving 12fpw.com to Vercel.
- BLOCKER: Claude's GitHub connection could not see shakadunk/12fpw, so nothing has been pushed yet. The repo needs to be added under the Claude GitHub app's repository access.

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
- The Mailchimp archive pages block automated readers. Method that works: Safari "Print as PDF" on each archive page, then a script pulls the text and the 12 images from each PDF (tested on Week 3: text and images extract cleanly). Extracted images are the emailed size (about 750px wide), so original files are better where they exist.
- PDFs say "Week N" but not the year. Posts were weekly from Week 1 of 2024, so year plus week determines the date. Ask about any skipped weeks.
- Old Mailchimp links will break once 12fpw.com moves; that is accepted as long as the posts are in the new archive.

## Technical notes
- Uploads must go straight to storage, not through a serverless function: Vercel's per-request size limit (about 4.5 MB, to verify) is too small for 12 photos.
- Source of truth is the GitHub repo (issues/<year>-w<week>/); Vercel redeploys on push. If the portal needs to publish without a git push, fall back to Vercel Blob with the site reading from it.
- The portal and sending code need npm packages; build and test them with Claude Code on Shaka's Mac. The cloud sandbox cannot reach the npm registry.
- Repo size: about 2 MB per post after resizing, so 60 posts is roughly 120 MB. Commit only resized images.

## Still open
- Any skipped weeks in 2024 and early 2025
- How to get the 60 posts' content out (PDF per post, or original files)
- Approval UX: preview link plus an Approve button on the upload page
- Logo: keep the current one (hanging "1") or try new options
