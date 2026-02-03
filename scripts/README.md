# PACT Scripts

This directory contains the ML pipeline scripts for PACT (Personalised AI Coding Tutor).

These scripts are **separate from the web application** and run independently to:
1. Generate the training dataset
2. Fine-tune the Qwen model
3. Evaluate model quality

## Directory Structure

```
scripts/
├── dataset/              # Dataset generation pipeline
│   ├── step1_prepare_problems.py
│   ├── step2_generate_examples.py
│   ├── step3_validate_examples.py
│   ├── step4_revise_examples.py
│   ├── step5_format_for_training.py
│   ├── step6_final_check.py
│   └── requirements.txt
│
├── training/             # Model fine-tuning
│   ├── train_qwen.py
│   ├── merge_weights.py
│   ├── upload_to_hf.py
│   └── requirements.txt
│
├── evaluation/           # Model evaluation
│   ├── evaluate_socratic.py
│   ├── check_hallucinations.py
│   └── requirements.txt
│
├── data/                 # Generated data (gitignored)
│   ├── source_problems.json
│   ├── generated_examples_raw.json
│   ├── training_data.jsonl
│   └── ...
│
├── .env                  # API keys (create from .env.template)
└── README.md             # This file
```

## Quick Start

### 1. Setup Environment

```bash
# Navigate to scripts directory
cd scripts

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (choose based on what you need)
pip install -r dataset/requirements.txt     # For dataset generation
pip install -r training/requirements.txt    # For model training
pip install -r evaluation/requirements.txt  # For evaluation
```

### 2. Configure API Keys

```bash
# Copy the template
cp .env.template .env

# Edit .env and add your keys
nano .env
```

### 3. Generate Dataset

```bash
cd dataset

# Step 1: Load problems from LeetCode dataset
python step1_prepare_problems.py

# Step 2: Generate training examples with Claude
python step2_generate_examples.py

# Step 3: Validate with GPT-4
python step3_validate_examples.py

# Step 4: Revise problematic examples
python step4_revise_examples.py

# Step 5: Format for Qwen training
python step5_format_for_training.py

# Step 6: Final quality check
python step6_final_check.py
```

### 4. Train Model

```bash
cd training

# Fine-tune with QLoRA
python train_qwen.py

# Merge adapter weights
python merge_weights.py

# Upload to Hugging Face (edit HF_USERNAME first!)
python upload_to_hf.py
```
importantly, since the training was done on RunPod, the following steps were taken:
1. create a pod - the selected configuration was a 4090 GPU with 24G of vRAM and 100GB of space.
2. connec tto the pod via terminal on RunPod.io platform
3. clone the github repo there
4. use "echo" to write the necessary keys into the .env file. This file must be located in the "scripts" folder
5. run python scripts for training
6. test run: python train_qwen.py --max_steps 1 --max_examples 10
7. actual run: 
### 5. Evaluate Model

```bash
cd evaluation

# Generate test responses from your model first, then:
python evaluate_socratic.py
python check_hallucinations.py
```

## Dataset Pipeline Details

| Step | Script | Input | Output | Description |
|------|--------|-------|--------|-------------|
| 1 | `step1_prepare_problems.py` | HuggingFace dataset | `source_problems.json` | Load & filter LeetCode problems |
| 2 | `step2_generate_examples.py` | `source_problems.json` | `generated_examples_raw.json` | Generate buggy code + hints with Claude |
| 3 | `step3_validate_examples.py` | `generated_examples_raw.json` | `examples_passed.json`, `examples_needs_revision.json` | Validate with GPT-4 |
| 4 | `step4_revise_examples.py` | `examples_needs_revision.json` | `training_dataset_final.json` | Fix problematic hints |
| 5 | `step5_format_for_training.py` | `training_dataset_final.json` | `training_data.jsonl` | Convert to Qwen chat format |
| 6 | `step6_final_check.py` | `training_data.jsonl` | Console report | Automated quality checks |

## Evaluation Metrics

### Automated Metrics (No API Required)
- **Code Leakage Rate (CLR)**: % of responses containing code (target: < 5%)
- **Guiding Question Rate (GQR)**: % of responses with questions (target: > 70%)
- **Direct Answer Rate (DAR)**: % of responses revealing answers (target: < 10%)

### LLM-as-Judge Metrics
- **Socratic Quality**: 1-5 scale rating
- **Helpfulness**: 1-5 scale rating
- **Error Identification Accuracy**: Does hint address actual bug?
- **Factual Correctness**: Is technical content accurate?

## Estimated Costs

| Task | API | Estimated Cost |
|------|-----|----------------|
| Generate 300 examples | Claude | ~$5-10 |
| Validate 300 examples | GPT-4 | ~$3-5 |
| Revise ~50 examples | Claude | ~$1-2 |
| LLM-as-Judge eval (50 samples) | Claude/GPT-4 | ~$1-2 |
| Training (RunPod A100) | - | ~$2-5 |

## Troubleshooting

### "Rate limit exceeded"
- Add `time.sleep(1)` between API calls
- Use smaller batches

### "Out of memory" during training
- Reduce `BATCH_SIZE` in train_qwen.py
- Increase `GRADIENT_ACCUMULATION` to maintain effective batch size
- Use a GPU with more VRAM

### "Model not found" on Hugging Face
- Check HF_USERNAME in upload_to_hf.py
- Verify you're logged in: `huggingface-cli login`

## Notes

- These scripts are for **one-time use** during development
- The web app does NOT depend on these scripts at runtime
- Generated data in `data/` should be gitignored (large files)
- Always review a sample of generated data manually before training
