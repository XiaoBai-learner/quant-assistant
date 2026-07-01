# a-stock-data Notice

This project plans to integrate data-source ideas, endpoint knowledge, and selected implementation patterns from:

- Repository: `https://github.com/simonlin1212/a-stock-data`
- Author: Simon Lin
- Referenced version: `SKILL.md` V3.3.0
- License: Apache License 2.0

## License Compatibility

`a-stock-data` is licensed under Apache License 2.0. `quant-assistant` is currently licensed as MIT in `pyproject.toml`.

Apache 2.0 code and documentation can be used in this project if we:

- Keep a copy of or reference to the Apache 2.0 license.
- Preserve copyright and attribution notices.
- Mark modified files where code is adapted rather than copied verbatim.
- Avoid implying that the upstream author endorses this project.

## Integration Policy

We will not copy `SKILL.md` wholesale into runtime code. Instead, we will:

- Re-implement providers in the local project style.
- Keep endpoint attribution in documentation.
- Write local tests for each provider.
- Normalize external fields into project-owned schemas.
- Add rate limits and retry policies appropriate for production use.

## Upstream Copyright

The upstream LICENSE includes:

```text
Copyright 2026 Simon Lin

Licensed under the Apache License, Version 2.0
```

## Files Influenced By Upstream

When implementation starts, files adapted from upstream endpoint code should include a short module comment such as:

```python
"""EastMoney provider.

Endpoint references are derived from simonlin1212/a-stock-data (Apache 2.0).
Implementation is adapted for quant-assistant provider interfaces, caching,
rate limiting, and schema normalization.
"""
```

## Data Source Terms

This notice only covers the upstream repository license. The external data providers themselves may have their own terms, rate limits, anti-abuse policies, and availability constraints. The project must use conservative request rates and cache data locally for research workflows.
