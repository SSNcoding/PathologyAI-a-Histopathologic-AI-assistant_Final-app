"""Fine-tune one of models/architectures.py's real backbones on your own
histopathology dataset and produce a checkpoint model_registry.py will pick
up automatically — no other code changes needed.

THIS SCRIPT HAS NOT BEEN RUN. Training a real model needs a GPU (or a lot
of patience on CPU) and a downloaded dataset (multiple GB), neither of which
were available in the sandboxed environment this was built in. The code
below is a complete, standard PyTorch transfer-learning loop — the same
shape as any torchvision ImageFolder fine-tuning script — but you should
run it yourself and watch the first few epochs before trusting it blindly,
the same way you'd sanity-check any new training script.

--------------------------------------------------------------------------
1. Get a dataset. Recommended starting point: CAMELYON16/17 (breast) or
   BreakHis (breast), PANDA (prostate), or LC25000 (lung/colon) — see
   models/disease_registry.py for the full per-organ list. Most of these
   ship as whole-slide images; you'll need to tile them into patches first
   (e.g. with OpenSlide + a simple sliding-window script) unless you're
   using an already-patched dataset like BreakHis or LC25000.

2. Arrange patches as an ImageFolder:

       data/breast/
           Benign/               *.png / *.jpg
           Ductal Carcinoma In Situ (DCIS)/
           Invasive Ductal Carcinoma/
           Invasive Lobular Carcinoma/

   The subfolder names MUST exactly match, in order, the `classes` list for
   that organ in models/disease_registry.py — torchvision's ImageFolder
   assigns label indices alphabetically by folder name, but this script
   re-maps them to match the registry's order (see _build_datasets below),
   so the checkpoint's output indices line up with what model_registry.py
   and the rest of the app expect.

3. Run it:

       python train_classifier.py --organ breast --architecture ResNet50 \
           --data-dir data/breast --epochs 10 --batch-size 32

4. On success, the checkpoint lands at
   models/weights/breast_ResNet50.pt — restart the Streamlit app and
   services/ai_analyzer.py will automatically switch that organ from
   HEURISTIC_PLACEHOLDER to PYTORCH mode.
--------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision import transforms
from torchvision.datasets import ImageFolder

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import DISEASE_CLASSIFIER_PATH_TEMPLATE  # noqa: E402
from models.architectures import ARCHITECTURE_BUILDERS, build_backbone  # noqa: E402
from models.disease_registry import get_organ  # noqa: E402

TRAIN_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Must match models/architectures.py's INFERENCE_TRANSFORM exactly — the
# whole point of validating with this transform is to measure the model the
# way it'll actually be used at inference time, not with training-time
# augmentation still applied.
EVAL_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


class _RemappedLabels(Dataset):
    """Wraps an ImageFolder so label indices match disease_registry's class
    order instead of ImageFolder's alphabetical default — otherwise a
    perfectly-trained model would predict the right class with the wrong
    index, and every downstream label would be silently wrong."""

    def __init__(self, base: ImageFolder, class_names: list[str], transform):
        self.base = base
        self.transform = transform
        # base.classes is alphabetically sorted by ImageFolder; map its index -> our index.
        self._index_map = {
            base.classes.index(name): i for i, name in enumerate(class_names) if name in base.classes
        }
        missing = set(class_names) - set(base.classes)
        if missing:
            raise ValueError(
                f"data-dir is missing subfolders for these classes: {sorted(missing)}. "
                f"Found subfolders: {sorted(base.classes)}"
            )

    def __len__(self) -> int:
        return len(self.base)

    def __getitem__(self, idx: int):
        path, original_label = self.base.samples[idx]
        image = self.base.loader(path)
        image = self.transform(image)
        return image, self._index_map[original_label]


def _build_datasets(data_dir: Path, class_names: list[str], val_split: float, seed: int):
    train_base = ImageFolder(str(data_dir))
    full_len = len(train_base)
    val_len = int(full_len * val_split)
    train_len = full_len - val_len
    generator = torch.Generator().manual_seed(seed)
    train_indices, val_indices = random_split(range(full_len), [train_len, val_len], generator=generator)

    train_ds = torch.utils.data.Subset(_RemappedLabels(train_base, class_names, TRAIN_TRANSFORM), train_indices.indices)
    val_ds = torch.utils.data.Subset(_RemappedLabels(train_base, class_names, EVAL_TRANSFORM), val_indices.indices)
    return train_ds, val_ds


def train(args: argparse.Namespace) -> None:
    organ = get_organ(args.organ)
    class_names = organ.classes
    print(f"Organ: {organ.display_name} ({args.organ}) — {len(class_names)} classes: {class_names}")

    if args.architecture not in ARCHITECTURE_BUILDERS:
        raise SystemExit(f"Unknown architecture '{args.architecture}'. Options: {list(ARCHITECTURE_BUILDERS)}")

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise SystemExit(f"--data-dir '{data_dir}' does not exist.")

    train_ds, val_ds = _build_datasets(data_dir, class_names, args.val_split, args.seed)
    print(f"Train samples: {len(train_ds)}  Val samples: {len(val_ds)}")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=args.num_workers)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.num_workers)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    model = build_backbone(args.architecture, num_classes=len(class_names), pretrained_backbone=True)
    model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    best_val_acc = 0.0
    weight_path = Path(DISEASE_CLASSIFIER_PATH_TEMPLATE.format(
        organ=args.organ, architecture=args.architecture.replace("/", "-")
    ))
    weight_path.parent.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        model.train()
        start = time.perf_counter()
        running_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * images.size(0)
        train_loss = running_loss / max(len(train_ds), 1)

        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                preds = outputs.argmax(dim=1)
                correct += (preds == labels).sum().item()
                total += labels.size(0)
        val_acc = correct / total if total else 0.0
        elapsed = time.perf_counter() - start
        print(f"Epoch {epoch}/{args.epochs} — train_loss={train_loss:.4f} val_acc={val_acc:.4f} ({elapsed:.1f}s)")

        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), weight_path)
            print(f"  -> new best (val_acc={val_acc:.4f}), saved to {weight_path}")

    print(f"\nDone. Best val_acc={best_val_acc:.4f}. Checkpoint: {weight_path}")
    print(
        "Restart the Streamlit app — services/ai_analyzer.py checks for this file automatically "
        "and switches the organ from HEURISTIC_PLACEHOLDER to PYTORCH mode on the next analysis."
    )
    print(
        "Before trusting this model with anything beyond a demo: hold out a proper test set "
        "(not just the val split used for checkpoint selection), check per-class metrics (not "
        "just overall accuracy — histopathology datasets are often class-imbalanced), and run "
        "scripts/fit_temperature.py-style calibration (see models/architectures.py's "
        "temperature_scale, not yet wired into a script) before treating confidence scores as "
        "meaningful."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--organ", required=True, help="Organ key from models/disease_registry.py (e.g. 'breast').")
    parser.add_argument("--architecture", required=True, help="One of: " + ", ".join(ARCHITECTURE_BUILDERS))
    parser.add_argument("--data-dir", required=True, help="ImageFolder-structured dataset directory.")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
