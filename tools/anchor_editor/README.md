# Anchor Editor

Manual UI tool for saving chat panel anchors from screenshots.

## Run

```powershell
python tools/anchor_editor/anchor_editor.py
```

Optional initial image and output path:

```powershell
python tools/anchor_editor/anchor_editor.py --image "tests/fixtures/screenshots/image (1) (1).png" --output "tools/anchor_editor/anchors.json"
```

Optional image directory:

```powershell
python tools/anchor_editor/anchor_editor.py --dir "tests/fixtures/screenshots"
```

You can switch screenshots in the UI dropdown at any time.
Supported image types: `.png`, `.jpg`, `.jpeg`, `.webp`.

## Controls

- Left click: set current point
- Right click: undo previous point
- `S`: save
- `R`: reset
- `Q`: quit

## Capture Order

1. Chat panel top-left
2. Chat panel bottom-right
3. Message-list top-left
4. Message-list bottom-right
5. Left bubble lane center
6. Right bubble lane center
7. Side split line (left of this line => `left`, right => `right`)

Required to save: steps 1-4.

Optional but recommended: steps 5-7.
If omitted, defaults are inferred from the message-list bounds.

Saved profiles are keyed by image resolution (for example `1920x1080`) in `anchors.json`.

## Classifier Behavior

- Primary side classifier uses bubble geometry against `split_x`.
  - If bubble is fully left of split: `left`
  - If fully right of split: `right`
  - If crossing split: chooses the side with larger bubble span
- Lane probes are fallback only when split geometry is unavailable.
