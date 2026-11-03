# Workflow tour

A picture-led walk through the app, in the order you will meet it. Each section
links to the guide that has the detail.

Every image here is a real screen from the app, captured against an invented
diary notebook. The pages are rendered text on ruled paper; no real notebook,
and no OCR run, is involved. The app follows your system light or dark theme;
these captures use dark.

## Home and the Library

**Home** shows your notebook count, the recent notebooks, and whether Ollama is
reachable. **Open sample notebook** installs a three-page placeholder you can
try without any OCR.

![Home: notebook count, recent notebooks and Ollama status](images/home.png)

**Library** is the cover gallery. Click the cover, or **Open** under it, to open
the notebook. **Activity** switches to a per-notebook histogram list.

![Library cover gallery with a visible Open button under each cover](images/library.png)

**Workflow → New notebook** creates an empty notebook (then Import), or installs
the sample.

![New notebook: name it, or open the sample](images/new-notebook.png)

More: [user guide](user_guide.md).

## Import

**Workflow → Import → This notebook** adds JPEG, PNG, or PDF pages to the open
notebook. Visual declutter crops scanner beds, gutters, and shadows on the way
in; change or re-apply it under **Settings → Configuration → Import**.

![Import page for the selected notebook](images/import.png)

**Target → Batch** imports a folder, or a parent of folders, as one notebook
each. **Scan inbox** fills the folder path from `TRANSCRIBE_INBOX_DIR`. When a run
finishes it reports **imported**, **failed**, **duplicated**, and **needs-review**
counts, and **Transcribe imported notebooks** hands the run to batch OCR.

![Batch import with Scan inbox and recent import runs](images/import-batch.png)

More: [user guide, bulk import](user_guide.md#bulk-import-and-batch-jobs) ·
[import runs](contracts/import-run.md).

## Transcribe

Pick an OCR-friendly vision model and start. **Refresh Models** re-reads what
your Ollama server has. **Compare models** (further down) runs two or more models
on the same pages so you can compare their readings in Review.

![Transcribe: Ollama URL, vision model, text model and Compare models](images/transcribe.png)

More: [OCR and transcription](runtime/ocr.md) ·
[model matrix](runtime/ocr_model_matrix.md).

## Review

Review is the work queue. The scan sits on the left; one lane at a time sits on
the right. A full pass over a page looks like this: read the scan against the
text, compare the OCR readings if they disagree, check the date and tags, then
**Save + Mark reviewed**.

![Review loop: transcription, OCR evidence, date, tags, then Save and Mark reviewed](images/workflow-review.gif)

### Transcription and OCR evidence

The **Transcription** lane holds the editor. When two OCR attempts disagree, the
line is flagged and **OCR evidence** lets you switch between attempts, copy one
into the editor, or make it the current text. Your edits are stored separately
from the raw OCR.

![Review, Transcription lane, with a source disagreement flagged](images/review-transcription.png)

Further down, **Source disagreement** steps through each differing word and lets
you take either reading or type a correction.

![OCR evidence and source disagreement navigation](images/review-ocr-evidence.png)

If you move to another page with unsaved changes, Review asks first: **Stay** to
keep editing, or **Discard & leave** to drop the edit.

### Date, tags, cleanup

The **Date** lane approves or sets the page date. **Tags** assigns page tags; a
tag you remove stays removed when you apply detected tags later. **Cleanup**
re-applies visual declutter on this page or the whole notebook without
re-running OCR. It crops scanner beds, stark-white gutters, corner wedges,
dark binding gutters, and edge shadows.

![Review, Tags lane](images/review-tags.png)

![Review, Cleanup lane](images/review-cleanup.png)

More: [OCR, Review](runtime/ocr.md#review-after-ocr).

## Fixing page order

Notebook order is the order of the pages in the notebook, not the number of the
folder on disk. If a page was scanned out of sequence you can move it without
touching the files.

- **Review → Other → Page order**: **Move up**, **Move down**, or **Move to position**.
- **Review → Other** also holds **Bookmark**, **Page note**, **Unsure**, **Kept scan**, **Do not OCR this page**, and **Confirmed spellings**. The page note is one short gloss, not the transcription.
- **Review → Date → Move to date cluster** appears when a page's date breaks the
  notebook order. It places the page after the pages with the same confirmed
  date, or in date order if there are none.
- **Thumbnails** shows the page grid with the same controls. Dragging a
  thumbnail also works in browsers that allow it; the numbered controls are the
  dependable route.

![Fix a date regression: Move to date cluster, then check the grid](images/workflow-reorder-pages.gif)

![Other lane with Move up, Move down and Move to position](images/review-page-order.png)

![Date lane offering Move to date cluster for an out-of-order page](images/review-date-cluster.png)

![Thumbnails grid with the page order panel](images/review-thumbnails.png)

Reordering is refused while OCR or analysis is running on the notebook. In the
app the controls are also disabled while the page has unsaved edits. From the
command line:

```bash
./transcribe.sh cli pages reorder "$TRANSCRIBE_PROJECTS_DIR/my-notebook" PAGE_ID_1 PAGE_ID_2 …
./transcribe.sh cli pages move-to-date-cluster "$TRANSCRIBE_PROJECTS_DIR/my-notebook" PAGE_ID
```

Contract: [project on disk, page reorder](contracts/project-on-disk.md).

## Reading

**View → Read** shows the same pages in order, read-only, with the text beside
the scan.

![Reading view](images/view-read.png)

## Detect

**Workflow → Detect** scans for poetry, lists, to-dos, quotations, names, and
custom detectors. A running scan shows progress and a **Stop after current
window** button; the run finishes the window in progress, starts no further
detectors, and is recorded as cancelled. **Findings** is where you
accept or reject what it found.

![Detect: choose detectors and run](images/detect.png)

More: [analysis and Detect](runtime/analysis.md#detect).

## Analyse

Choose **Quick**, **Balanced**, **Thorough**, or **Custom**, then run. Quick
needs no text model. Balanced and above use one for the LLM modules.

![Analyse presets](images/analyse.png)

More: [analysis and Detect](runtime/analysis.md).

## Export

Choose formats, structure, and typography, then export. **Fine-tune dataset**
packs page images with their preferred or current text for training elsewhere;
Transcribe does not train models.

![Export: formats, structure, typography](images/export.png)

![Fine-tune dataset export](images/export-finetune.png)

After training elsewhere, bring the model back with the checklist the export
writes: [fine-tune export](finetune_export.md).

More: [export](runtime/export.md).

## Settings and Diagnostics

**Settings → Configuration** holds folders, backup and restore, import and
declutter options. **System → Diagnostics** checks the workspace, the selected
notebook, and Ollama.

![Settings, Configuration tab](images/settings.png)

![Diagnostics after a run](images/diagnostics.png)

More: [settings](runtime/settings.md) · [backup and restore](backup_and_restore.md).

## Regenerating these images

The screenshots and GIFs come from a script, so they can be refreshed after UI
changes. See [documentation architecture](dev/docs_architecture.md#documentation-media).
