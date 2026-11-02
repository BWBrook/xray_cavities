# Manuscript workflow

This repository owns the manuscript sources and generated review outputs.
`makedoc` remains the external build engine at `/Users/bwbrook/work/makedoc`;
no manuscript files are copied into that repository.

## Layout

- `text/main.md`: canonical manuscript body
- `text/figures.md`: selected paper figures and captions
- `figures/`: selected manuscript figures only
- `authors.template.yaml`: authorship schema to complete after author list and order are agreed
- `../references/refs.yaml`: canonical Pandoc bibliography
- `../csl/`: citation style used for draft PDF/DOCX builds
- `../settings/build.yaml`: `makedoc` draft and submission profiles

Generated outputs are written under the ignored `build/manuscript/` tree.

## Commands

Run these from the `xray_cavities` repository root:

```bash
make manuscript-validate
make manuscript-draft
make manuscript-submission
make manuscript-all
make manuscript-check
```

`manuscript-check` applies the strict submission-profile lint, citation audit,
configuration checks, and PDF/DOCX build. The ordinary draft target remains
fast enough for iterative writing.

## PASA contract

The target journal is the *Publications of the Astronomical Society of
Australia* (PASA). Drafting should use Australian English, a maximum 400-word
abstract, one to six Unified Astronomy Thesaurus keywords, and full labels such
as "Figure", "Equation", and "Section".

PASA's definitive LaTeX template uses `pasa-mnras.bst`. The CSL repository and
the Zotero style index still had no PASA or MNRAS style on 2 November 2026. The
nearest independent astronomy style is `the-astrophysical-journal`, whose AAS
author–year format is close to MNRAS's. The committed Cambridge University Press
author-date CSL is a transparent draft/review analogue for `makedoc` PDF and
DOCX builds, not a claim of exact final PASA typesetting. When the text
matures, switch to the ApJ CSL or derive a PASA CSL from it, and check the
references against PASA's current LaTeX template before submission.

## References workflow

The agents keep a plain-text list of identifiers, one DOI (or ISSN, ISBN or
arXiv ID) per line. Barry imports it with Zotero's magic-wand tool and exports
the collection as Better BibTeX CSL YAML to `../references/refs.yaml`, which
`makedoc` reads. Citation keys in the text must match the exported keys.

## Products from one living repository

The repository is the primary scientific record, licensed CC BY-SA for text
and MIT for code. Each written product is a snapshot drawn from it:

1. **Journal article** (`text/main.md`, PASA). Tag a release with a Zenodo
   DOI at each submission and revision.
2. **Two-page brief.** At most two A4 pages, so that it prints as a single
   double-sided sheet. It states the core findings for a broad audience,
   including interested lay readers, and is maintained as an output in its
   own right, not as an abstract of the article.
3. **Agent guide.** As long as it needs to be, written so that a new agent can
   use the work fully: the claims and their evidence, conventions, dead ends,
   reproduction commands and open questions. Its form is experimental.

All three should draw on the same evidence and must not drift apart. None
should be drafted until the boundary-control result is in and a cavity
detector has passed.

Authorship injection is intentionally disabled until the author list and order
are agreed. Once agreed, create `manuscript/authors.yaml` from the template and
add `author_metadata: ../manuscript/authors.yaml` to both profiles.

PASA author guidance:
<https://www.cambridge.org/core/journals/publications-of-the-astronomical-society-of-australia/information/author-instructions/preparing-your-materials>
