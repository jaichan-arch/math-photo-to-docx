---
name: maths-photo-to-docx
description: Convert a photo, screenshot or handwritten maths page (HEIC, JPG, PNG) into a Word .docx with native equations intended for BrailleSense 6. Use when the user wants maths images transcribed into an accessible Word file.
---

# Maths Photo to Word

Use this when the user supplies a picture of maths (printed textbook page, worksheet, handwritten working, or a screenshot) and wants it as a Word file that a blind user can read and solve on BrailleSense 6. Output is a compact, single-column .docx. Use native Word equations (OMML) for calculation exercises and structural maths, one equation per paragraph with its label on the same line. Keep prose and simple values in ordinary text. Use plain formatting: no colour, no font-size changes, no extra spacing. Headings are bold; nothing else is styled.

The bundled generator is `scripts/math2docx.py`, relative to this skill directory. Run it using its resolved absolute path. Keep working images and specs in a temporary working directory; never modify the installed skill during a conversion. Save requested deliverables using the available file-saving workflow and return a downloadable link.

Requires Python 3 (standard library only for generation). Image optimisation uses Pillow and NumPy; HEIC decoding additionally needs pillow-heif. Check availability before using them. If a dependency cannot be installed, explain the limitation and request a supported image format when necessary. Do not claim BrailleSense compatibility has been tested unless it has.

## Content rules (apply to every job)

- **Remove writing space, preserve missing terms.** Leave out blank answer lines, dotted writing lines, name-entry lines and blank working areas. A missing operand, numerator or denominator is question content: represent it with the single character `□`, including where the source uses an underline. Do not draw boxes or insert the words “missing number” inside equations. Keep the source’s wording about the missing term.
- **No grids or tables.** Do not reproduce table or grid structures. Linearise question text and multiple-choice options into ordinary paragraphs, retaining each label and value. Briefly note that the layout was omitted. For a marks table, put its readable facts into a concise placeholder, for example: `[Table omitted: Section 1 is 8 marks; Section 2 is 46 marks; extension is 10 marks; printed total is 54 marks.]` Preserve printed totals even if inconsistent; do not silently recalculate them. Only refer the reader to the sender or photo when the content cannot be meaningfully linearised.
- **PDF uploads.** Do not try to read a PDF. Reply that the user should take a photo of each page and upload those instead, then stop and wait for the photos.

## Compact transcription rules

- Preserve the source wording, sentences, question order, marks and mathematical meaning. Do not rewrite a word problem into fragments such as “the following distance” followed by a detached equation.
- Keep simple numerical values, decimal comparisons, recurring decimals written with ellipses, and multiple-choice options as plain text on the same paragraph as their label: `(a) 0.64`, `A. 0.631 > 0.6311`.
- In prose and True/False statements, write simple fractions as `4/7` and mixed numbers as `4 1/2`. For example, `Express 1/6 as a recurring decimal:` and `Jane ran 4 1/2 km on Monday and 3 1/6 km on Tuesday.` Do not force these into display equations. These prose fractions are deliberately ordinary text, not native equations; do not claim that every fraction is OMML.
- Use native OMML for calculation exercises, algebraic fractions and standalone fraction-conversion items: `(a) [2|7]+[4|7]`, `(b) 9[3|7]-4[1|7]`, `(a) [3|5]`. Keep labels and expressions together. Use a centred display only when the source has an unlabelled standalone calculation or it follows wording such as “Simplify:”.
- Retain mixed-number meaning; never insert a multiplication sign between the whole number and its fractional part. Preserve algebraic juxtaposition such as `20fg`. Use `×` where multiplication is shown explicitly.
- Correct an unmistakably duplicated or skipped subpart label to the intended sequence, with one nearby `? ` note explaining both the printed label and the correction. Preserve ambiguous labels and flag them instead. Never change a mathematical value as an editorial correction.
- Flag only actual unreadable content, source inconsistencies or unsupported notation present in the question. Do not add a warning about notation that students are being asked to produce. A prompt asking students to rewrite `1.181818…` with recurring notation needs no recurring-dot warning.
- Do not reproduce the original blank space or page count. Use compact natural pagination. Keep headings with following content, and labels with their values. Do not add colours, enlarged headings, decorative elements or extra paragraph spacing.

## Workflow

1. **Locate the file.** Copy the upload to a scratch folder. Never edit the original.
2. **Convert HEIC to JPG if needed.** Use pillow-heif:
   ```python
   # pip install pillow-heif   (if missing)
   from pillow_heif import register_heif_opener
   from PIL import Image, ImageOps
   register_heif_opener()
   im = ImageOps.exif_transpose(Image.open('photo.heic')).convert('RGB')
   im.save('photo.jpg', quality=92)
   ```
