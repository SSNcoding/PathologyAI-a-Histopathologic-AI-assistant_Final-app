"""Modular disease/organ registry.

Each entry describes one organ system: the class taxonomy the UI shows,
which public datasets are the standard starting point for training a real
classifier, and which architectures are commonly used in the literature.

To add a new disease/organ: add one `DiseaseOrgan` entry to `DISEASE_REGISTRY`.
Nothing else in the app needs to change — pages, charts, and the analyzer all
read from this registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiseaseOrgan:
    key: str
    display_name: str
    icon: str  # bootstrap-icons name (used with streamlit-option-menu / fa-style badges)
    classes: list[str]
    datasets: list[str]
    reference_architectures: list[str]
    notes: str = ""


DISEASE_REGISTRY: dict[str, DiseaseOrgan] = {
    "breast": DiseaseOrgan(
        key="breast",
        display_name="Breast Cancer",
        icon="gender-female",
        classes=["Benign", "Ductal Carcinoma In Situ (DCIS)", "Invasive Ductal Carcinoma", "Invasive Lobular Carcinoma"],
        datasets=["CAMELYON16", "CAMELYON17", "BreakHis", "TCGA-BRCA"],
        reference_architectures=["ResNet50", "EfficientNet-B0", "ViT-B/16"],
    ),
    "lung": DiseaseOrgan(
        key="lung",
        display_name="Lung Cancer",
        icon="lungs",
        classes=["Benign", "Adenocarcinoma", "Squamous Cell Carcinoma"],
        datasets=["LC25000", "TCGA-LUAD", "TCGA-LUSC"],
        reference_architectures=["EfficientNet-B0", "DenseNet121"],
    ),
    "colon": DiseaseOrgan(
        key="colon",
        display_name="Colon Cancer",
        icon="capsule",
        classes=["Benign", "Adenocarcinoma", "Mucinous Adenocarcinoma"],
        datasets=["LC25000", "TCGA-COAD"],
        reference_architectures=["EfficientNet-B0", "ResNet50"],
    ),
    "prostate": DiseaseOrgan(
        key="prostate",
        display_name="Prostate Cancer",
        icon="gender-male",
        classes=["Benign", "Gleason Pattern 3", "Gleason Pattern 4", "Gleason Pattern 5"],
        datasets=["PANDA", "TCGA-PRAD"],
        reference_architectures=["EfficientNet-B0", "Swin Transformer"],
    ),
    "skin": DiseaseOrgan(
        key="skin",
        display_name="Skin Cancer",
        icon="bandaid",
        classes=["Benign Nevus", "Basal Cell Carcinoma", "Squamous Cell Carcinoma", "Melanoma"],
        datasets=["ISIC Archive", "TCIA"],
        reference_architectures=["EfficientNet-B0", "ConvNeXt-Tiny"],
    ),
    "brain": DiseaseOrgan(
        key="brain",
        display_name="Brain Tumor",
        icon="bezier2",
        classes=["Normal", "Glioma", "Meningioma", "Pituitary Tumor"],
        datasets=["TCGA-GBM", "TCGA-LGG", "TCIA"],
        reference_architectures=["ResNet50", "ViT-B/16"],
    ),
    "cervical": DiseaseOrgan(
        key="cervical",
        display_name="Cervical Cancer",
        icon="flower1",
        classes=["Normal", "LSIL", "HSIL", "Squamous Cell Carcinoma"],
        datasets=["TCGA-CESC", "SIPaKMeD"],
        reference_architectures=["EfficientNet-B0", "ResNet50"],
    ),
    "oral": DiseaseOrgan(
        key="oral",
        display_name="Oral Cancer",
        icon="emoji-smile",
        classes=["Normal", "Leukoplakia", "Squamous Cell Carcinoma"],
        datasets=["TCGA-HNSC", "TCIA"],
        reference_architectures=["DenseNet121", "EfficientNet-B0"],
    ),
    "liver": DiseaseOrgan(
        key="liver",
        display_name="Liver Cancer",
        icon="droplet-half",
        classes=["Normal", "Hepatocellular Carcinoma", "Cholangiocarcinoma"],
        datasets=["TCGA-LIHC", "TCIA"],
        reference_architectures=["ResNet50", "DenseNet121"],
    ),
    "kidney": DiseaseOrgan(
        key="kidney",
        display_name="Kidney Cancer",
        icon="moisture",
        classes=["Normal", "Clear Cell RCC", "Papillary RCC", "Chromophobe RCC"],
        datasets=["TCGA-KIRC", "TCGA-KIRP", "TCGA-KICH"],
        reference_architectures=["EfficientNet-B0", "ConvNeXt-Tiny"],
    ),
}


def get_organ(key: str) -> DiseaseOrgan:
    return DISEASE_REGISTRY.get(key, DISEASE_REGISTRY["breast"])


def organ_options() -> list[tuple[str, str]]:
    """(key, display_name) pairs for select widgets, sorted by display name."""
    return sorted(((o.key, o.display_name) for o in DISEASE_REGISTRY.values()), key=lambda t: t[1])
