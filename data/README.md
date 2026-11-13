# Data Directory

This directory contains the Banking77 dataset and its derived splits.

## Structure

```
data/
├── raw/              # Original downloaded data
│   ├── train.json
│   ├── test.json
│   └── metadata.json
├── processed/        # Intermediate processing artifacts
├── splits/           # Fixed reproducible splits
│   ├── train.json        # Training set (~9,500 examples)
│   ├── validation.json   # Validation set (500 examples)
│   └── golden_test.json  # Golden test set (500 examples)
└── manifests/        # Dataset metadata and hashes
    └── dataset_manifest.json
```

## Dataset: PolyAI/Banking77

- **Source**: https://huggingface.co/datasets/PolyAI/banking77
- **License**: CC BY 4.0
- **Classes**: 77 banking intent categories
- **Attribution**: Casanueva et al., "Efficient Intent Detection with Dual Sentence Encoders", 2020

## Reproducibility

All splits use `seed=42` with stratified sampling. SHA-256 hashes are recorded in `manifests/dataset_manifest.json`.

## Setup

```bash
python scripts/download_data.py    # Download from HuggingFace
python scripts/prepare_data.py     # Create deterministic splits
```

