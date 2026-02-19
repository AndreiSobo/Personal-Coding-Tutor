# PACT Scripts - Machine Learning Pipeline

This directory contains the complete Machine Learning pipeline for the **Personalised AI Coding Tutor (PACT)**. 

These scripts operate independently from the web application to:
1.  **Generate a Synthetic Socratic Dataset**: Create a high-quality dataset of student errors and corresponding Socratic hints using Claude and GPT-4.
2.  **Fine-Tune the Model**: Train a custom version of Qwen 2.5 7B Instruct to act as a Socratic tutor.
3.  **Evaluate Performance**: Benchmark the model against pedagogical metrics (e.g., code leakage, direct answer rate).
4.  **Inference Testing**: Validate model behavior before deployment.

## Pipeline Architecture

The pipeline is designed to be modular and reproducible.

### 1. Dataset Generation (`/dataset`)
Since high-quality "Socratic dialogue" data is scarce, we built a synthetic data generation pipeline:
*   **Source**: LeetCode-style coding problems.
*   **Generator (Claude 3.5 Sonnet)**: Simulates realistic student mistakes (logic bugs, syntax errors) and writes pedagogical hints.
*   **Validator (GPT-5.2)**: acts as a quality gate, ensuring the buggy code actually fails and the hint is helpful without giving away the answer.
*   **Outcome**: A dataset of **227 high-quality** (Buggy Code, Socratic Hint) pairs.

### 2. Model Training (`/training`)
*   **Base Model**: `Qwen/Qwen2.5-7B-Instruct` (chosen for reasoning capabilities).
*   **Method**: **QLoRA** (Quantized Low-Rank Adaptation) on a single NVIDIA RTX 4090 (24GB VRAM).
*   **Configuration**:
    *   4-bit quantization.
    *   LoRA rank 16 / Alpha 32.
*   **Infrastructure**: Trained on **RunPod.io** cloud GPU instances.

### 3. Evaluation (`/evaluation`)
*   **Approach**: **LLM-as-a-Judge**.
*   **Metrics**:
    *   **Socratic Quality**: Does the model ask guiding questions?
    *   **Code Leakage**: Does the model reveal code snippets? (Strictly penalized).
    *   **Direct Answer**: Does the model give the answer away?
    *   **Helpfulness**: Would this hint actually help the user?
    *   **Factual Corectness**: Is the hint technically accurate?

---

## Directory Structure

```
scripts/
├── dataset/              # Synthetic Data Generation
│   ├── step1_prepare_problems.py    # Loads source problems
│   ├── step2_generate_examples.py   # Claude generates bugs + hints
│   ├── step2_5_adjust_problems.py   # Refines source problems
│   ├── step3_validate_examples.py   # GPT-5.2 validates pedagogical quality
│   ├── step3_5_merge_datasets.py    # Merges validation results
│   ├── step3_6_analyse_results.py   # Stat analysis of dataset
│   ├── step4_revise_examples.py     # Revies rejected examples
│   └── step5_format_for_training.py # Prepares JSONL for training
│
├── training/             # Fine-Tuning Pipeline
│   ├── train_qwen.py              # Main QLoRA training script
│   ├── merge_weights.py           # Merges LoRA adapters into base model
│   ├── quantize_model.py          # Quantizes model for inference (AWQ)
│   └── upload_to_hf.py            # Uploads models to Hugging Face
│
├── evaluation/           # Evaluation Benchmarks
│   ├── evaluate_socratic.py       # LLM-as-a-Judge evaluation script
│   ├── generate_test_cases.py     # Creates hold-out test set
│   └── generate_test_responses.py # Batch generates model answers
│
├── notebooks/            # Interactive Experimentation
│   ├── local_inference.ipynb      # Tests inference with local GPU / HF Endpoints
│   ├── generate_test_responses.ipynb # Interactive response generation
│   └── publish_dataset.ipynb      # Manage Hugging Face dataset uploads
│
├── data/                 # Data Artifacts
│   ├── training_dataset_final.json
│   └── ...
```


### 4. Train Model (Cloud Infrastructure)

Training was done on **RunPod.io**. Other cloud providers were evaluated but the cost made RunPod a good choice.

**Specs**:
- **GPU**: NVIDIA RTX 4090 (24GB VRAM)
- **Disk**: 50GB+ Container Disk, 50GB+ Volume Disk

