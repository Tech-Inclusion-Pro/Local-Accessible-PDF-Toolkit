# Accessible PDF Toolkit (APT)

<p align="center">
  <img src="assets/logo.png" alt="APT Logo - A document with tools icon" width="200"/>
</p>

<p align="center">
  <strong>Make your PDFs easy for everyone to read!</strong>
</p>

<p align="center">
  <a href="#what-is-this-app">What Is This?</a> •
  <a href="#how-to-install">How to Install</a> •
  <a href="#how-to-use">How to Use</a> •
  <a href="#need-help">Need Help?</a>
</p>

---

## What Is This App?

The **Accessible PDF Toolkit** helps you make PDF files easier for everyone to read. This includes people who:

- Use **screen readers** (software that reads text out loud)
- Have **trouble seeing**
- Need documents to follow **accessibility rules**

### Your Files Stay Private!

This app runs on **your computer only**. Your files never leave your machine. This makes it safe for:
- Student records (FERPA)
- Medical information (HIPAA)
- Any private documents

---

## What Can This App Do?

| Feature | What It Does |
|---------|--------------|
| **Check PDFs** | Find accessibility problems including contrast, tables, links, and reading order |
| **Fix PDFs** | Auto-fix titles, language, tags, headings, and image descriptions |
| **AI Helper** | Get smart suggestions and AI-generated image alt text from AI on YOUR computer |
| **Show Me Walkthroughs** | Step-by-step guides for tasks that need external tools (like Adobe Acrobat) |
| **Progress Tracker** | Visual dashboard showing remediation status across 14 WCAG categories |
| **WCAG Explainer** | "Why does this matter?" tooltips on every issue, explaining who is affected |
| **Issue Priority Queue** | Issues sorted by impact: Level A errors first, screen-reader blockers highlighted |
| **Compliance Reports** | Generate HTML accessibility audit reports with actions taken and remaining items |
| **Document Memory** | Remembers your progress across sessions - see your previous score when reopening |
| **Before/After Audit Log** | Tracks every change made (title set, alt text added, etc.) for accountability |
| **Batch Process** | Validate and fix multiple PDFs at once via Tools > Batch Process |
| **Export HTML** | Turn PDFs into accessible web pages (via File menu) |
| **Undo / Redo** | Undo any tag edit or auto-fix with Ctrl+Z / Ctrl+Shift+Z |
| **Accessibility Settings** | Full suite of display accommodations with live preview |
| **Stay Private** | Everything stays on your computer - nothing goes online! |

---

## What's New (v1.4.0)

### Two Modes: AI-Handled and Show Me

The app now operates in two complementary modes so AI never leaves you at a dead end:

- **AI-Handled** - For issues the app can fix directly (title, language, tags, headings, alt text). Ollama generates copy-ready output and applies it with one click.
- **Show Me** - For tasks that require external tools (like Adobe Acrobat Pro). The app provides step-by-step guided walkthroughs so you always know exactly what to do next.

### Show Me Walkthroughs (7 Guides)

Step-by-step instructions for tasks that need hands-on work in external tools:

| Walkthrough | Steps | What It Covers |
|-------------|-------|----------------|
| Tag the Document Structure | 6 | Opening the tag tree, creating parent tags, auto-tagging pages |
| Fix Reading Order | 4 | Using the Order panel in Acrobat to reorder content |
| Apply Artifacts | 3 | Marking decorative elements so screen readers skip them |
| Table Headers and Scope | 4 | Setting TH tags and row/column scope on table cells |
| Set Tab Order for Forms | 3 | Configuring form field tab order for keyboard navigation |
| Security Settings | 3 | Ensuring security settings allow screen reader access |
| Screen Reader Testing | 4 | Running NVDA/VoiceOver to verify your fixes work |

### 11 New AI Capabilities

All running locally on your machine via Ollama:

| Capability | What It Does |
|------------|--------------|
| Correct Heading Outline | Fixes skipped heading levels and mis-leveled headings |
| Rewrite Link Text | Rewrites generic "click here" links to descriptive text |
| Suggest Contrast Fixes | Recommends replacement colors for low-contrast elements |
| Suggest Document Metadata | Suggests title, language, and subject from content |
| Generate Graph Descriptions | Long-form chart and graph descriptions for complex visuals |
| Generate Form Labels | Labels and tooltips for unlabelled form fields |
| Draft Captions and Footnotes | Captions for figures and footnote text |
| Suggest Non-Color Cues | Text labels, icons, and patterns for color-only information |
| Review OCR Accuracy | Flags likely OCR errors in specialized terminology |
| Generate Bookmark Structure | Builds bookmark hierarchy from heading structure |
| Generate Math Alt Text | Spoken-math descriptions for equations and formulas |

