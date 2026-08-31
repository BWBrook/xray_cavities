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

PASA's definitive LaTeX template uses `pasa-mnras.bst`. No dedicated PASA CSL
was available from the Citation Style Language repository when this scaffold
was created. The committed Cambridge University Press author-date CSL is a
transparent draft/review analogue for `makedoc` PDF and DOCX builds, not a
claim of exact final PASA typesetting. Final submission preparation should
validate the references against PASA's current LaTeX template.

Authorship injection is intentionally disabled until the author list and order
are agreed. Once agreed, create `manuscript/authors.yaml` from the template and
add `author_metadata: ../manuscript/authors.yaml` to both profiles.

PASA author guidance:
<https://www.cambridge.org/core/journals/publications-of-the-astronomical-society-of-australia/information/author-instructions/preparing-your-materials>
