# Offline LLM Setup Guide

This guide explains how to set up and use offline LLM models with the LeadGen pipeline instead of OpenAI API.

## Why Offline LLM?

- **Privacy**: Keep your data and email generation completely private
- **Cost**: No API costs after initial setup
- **Control**: Full control over the model and generation process
- **Offline**: Works without internet connection

## Recommended Solution: Ollama

Ollama is the easiest way to run large language models locally on your machine.

### Step 1: Install Ollama

**macOS/Linux:**

```bash
curl https://ollama.ai/install.sh | sh
```

**Or download from:** https://ollama.ai/download

### Step 2: Download a Model

We recommend Llama 2 for general use or Mistral for faster performance:

```bash
# For general use (7GB)
ollama pull llama2

# For faster performance (4GB)
ollama pull mistral

# For German-language optimization
ollama pull llama2:13b
```

### Step 3: Verify Ollama is Running

```bash
ollama list
```

You should see your downloaded models listed. Ollama runs as a service on `http://localhost:11434`.

### Step 4: Configure LeadGen

Edit your `.env` file in the `backend` directory:

```bash
# LLM Configuration
LLM_MODE=ollama  # Change from "openai" to "ollama"

# Ollama settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# OpenAI is no longer required
# OPENAI_API_KEY can be left empty
```

### Step 5: Restart Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

You should see in the logs: `Using Ollama LLM with model: llama2`

## Switching Between OpenAI and Ollama

To switch back to OpenAI:

```env
LLM_MODE=openai
OPENAI_API_KEY=your-api-key-here
```

To use Ollama:

```env
LLM_MODE=ollama
OLLAMA_MODEL=llama2  # or mistral, or any other model
```

## Model Recommendations

| Model      | Size | Best For                 | Speed  |
| ---------- | ---- | ------------------------ | ------ |
| llama2     | 7GB  | General email generation | Medium |
| mistral    | 4GB  | Faster generation        | Fast   |
| llama2:13b | 13GB | Better German/quality    | Slow   |
| codellama  | 7GB  | Technical outreach       | Medium |

## Performance Considerations

**Hardware Requirements:**

- **Minimum**: 8GB RAM for 7B models
- **Recommended**: 16GB RAM for 13B models
- **GPU**: Optional but significantly faster with CUDA/Metal support

**Generation Speed:**

- CPU only: 2-5 seconds per email
- With GPU: 0.5-1 second per email

**Quality:**

- Ollama models produce excellent results
- May need prompt tuning for your specific use case
- Test with a few runs before scaling up

## Troubleshooting

### Ollama not found

```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# If not running, start it
ollama serve
```

### Model download failed

```bash
# Check available disk space (models are large)
df -h

# Re-download model
ollama pull llama2
```

### Poor generation quality

1. Try a larger model: `ollama pull llama2:13b`
2. Adjust temperature in `email_writer.py` (default: 0.7)
3. Modify the system prompt for your use case

## Advanced Configuration

### Custom Models

You can use any Ollama-compatible model:

```bash
# List available models
ollama list

# Pull a specific model
ollama pull yourusername/yourmodel
```

Then update `.env`:

```env
OLLAMA_MODEL=yourusername/yourmodel
```

### Local llama.cpp (Alternative)

If you prefer llama.cpp instead of Ollama, you can modify `email_writer.py` to use llama-cpp-python. This requires more technical setup but offers more control.

## Benefits of Offline LLM

✅ **Privacy**: No data leaves your machine
✅ **Cost**: One-time setup vs ongoing API costs
✅ **Speed**: No network latency
✅ **Reliability**: No API rate limits or downtime
✅ **Customization**: Fine-tune models for your industry

## Next Steps

1. Install Ollama
2. Download llama2 model
3. Update `.env` with `LLM_MODE=ollama`
4. Restart backend
5. Run a test lead generation run
6. Compare results with OpenAI (if you have access)

For questions or issues, check the Ollama documentation at https://github.com/jmorganca/ollama