### Progress Tracker

A visual dashboard in the right panel showing remediation status across 14 categories:

- Document Title, Document Language, Language of Parts
- Tagged PDF, Reading Order, Headings, Alternative Text
- Tables, Links, Color Contrast, Bookmarks
- Forms, Artifacts, Security Settings

Each category shows: Not Started, In Progress, or Complete with an overall progress bar.

### WCAG Explainer Layer

Every issue now has a "Why does this matter?" toggle that reveals:
- **What this means** - plain-language explanation of the WCAG criterion
- **Who it affects** - which users are impacted (blind, low-vision, motor, etc.)
- **Real-world barrier** - a concrete example of the accessibility failure

Covers all 12 WCAG criteria checked by the app (1.1.1 through 4.1.2).

### Issue Priority Queue

Issues are now sorted by real-world impact:
1. WCAG Level A errors first (most critical)
2. Then AA, then AAA
3. Within each level: ERROR > WARNING > INFO
4. Screen-reader-blocking criteria (1.3.1, 1.3.2, 1.1.1, 2.4.2, 3.1.1) prioritized

### Compliance Report Generator

Generate a full HTML accessibility audit report from Tools > Generate Compliance Report:
- Executive summary with score, level, and pass/fail status
- All issues found, grouped by WCAG criterion with severity badges
- Actions taken (from the audit log)
- Remaining items needing manual review
- The report itself is WCAG-compliant with proper headings, lang attribute, and semantic HTML

### Document Profile Memory

The app remembers your documents across sessions:
- Recognizes returning documents by file hash (SHA-256)
- Shows your previous compliance score when reopening a file
- Tracks session count, resolved criteria, and persistent issues
- Helps you pick up exactly where you left off

### Before/After Audit Log

Every accessibility change is logged:
- What was changed (action, criterion, page)
- Original value and new value
- Feeds into compliance reports for accountability

### Bug Fixes

- **Fixed: Score stuck at 82% after auto-fix** - The alt text map was never refreshed after adding image descriptions, causing the validator to always report images as missing alt text. Now refreshed automatically.
- **Fixed: Blank image boxes in AI Suggestions** - Image detection now provides meaningful descriptions and editable fields instead of blank entries.
- **Fixed: Changes not persisting across sessions** - PDF is now auto-saved to disk after every fix, and the compliance score is stored in the document profile.
- **Fixed: Validation score not updating after fixes** - Suggestion apply, document property changes, and wizard inline fixes now all trigger re-validation.
- **Fixed: Heading tags not persisted to PDF** - Auto-fix heading tagging now writes to the PDF structure tree (not just in-memory).
- **Fixed: Figure tags missing page reference** - Structure elements now include /Pg so alt text maps correctly to pages.

### What was new in v1.3.0

#### Accessibility Settings with Live Preview
- **High Contrast Mode** - black background with white text for maximum readability
- **Reduced Motion** - disables all animations including toggle switch transitions
- **Large Text Mode** - scales all fonts by 125% across the entire application
- **Enhanced Focus Indicators** - adds bright yellow 4px focus rings and thicker borders on all interactive controls
- **Dyslexia-Friendly Font** - switches to OpenDyslexic (or Comic Sans MS / Arial fallback) with increased letter and word spacing
- **Color Blindness Accommodation** - remaps all brand colors app-wide for Deuteranopia, Protanopia, Tritanopia, or Monochrome vision
- **Custom Cursor Styles** - Large Black, Large White, Large Crosshair, High Visibility, and animated Cursor Trail
- **Live Preview** - every accessibility setting previews instantly as you toggle it, no save required

#### Animated Toggle Switches
- All checkbox controls replaced with custom animated toggle switches
- Smooth sliding thumb animation with color interpolation
- Full keyboard accessibility (Tab to focus, Space/Enter to toggle)
- Respects Reduced Motion setting (snaps instead of animating)
- Color-blind-aware (toggle color updates with color blindness mode)

### What was new in v1.2.0

#### Validation Improvements
- **Real image alt text checking** - walks the PDF structure tree instead of always reporting missing
- **Color contrast analysis** - checks every text element against WCAG luminance thresholds (AA and AAA)
- **Heuristic table detection** - finds untagged tables by detecting grid-like text patterns
- **Untagged link detection** - finds hyperlinks that exist as annotations but lack Link structure tags
- **Smarter reading order** - detects multi-column layouts and warns when reading order may be wrong

#### Features
- **Batch processing** - validate and auto-fix multiple PDFs at once (Tools > Batch Process)
- **AI-powered alt text** - auto-fix uses your local AI to generate real image descriptions
- **Undo / Redo** - revert any tag edit or auto-fix action (Ctrl+Z / Ctrl+Shift+Z)
- **Working HTML export** - File > Export HTML now generates accessible HTML with TOC and ARIA landmarks
- **Toolbar wiring** - Validate and AI Suggest toolbar buttons now work end-to-end
- **Inline results panel** - validation issues appear as a clickable list with "Fix" and "Page N" buttons

