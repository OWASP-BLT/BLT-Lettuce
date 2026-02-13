# Deployment Notes for Cloudflare Python Worker

## Project Recommendation System

The project recommendation system requires the `projects_metadata.json` file to be accessible to the worker. There are several approaches:

### Option 1: Include in Worker Bundle (Recommended)

The `projects_metadata.json` file (145KB) should be included in the worker deployment:

```bash
# Ensure the data directory is included in the worker bundle
wrangler deploy
```

The worker will load the file using:
```python
from project_recommender import load_projects_metadata
metadata = load_projects_metadata()
```

### Option 2: Use KV Storage

For better performance and easier updates, store the metadata in Cloudflare KV:

```bash
# Upload to KV
wrangler kv:key put --binding=PROJECTS_KV "metadata" data/projects_metadata.json

# Update worker.py to load from KV
metadata = await env.PROJECTS_KV.get("metadata", "json")
```

### Option 3: Fetch from GitHub

Fetch the metadata file from the repository at runtime:

```python
async def load_metadata_from_github():
    url = "https://raw.githubusercontent.com/OWASP-BLT/BLT-Lettuce/main/data/projects_metadata.json"
    response = await fetch(url)
    return await response.json()
```

## File Structure

The worker expects the following structure:
```
cloudflare-worker/
├── worker.py                  # Main worker
├── project_recommender.py     # Recommendation engine
├── wrangler.toml             # Wrangler config
└── ../data/
    └── projects_metadata.json # Project metadata
```

## Dependencies

The worker uses only Python standard library functions, making it compatible with Cloudflare Python Workers.

**No external dependencies required** for the recommendation engine.

## Testing Locally

Test the worker locally with Wrangler:

```bash
cd cloudflare-worker
wrangler dev
```

Then test the endpoints:

```bash
# Get available categories
curl http://localhost:8787/projects

# Get recommendations
curl -X POST http://localhost:8787/recommend \
  -H "Content-Type: application/json" \
  -d '{"approach":"technology","technology":"python","level":"beginner","top_n":3}'
```

## Updating Project Metadata

To update the project metadata:

1. Run the enrichment script:
   ```bash
   python3 scripts/enrich_projects.py
   ```

2. Redeploy the worker:
   ```bash
   cd cloudflare-worker
   wrangler deploy
   ```

Or upload to KV:
```bash
wrangler kv:key put --binding=PROJECTS_KV "metadata" data/projects_metadata.json
```

## Performance Considerations

- **Cold Start**: First request may be slower (~100-200ms) while loading metadata
- **Memory**: Metadata file is ~145KB, loaded once per worker instance
- **Caching**: Consider caching recommendations for common queries
- **Rate Limiting**: Implement rate limiting for public endpoints

## Monitoring

Monitor worker performance in Cloudflare dashboard:
- Request volume
- Error rate
- CPU time
- Memory usage

## Security Notes

- All endpoints are CORS-enabled for public access
- No authentication required for read-only recommendations
- Rate limiting recommended for production use
- Input validation performed on all recommendation parameters

## Troubleshooting

### Error: "Project recommendation service not available"
- Ensure `projects_metadata.json` is accessible
- Check file path in `load_projects_metadata()`
- Verify import of `project_recommender` module

### Error: "Failed to generate recommendations"
- Check request body format
- Verify required parameters (approach, technology/mission)
- Check worker logs: `wrangler tail`

### Empty Recommendations
- Technology/mission might not have matching projects
- Try fallback recommendations (don't specify criteria)
- Check available categories: `GET /projects`
