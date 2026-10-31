# math-photo-to-docx

Turn a photo, screenshot or handwritten maths page into a Word (.docx) file of native, editable equations, laid out so a blind user can read and solve it on a BrailleSense 6.

The output uses real Word equations (OMML), one equation per paragraph, question labels as plain text, and no colour or size styling, so it reads cleanly on braille displays.

## What's in this repo

| Folder | Version | Status |
|---|---|---|
| `claude/` | Claude skill: `SKILL.md` (instructions) and `math2docx.py` (generator) | Ready |
| `chatgpt/` | Custom GPT version | Not yet added |
| `gemini/` | Gemini Gem version | Not yet added |

## Claude version

### What you need

- Python 3.8 or newer. No extra packages are needed to build the .docx.
- For photo clean-up only: `pip install pillow-heif pillow numpy`
- Optional: [pandoc](https://pandoc.org), which enables an extra round-trip check.

### Using it

1. Put `SKILL.md` and `math2docx.py` where your Claude setup can load them (see the Claude skills documentation for your platform).
2. Upload a photo of each page. Photos work better than PDFs. Upload a PDF and the skill will ask you to send photos instead.
3. Claude transcribes the page into a plain-text spec and runs the generator:

   ```bash
   python3 math2docx.py spec.txt out.docx
   ```

4. The generator checks the file before it's delivered: equation count, fractions and superscripts complete, equation text in order, no duplicate headings, and a pandoc read-back if pandoc is installed.

### Running the generator on its own

If you already have a spec file, you can build the .docx without Claude:

```bash
python3 claude/math2docx.py spec.txt out.docx          # build and check
python3 claude/math2docx.py spec.txt out.docx --no-check  # build only
```

The spec format is described in `claude/SKILL.md`. A short example:

```
% Page 1 of 1
# Question 1
= 3x+y=13
(a) [2x|2]
Explain why the answer is 4z.
? Is the trailing "= 1" cut off by the frame edge?
```

## Limits and things to check

- **Transcription is by eye.** The AI reads the photo and writes the spec, so it can misread a digit or sign. Any uncertain item is marked `[Check: ...]` in the .docx so it can be fixed before the file goes to the user.
- **Not visually verified.** The checks confirm the file's structure and equation text, but LibreOffice does not render these equations, so nobody has seen the rendered page. Open the file in Word and on BrailleSense 6 before relying on it.
- **Grids and tables are not reproduced.** They are replaced with a placeholder explaining what was left out.
- **Answer lines are removed** from the output.

## Privacy

Do not commit real student or personal photos, or the .docx files made from them. `.gitignore` excludes common image, PDF and Word output formats, but check `git status` before each commit.

## Licence

MIT. See [LICENSE](LICENSE).
