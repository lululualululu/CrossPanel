# CrossPanel

**From Dispersed Observations to Grounded Experimental Conclusions**

[Project page](https://lululualululu.github.io/CrossPanel/)

CrossPanel studies evidence-grounded reasoning across scientific figure panels, including object selection, condition resolution, cross-panel correspondence, and target evidence reading.

This is a preliminary project website. The manuscript, authorship information, dataset, evaluation code, and citation will be added when ready. The subtitle is descriptive project copy, not a finalized paper title.

## Current contents

- Overview and task motivation
- Dataset construction and distribution
- Preliminary model comparison and case analysis
- Five figures with full-resolution previews and font-embedded PDFs

The current collection contains 2,650 questions (248 region-grounded and 2,402 dependency-oriented). Figure 4 reports a 251-question evaluation set; Figure 5 reports a 57-question analysis set. These scopes are distinct. Detailed evaluation protocols will accompany the manuscript.

## Update the website

The site is plain HTML/CSS with no build dependencies. GitHub Pages serves `main` from the repository root.

- Edit title, introduction, resource links and section descriptions in `index.html`.
- Edit typography, colors and responsive layout in `style.css`.
- Replace `assets/figures/figure-1.webp` through `figure-5.webp` to update previews.
- Replace the corresponding `assets/pdfs/figure-N.pdf` files to update downloadable figures.
- Update image `width` and `height` attributes when aspect ratios change.
- When paper/data/code links exist, replace their `span.pill.pending` elements with `a.pill` links. Remove the “Coming soon” labels.
- Add the finalized authors/affiliations, abstract, release licenses and BibTeX only when confirmed.
- Push to `main`; GitHub Pages automatically republishes the site.

Local preview:

```sh
python3 -m http.server 8000
```

Then visit http://localhost:8000.

## Attribution and rights

Project-page organization is inspired by [MC-Bench](https://xuyunqiu.github.io/MC-Bench/). Website implementation is original; no template code was copied. Scientific figures may contain excerpts of third-party publications. No blanket license for the figures or future dataset is granted by this repository; release-specific licensing will be documented separately.
