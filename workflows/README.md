# Workflow Exports

These are n8n-compatible workflow JSON files representing the Clara Agent Ops Pipeline.

## How to Import into n8n

1. Open n8n (self-hosted or cloud)
2. Go to **Workflows → Import from file**
3. Select `demo_pipeline.json` or `onboard_pipeline.json`
4. Set environment variables in n8n settings:
   - `GEMINI_API_KEY`
   - `GH_TOKEN`
   - `GH_REPO`

## Architecture

Both workflows use **Webhook triggers** — POST a file path to start the pipeline.

### Pipeline A (demo_pipeline.json)