3. **Optimise handwriting or print for reading.** Use flat-field correction, which evens out uneven lighting and shadows better than a global contrast boost (a plain contrast boost blew out the paper in testing). Requires `numpy` and `pillow`:
   ```python
   from PIL import Image, ImageOps, ImageFilter
   import numpy as np
   im = ImageOps.exif_transpose(Image.open(src)).convert('L')
   im = im.resize((im.width*3, im.height*3), Image.LANCZOS)
   bg = im.filter(ImageFilter.GaussianBlur(60))
   a = np.asarray(im).astype(float); b = np.asarray(bg).astype(float) + 1
   out = Image.fromarray(np.clip(a / b * 235, 0, 255).astype('uint8'))
   out = out.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))
   out = ImageOps.autocontrast(out, cutoff=0.5)
   out.save('optimised.png', optimize=True)
   ```
   View the result to check it. Deliver it as a file if the user asked for the cleaned image.
4. **Transcribe by eye, one spec per photo.** View each optimised image and write one spec file per photo (syntax below), following the compact transcription rules and retaining the source order and signs. Skip writing spaces and linearise table content as described above. Apply only clearly justified label corrections, with a note. Mark each photo's start with a `% Page N of M` comment line.
5. **Flag what you cannot see, in the file.** Do not stop to ask first. Mark each uncertain item on its own line with `? ` (for example, a trailing `= 1` cut off at the frame edge, a digit or letter that could be read two ways, or unsure bracket structure). These show up as `[Check: ...]` lines in the .docx so the user can correct them in one pass. Name the open checks in your reply.
6. **Combine pages if there are several photos.** Concatenate the spec files in page order into one `spec.txt`. The generator ignores `%` comment lines and warns if a heading appears twice, which catches a page pasted in twice.
7. **Build and check the .docx.** Run `python3 math2docx.py spec.txt out.docx`. The build runs its own check and exits non-zero on failure. The check confirms:
   - the number of equations matches the spec,
   - fractions and superscripts are complete,
   - the text in each equation, in order, matches the spec,
   - no heading appears twice,
   - pandoc can open the file and read the expected number of fractions back (when pandoc is installed).
   If the check fails, fix the spec and rebuild. Do not deliver a failing file.
8. **Validate and inspect.** Use the available document-validation and rendering workflow when possible; preserve native OMML equations. Inspect any successful render, and report which checks actually ran. Rendering availability varies; do not assume LibreOffice cannot render equations. A render or XML check does not establish braille-device accessibility. Ask the user to verify the result in Word and on BrailleSense 6, and disclose if rendering or device testing was unavailable.
9. **Deliver** the .docx to the user.

## Spec syntax (one block per line)

- `% text` : comment, never printed (use for `% Page N of M` markers)
- `# text` : bold heading paragraph (e.g. question number)
- `= expr` : centred display equation on its own paragraph
- `(a) expr` : label followed by an inline equation on the same line. The line is treated as maths only if the expression contains a symbol such as `=`, `+`, `-`, `×`, `÷`, `^` or `[`. Otherwise it is printed as plain text. Use that plain-text behaviour for labelled decimals; do not split the label onto a separate line.
- `? text` : a check for the user, printed as `[Check: text]`
- `text` : plain paragraph (question wording, explanations, and grid placeholders such as `[Grid omitted: ...]`)
- Inside expressions: `[num|den]` is a fraction and nests, `x^2` or `x^{10}` is a superscript, `×` is multiplication, `÷` is division. Everything else is upright text.
- `□` represents an intentional missing term, including inside `[15a|□]`.
- Write multiplication as `×` where the page shows it; preserve mixed numbers and algebraic juxtaposition.

Example spec:
```
% Page 1 of 1
# Question 1
= ([(3x+y)×40z|25y])×5x+([4y^3|x]×5z)=1
? Is the trailing "= 1" cut off by the frame edge?
# Question 2
= 3x+y=13
(a) [2x|2]
Explain why the answer is 4z.
[Grid omitted: ask the sender to describe it, or see the original photo.]
(b) x^{10}-3=7
```

## Generator limits

The supplied notation supports fractions and single-character superscript bases with text exponents. It does not encode radicals, subscripts, matrices, or powers of a grouped expression or fraction structurally. Do not silently flatten unsupported maths into apparently valid equations. Flag affected items with `? ` checks and explain the limitation. The checker establishes consistency with the spec, not accuracy against the photo; compare the transcription with the source separately. Labelled expressions without a recognised maths symbol are plain text; this is intentional for decimals and short answers. Fractions use `[num|den]` to become native equations. Keep simple fractions in prose as slash text. Do not work around this distinction by splitting labels and values into separate paragraphs.

## Checks before delivering

- Every question and mathematical item appears once in order, with its label; prose fractions and simple values may be plain text as specified above.
- No writing lines or drawn answer boxes remain. Intentional missing terms remain as `□`.
- Table and grid structures are omitted; readable question content, options and marks summaries are retained in linear form.
- Every uncertain item appears as a `[Check: ...]` line and is named in the reply.
- The generator check passed (equation count, text order, no duplicate headings, pandoc round-trip where available).
- Signs, brackets, values and wording match the page. Any label correction is disclosed. No artificial notation warnings are added.
- Give the user the .docx and, if relevant, the cleaned image. Name any assumptions in one or two lines.
