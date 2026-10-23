#!/bin/bash
# The runner already has bash, gh and jq. Do not install Python or scrape
# dependencies just to reuse an immutable daily release asset.
set -euo pipefail

# This asset is cumulative, not a dated completion marker.
if [[ "$LGD_COMPONENT" == TRANSACTIONS ]]; then
  exit 0
fi

release_id=$(jq -er '.release_id | select(type == "number" and . > 0)' <<< "$LGD_ASSIGNMENT")
asset_name=$(jq -er '.asset_name | select(type == "string" and length > 0)' <<< "$LGD_ASSIGNMENT")
if [[ "$asset_name" != *."$LGD_COLLECTION_DATE".csv.7z ]]; then
  echo '::error::Assigned asset does not match the collection date'
  exit 1
fi

# Slurp every page: an existing upload can be near the end of a full release.
asset=$(gh api "repos/$GITHUB_REPOSITORY/releases/$release_id/assets?per_page=100" \
  --paginate --slurp | jq -c --arg name "$asset_name" '
    [.[][] | select(.name == $name)] |
    if length > 1 then error("Duplicate release asset: " + $name) else .[0] end')
if [[ "$asset" == null ]]; then
  exit 0
fi
if jq -e '.state == "starter" and .size == 0' <<< "$asset" > /dev/null; then
  # The normal publisher removes empty failed-upload placeholders.
  exit 0
fi
jq -e '.state == "uploaded" and (.size | type == "number" and . > 0)
       and (.id | type == "number" and . > 0)' <<< "$asset" > /dev/null
if ! jq -e '.digest | strings | test("^sha256:[0-9a-f]{64}$")' <<< "$asset" > /dev/null; then
  # Older assets require the normal download-and-hash validation before reuse.
  echo "No server checksum for $asset_name; using the normal validation path."
  exit 0
fi

receipt=$(jq -c --arg component "$LGD_COMPONENT" --arg date "$LGD_COLLECTION_DATE" '
  {component: $component, date: $date, asset: {id, name, size, state, digest}}' <<< "$asset")
printf 'published=%s\n' "$receipt" >> "$GITHUB_OUTPUT"
echo "Reusing published $asset_name; skipping component setup and scraping."
