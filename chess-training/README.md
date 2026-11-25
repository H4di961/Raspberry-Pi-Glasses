# Chess set annotation batch

Nine original PNG images were found, despite their `.jpeg.png` filenames. Originals are untouched. `dataset/images/01.png` through `09.png` are byte-for-byte copies with clear extensions.

Open `dataset/review.html` in your PC browser. It works locally without an API or server. Save edits with **Save annotations JSON** before closing; the page does not silently write to disk. Load the saved JSON to continue later.

## Confirmed identities

05, black foreground lineup, left to right: rook, knight, bishop, king, queen, pawn.
06, white foreground lineup, left to right: rook, knight, bishop, queen, king, pawn.

The initial manifest contains 12 manually drawn boxes for these foreground pieces, with identities explicitly supplied by the user. Background pieces in those same images are NOT yet annotated. All images start unreviewed. Image 09 is excluded from the initial training pool because it is blurry, but retained for later evaluation.

This is an annotation seed, not a complete training set. Do not train directly on the two partially labelled lineup photos: unlabelled background chess pieces could be treated as background during training.

## Annotation rules

- Draw a tight box around each visible piece, including its base; exclude its shadow.
- Use the confirmed lineup shapes to identify this set's types. Do not assume standard placement proves identity.
- Label visible pieces outside the board too. Board-location filtering is a separate runtime step.
- Do not guess the type of a heavily obscured piece. Leave the image unreviewed or exclude it until it can be resolved.
- Mark reviewed only after every visible target has been labelled and the boxes checked.
- Keep related views of the same arrangement together when later dividing train/validation data. This small batch is not an independent accuracy benchmark.

## Files

`prepare_dataset.py` creates the original seed and refuses to overwrite an existing manifest.
`dataset/annotations.json` stores pixel boxes, provenance, review status and image hashes.
`dataset/dataset.js` embeds that initial manifest for the standalone browser page.
`dataset/review.html` supports drawing/selecting/deleting boxes and saving/loading JSON.

No model has been trained and the live camera/chess application has not been modified.

## First training experiment

Run `chess-training/.venv/Scripts/python.exe -B chess-training/train_pilot.py` from the repository root to start a new pilot. The separate training environment uses GPU-enabled PyTorch; it does not modify the Pi or camera application's packages.

`export_yolo.py` converts the reviewed pixel boxes to normalized YOLO labels and verifies source image hashes. It refuses to overwrite an existing export. Images 01-06 are training data; 07-08 are validation data, kept together outside training. Image 09 is excluded. This tiny split is a preliminary test on the same room and chess set, not evidence of reliable generalization.

The pilot fine-tunes pretrained YOLO11n with 12 classes, 640-pixel input, batch 4, frozen backbone, AdamW, up to 80 epochs and early stopping patience 20. Data augmentation is applied only by the trainer. `runs/pilot-01/weights/best.pt` is the checkpoint selected by validation performance; related numbered run directories are used if rerun. `latest-run.json` records the completed run path. `training.log` records the initial run output. Validation predictions are saved in `runs/pilot-01-validation` (or a numbered variant).

No live integration is performed. Review held-out prediction images and collect new independently captured labelled images before trusting a recognized chess position. The training framework is available locally without an API fee; retain upstream license requirements if distributing a product.

## Round 02

`export_round_02.py` creates a separate `yolo-round-02` dataset from the latest reviewed annotations. It retains the original train/validation split: 07 and 08 remain validation-only; all other included images are used for training. This run has 22 training images (672 boxes), two validation images (63 boxes), and one excluded image. The source JSON hash is recorded in the export manifest.

`train_round_02.py` starts from pretrained YOLO11n, fine-tunes all layers for up to 150 epochs with patience 30, and saves under `runs/round-02`. Unlike the first pilot, the backbone is not frozen, so any improvement cannot be attributed only to additional photos. Other core input/batch/optimizer settings remain the same. The validation set has already been used for model selection; it is not a fresh independent test set.

Reproduction from the repository root (do not overwrite an existing export):

    .\chess-training\.venv\Scripts\python.exe -B chess-training/export_round_02.py
    .\chess-training\.venv\Scripts\python.exe -B chess-training/train_round_02.py

Review the saved validation predictions at confidence 0.25 before considering live integration. No camera or live chess application changes are part of this experiment.
