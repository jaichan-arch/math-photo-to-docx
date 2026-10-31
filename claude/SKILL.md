---
name: math-photo-to-docx
description: Convert a photo, screenshot or handwritten maths page (HEIC, JPG, PNG) into a Word .docx of native equations for BrailleSense 6.
---

# Maths photo or handwriting to BrailleSense-ready .docx

Use this when the user supplies a picture of maths (printed textbook page, worksheet, handwritten working, or a screenshot) and wants it as a Word file that a blind user can read and solve on BrailleSense 6. Output is a .docx with native Word equations (OMML), one equation per paragraph, question labels as plain text, and plain formatting: no colour, no font-size changes, no extra spacing. Headings are bold; nothing else is styled.

The generator script `math2docx.py` sits next to this file. Copy both into a scratch folder before starting.

## Content rules (apply to every job)

- **Remove answer lines.** Transcribe the questions and the working the user needs to read, but leave out blank answer lines, dotted answer lines and empty answer boxes. Do not add them back.
- **No grids or tables.** Grids (for example, a tic-tac-toe style grid or a number grid) and tables are hard to read on a braille device. Do not reproduce them. Put a placeholder paragraph in their place that tells the braille user what was left out and how to get it, for example: `[Grid omitted: ask the sender to describe it, or see the original photo.]`
- **PDF uploads.** Do not try to read a PDF. Reply that the user should take a photo of each page and upload those instead, then stop and wait for the photos.

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
4. **Transcribe by eye, one spec per photo.** View each optimised image and write one spec file per photo (syntax below), keeping the same order, labels and signs as the page. Skip answer lines and replace any grid or table with the placeholder from the content rules. Mark each photo's start with a `% Page N of M` comment line.
5. **Flag what you cannot see, in the file.** Do not stop to ask first. Mark each uncertain item on its own line with `? ` (for example, a trailing `= 1` cut off at the frame edge, a digit or letter that could be read two ways, or unsure bracket structure). These show up as `[Check: ...]` lines in the .docx so the user can correct them in one pass. Name the open checks in your reply.
6. **Combine pages if there are several photos.** Concatenate the spec files in page order into one `spec.txt`. The generator ignores `%` comment lines and warns if a heading appears twice, which catches a page pasted in twice.
7. **Build and check the .docx.** Run `python3 math2docx.py spec.txt out.docx`. The build runs its own check and exits non-zero on failure. The check confirms:
   - the number of equations matches the spec,
   - fractions and superscripts are complete,
   - the text in each equation, in order, matches the spec,
   - no heading appears twice,
   - pandoc can open the file and read the fractions back (when pandoc is installed).
   If the check fails, fix the spec and rebuild. Do not deliver a failing file.
8. **Validate the package** if a validator is available (for example, the docx skill's `validate.py`). LibreOffice does not render these equations, so visual checks are not possible in most environments. Say so, and ask the user to open the file in Word and on BrailleSense 6.
9. **Deliver** the .docx to the user.

## Spec syntax (one block per line)

- `% text` : comment, never printed (use for `% Page N of M` markers)
- `# text` : bold heading paragraph (e.g. question number)
- `= expr` : centred display equation on its own paragraph
- `(a) expr` : label followed by an inline equation on the same line. The line is treated as maths only if the expression contains a symbol such as `=`, `+`, `-`, `×`, `÷`, `^` or `[`. Otherwise it is printed as plain text.
- `? text` : a check for the user, printed as `[Check: text]`
- `text` : plain paragraph (question wording, explanations, and grid placeholders such as `[Grid omitted: ...]`)
- Inside expressions: `[num|den]` is a fraction and nests, `x^2` or `x^{10}` is a superscript, `×` is multiplication, `÷` is division. Everything else is upright text.
- Write multiplication as `×` where the page shows it or where juxtaposition could be misread. State the choice to the user.

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

## Checks before delivering

- Every equation in the photo appears once, in order, with its label.
- No answer lines, dotted lines or empty boxes remain in the output.
- Every grid or table is replaced by a placeholder paragraph, not reproduced.
- Every uncertain item appears as a `[Check: ...]` line and is named in the reply.
- The generator check passed (equation count, text order, no duplicate headings, pandoc round-trip where available).
- Signs and brackets match the page.
- Give the user the .docx and, if relevant, the cleaned image. Name any assumptions in one or two lines.