#### Bug Fixes & Polish
- **Async validation** - UI no longer freezes during validation or AI calls
- **Clean exit** - close confirmation only appears when there are unsaved changes
- **Animation stability** - circular progress animation no longer gets garbage collected
- **Consistent icons** - all emoji icons replaced with clean white Unicode line symbols

---

## How to Install

### Step 1: Download the Files

1. Click the green **Code** button at the top of this page
2. Click **Download ZIP**
3. Find the ZIP file in your Downloads folder
4. Double-click the ZIP file to open it

### Step 2: Install Python

This app needs Python to run.

**On Mac:**
1. Open **Terminal** (search for "Terminal" using Spotlight - press Cmd+Space)
2. Copy this command and press Enter:
   ```bash
   brew install python
   ```
   If that doesn't work, go to [python.org](https://www.python.org/downloads/) and download Python.

**On Windows:**
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Click the big yellow **Download Python** button
3. Run the file you downloaded
4. **IMPORTANT:** Check the box that says **"Add Python to PATH"**
5. Click **Install Now**

### Step 3: Set Up the App

1. Open **Terminal** (Mac) or **Command Prompt** (Windows)
   - Mac: Search for "Terminal"
   - Windows: Search for "cmd"

2. Go to the folder you downloaded:
   ```bash
   cd ~/Downloads/Local-Accessible-PDF-Toolkit-main
   ```

3. Create a safe space for the app:
   ```bash
   python3 -m venv venv
   ```

4. Turn on that safe space:

   **Mac:**
   ```bash
   source venv/bin/activate
   ```

   **Windows:**
   ```bash
   venv\Scripts\activate
   ```

5. Install what the app needs:
   ```bash
   pip install -r requirements.txt
   ```

### Step 4: Run the App

Type this and press Enter:
```bash
python launcher.py
```

**The app will open!** You'll see a login screen with the APT logo.

---

## How to Use

### First Time: Make an Account (or Skip It)

When the app opens:

1. Click the **Register** tab
2. Pick a **username** (any name you like)
3. Add your **email** (you can skip this)
4. Pick a **password** (at least 6 letters or numbers)
5. Type the password again
6. Click **Create Account**

**Don't want to make an account?** Click "Continue without login" at the bottom.

---

### Opening a PDF File

**Way 1: Drag and Drop (Easiest!)**
1. Find your PDF file
2. Drag it into the app
3. Drop it on the "Drop PDF Here" area

**Way 2: Click Browse**
1. Click **Import PDF**
2. Find your file
3. Click **Open**

---

### The 3 Tabs

The app has 3 tabs on the left side:

#### 1. Dashboard
- See all your recent PDFs with compliance scores
- Drag files here to open them
- Click any file to work on it
- Returning documents show previous score and session count

#### 2. PDF Viewer
- See your PDF with colored highlights
- AI-powered accessibility analysis
- Apply suggested fixes directly
- Progress tracker shows remediation status across 14 categories
- Colors show what needs fixing:
  - Purple = Headings
  - Yellow = Images that need descriptions
  - Green = Tables
  - Orange = Links
  - Red = Problems to fix

#### 3. Settings
- **AI Backend** - pick your AI helper (Ollama, LM Studio, GPT4All, and more)
- **Processing** - batch limits, OCR language, file preservation
- **Display & Accessibility** - high contrast, reduced motion, large text, enhanced focus, dyslexia font, color blindness modes, custom cursors - all with instant live preview
- **Validation** - choose WCAG level (A/AA/AAA) and toggle individual checks

---

### Keyboard Shortcuts

Press these keys to work faster:

| Press These Keys | What Happens |
|-----------------|--------------|
| Ctrl+1 | Go to Dashboard |
| Ctrl+2 | Go to PDF Viewer |
| Ctrl+3 | Go to Settings |
| Ctrl+O | Open a PDF file |
| Ctrl+S | Save your work |
| Ctrl+Z | Undo last change |
| Ctrl+Shift+Z | Redo last change |
| Ctrl+E | Export to HTML |
| Ctrl+Shift+V | Validate WCAG compliance |
| Ctrl+Space | Get AI suggestions |

---

## Accessibility Settings

The app itself is built to be accessible. Go to **Settings** (Ctrl+3) and look under **Display & Accessibility** to configure:

| Setting | What It Does |
|---------|--------------|
| **High Contrast** | Switches to a black-and-white theme for maximum readability |
| **Reduced Motion** | Turns off all animations (toggle slides, progress spinners) |
| **Large Text** | Increases all text by 25% across the entire app |
| **Enhanced Focus** | Adds bright yellow borders around the currently focused control |
| **Dyslexia Font** | Switches to OpenDyslexic (or Comic Sans MS) with extra letter spacing |
| **Color Blindness** | Remaps purple/blue accents to blue, pink, or grayscale depending on mode |
| **Custom Cursor** | Choose from Large Black, Large White, Crosshair, High Visibility, or Cursor Trail |

All settings preview **instantly** as you toggle them - no need to save first.

---

## Setting Up AI (Optional but Helpful!)

The app can use AI to suggest fixes. The AI runs on your computer, so your files stay private.

### Install Ollama (Recommended - It's Free!)

1. Go to [ollama.ai](https://ollama.ai)
2. Click **Download**
3. Install it like any other app
4. Open Terminal and type:
   ```bash
   ollama pull llama3.2
   ```
5. Wait for it to download (this takes a few minutes)

### Tell the App to Use Ollama

1. Open the app
2. Go to **Settings** (Ctrl+3)
3. Click the **AI Backend** tab
4. Make sure **Ollama** is selected
5. Click **Test Connection** - you should see a green checkmark!

---

## Building a Desktop App (Advanced)

Want an app you can double-click to open? Do this:

1. Make sure you have PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Build the app:
   ```bash
   pyinstaller accessible-pdf-toolkit.spec
   ```

3. Find your new app in the **dist** folder!

---

## Need Help?

### Common Problems

**"Python not found"**
- Install Python (see Step 2 above)
- On Windows, make sure you checked "Add Python to PATH"

**App won't start**
- Make sure you ran `source venv/bin/activate` (Mac) or `venv\Scripts\activate` (Windows)
- Try running `pip install -r requirements.txt` again

**AI doesn't work**
- Make sure Ollama is running
- Go to Settings > AI Backend > Click "Test Connection"

### Still Stuck?

[Click here to ask for help](https://github.com/Tech-Inclusion-Pro/Local-Accessible-PDF-Toolkit/issues)

---

## Privacy Premise

*If you use a local model on your computer (like Ollama), your files are **100% private**:

- PDFs **never** leave your computer
- AI runs **locally** on your machine
- **No data** is sent to the internet
- Safe for **sensitive documents**

---

## Technical Details

### What's Inside

- **PyMuPDF** - Reads and writes PDF files
- **pikepdf** - Adds accessibility tags
- **Tesseract OCR** - Reads text from scanned documents
- **PyQt6** - Makes the app look nice
- **Ollama/LM Studio** - Provides AI features

### WCAG Compliance

This app checks your PDFs against WCAG 2.1/2.2 Level A, AA, and AAA:

| What We Check | Why It Matters |
|---------------|----------------|
| Document title | Screen readers announce it |
| Document language | Ensures correct pronunciation |
| Tagged PDF structure | Enables assistive technology to parse the document |
| Headings | Helps people navigate |
| Image descriptions | Describes pictures for blind users (uses structure tree) |
| Color contrast | Text must be readable (4.5:1 for AA, 7:1 for AAA) |
| Table detection | Finds untagged tables using layout heuristics |
| Link text | "Click here" doesn't help - detects untagged hyperlinks too |
| Reading order | Detects multi-column layouts and order mismatches |

### Auto-Fix Capabilities

The auto-fix feature can resolve these issues automatically:

| What It Fixes | How |
|---------------|-----|
| Missing title | Sets a human-readable title from the filename |
| Missing language | Sets document language to English |
| No tags / structure | Creates a structure tree and marks the PDF as tagged |
| Untagged headings | Detects headings by font size and assigns H1-H6 tags (persisted to structure tree) |
| Missing image alt text | Uses AI-generated descriptions when available, placeholder otherwise |

### Show Me Walkthrough Capabilities

For issues that require external tools, the app provides step-by-step guides:

| What It Guides | External Tool |
|----------------|---------------|
| Tag document structure | Adobe Acrobat Pro |
| Fix reading order | Adobe Acrobat Pro |
| Apply artifacts | Adobe Acrobat Pro |
| Set table headers and scope | Adobe Acrobat Pro |
| Set form tab order | Adobe Acrobat Pro |
| Configure security settings | Adobe Acrobat Pro |
| Screen reader testing | NVDA / VoiceOver |

---

## Credits

Made with love by **Rocco Catrone**

Helping make the digital world accessible to everyone!

---

## License

MIT License - Free to use!

---

<p align="center">
  <img src="assets/logo.png" alt="APT Logo" width="100"/>
  <br/>
  <strong>Accessible PDF Toolkit</strong>
  <br/>
  Making PDFs accessible, one document at a time.
</p>