**Deployment Steps on RunPod**:
1.  **Launch Pod**: Select a `RunPod PyTorch 2.X` template with a 4090 GPU.
2.  **Connect**: Open the Web Terminal or connect via SSH.
3.  **Setup**:
    ```bash
    git clone https://github.com/YOUR_USERNAME/personal-coding-tutor.git
    cd personal-coding-tutor/scripts
    pip install -r training/requirements.txt
    ```
4.  **Environment Variables**:
    Since login is done via API keys, a `.env` file was created for the scripts to authenticate with Hugging Face, OpenAI, and Anthropic.
    
    ```bash
    echo "HF_TOKEN=your_token_here" > .env
    echo "WANDB_API_KEY=your_key_here" >> .env
    echo "OPENAI_API_KEY=your_key_here" >> .env
    echo "ANTHROPIC_API_KEY=your_key_here" >> .env
    ```
5.  **Run Training**:
    ```bash
    cd training
    # Test run (sanity check)
    python train_qwen.py --max_steps 1 --max_examples 10
    
    # Full training run
    python train_qwen.py
    ```
    

6.  **Merge & Upload**:
    ```bash
    # Merge LoRA adapters with base model
    python merge_weights.py
    
    # Quantize (Optional for faster inference)
    python quantize_model.py

    # Upload to Hugging Face (Uses HF_TOKEN from .env)
    python upload_to_hf.py
    ```

### 5. Evaluate Model

```bash
cd evaluation

python generate_test_cases.py           # generate a json file with the evaluation dataset
python generate_test_responses.py       # iterate through each test case and run inference on both PACT and quantized PACT 
python evaluate_socratic.py             # implement LLM-as-judge to evaluate the answers
```

## Inference Pipeline

The inference infrastructure can be a complex process, therefore for simplicity and reduced costs, I opted for a Hugging Face Inference Endpoint solution, where an API connected to a GPU instance is used to query the model.

Importantly, this required a handler.py and a requirements.txt files to be created on the model repository. 

*   **Notebook**: `notebooks/local_inference.ipynb` has examples of how to run inference


## Dataset Pipeline Details

Research showed a clear lack of datasets containing incorrect code, that I may use to train the model. Therefore, I built a comprehensive synthetic data generation and validation pipeline. This approach leverages an LLM-as-a-Judge architecture to filter, score, and revise the training data before fine-tuning.

The pipeline consists of the following automated steps (located in `scripts/dataset/`):

1. **Problem Preparation (`step1_prepare_problems.py`)**: Sourcing and formatting base Python coding problems (e.g., from `source_problems.json`) to serve as the context for the synthetic conversations.
2. **Synthetic Generation (`step2_generate_examples.py` & `step2_5_adjust_problems.py`)**: Prompting a frontier LLM to act as a student and a Socratic tutor, generating multi-turn conversational data where the student presents buggy code and the tutor provides guided hints.
3. **LLM-as-a-Judge Validation (`step3_validate_examples.py` & `step3_6_analyse_results.py`)**: A critical quality control step where an evaluator LLM reviews the generated conversations against strict Socratic criteria. Examples are categorized into `passed`, `rejected`, or `needs_revision`.
4. **Automated Revision (`step4_revise_examples.py`)**: Taking the examples flagged for revision and feeding them back into the LLM with critique prompts to correct issues (such as accidental code leakage) and salvage the data.
5. **Formatting and Merging (`step3_5_merge_datasets.py` & `step5_format_for_training.py`)**: Compiling the final, validated examples into the required ChatML/JSONL format (`qwen_training_data.jsonl`) for the Hugging Face `SFTTrainer`.

## Evaluation Metrics using the LLM-as-Judge

- **Socratic Quality**: How well does it guide through questions? (1-5)
- **Code leakage rate**: Does the response contain executable code that solves the problem? (Yes/No)
- **Direct Answer**: Does it directly tell the user the fix? (Yes/No)
- **Helpfulness**: Would this actually help the user? (1-5)
- **Factual Correctness**: Is technical content accurate? (Yes/No)

## Troubleshooting

### "Dependency hell" library versions that work with eachother and all the platforms
- It was quite challenging to navigate the different platforms and find the correct library versions that they all accepted. If anyone is interested in a similar project, I strongly suggest they use the dependency versions mentioned in projects that have successfully done these tasks - alternatively, copy mine.


