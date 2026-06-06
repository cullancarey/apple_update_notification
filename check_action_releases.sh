#!/usr/bin/env bash

set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: gh CLI is required. Install from https://cli.github.com/" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Error: gh is not authenticated. Run: gh auth login" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOWS_DIR="${ROOT_DIR}/.github/workflows"

if [[ ! -d "${WORKFLOWS_DIR}" ]]; then
  echo "Error: workflows directory not found at ${WORKFLOWS_DIR}" >&2
  exit 1
fi

trim() {
  local text="$1"
  text="${text#"${text%%[![:space:]]*}"}"
  text="${text%"${text##*[![:space:]]}"}"
  printf '%s' "$text"
}

tmp_uses_file="$(mktemp)"
tmp_repos_file="$(mktemp)"
trap 'rm -f "${tmp_uses_file}" "${tmp_repos_file}"' EXIT

while IFS= read -r line; do
  value="${line#*uses:}"
  value="$(trim "${value%%#*}")"
  value="${value%\"}"
  value="${value#\"}"
  value="${value%\'}"
  value="${value#\'}"

  if [[ -z "${value}" ]]; then
    continue
  fi

  if [[ "${value}" == ./* || "${value}" == docker://* ]]; then
    continue
  fi

  repo="${value%@*}"
  ref="${value#*@}"
  if [[ "${repo}" == "${value}" ]]; then
    ref="(no-ref)"
  fi

  if [[ -z "${repo}" || "${repo}" != */* ]]; then
    continue
  fi

  printf '%s\t%s\n' "$repo" "$ref" >>"${tmp_uses_file}"
done < <(grep -hE '^[[:space:]]*uses:[[:space:]]*' "${WORKFLOWS_DIR}"/*.yml "${WORKFLOWS_DIR}"/*.yaml 2>/dev/null)

if [[ ! -s "${tmp_uses_file}" ]]; then
  echo "No external action repositories found in ${WORKFLOWS_DIR}."
  exit 0
fi

awk -F '\t' '
  {
    key = $1 FS $2
    if (!seen[key]++) {
      if ($1 in refs) {
        refs[$1] = refs[$1] "|" $2
      } else {
        refs[$1] = $2
      }
      repos[$1] = 1
    }
  }
  END {
    for (repo in repos) {
      print repo "\t" refs[repo]
    }
  }
' "${tmp_uses_file}" | sort >"${tmp_repos_file}"

printf '%-45s %-28s %-20s %-20s %s\n' "Repository" "Current Ref(s)" "Latest Release" "Published" "URL"
printf '%-45s %-28s %-20s %-20s %s\n' "----------" "--------------" "--------------" "---------" "---"

while IFS=$'\t' read -r repo refs; do

  if release_info="$(gh release view --repo "$repo" --json tagName,publishedAt,url --jq '[.tagName,.publishedAt,.url] | @tsv' 2>/dev/null)"; then
    latest_tag="$(printf '%s' "$release_info" | cut -f1)"
    published="$(printf '%s' "$release_info" | cut -f2 | cut -c1-19)"
    release_url="$(printf '%s' "$release_info" | cut -f3)"
  else
    latest_tag="(none)"
    published="(n/a)"
    release_url="https://github.com/${repo}/releases"
  fi

  printf '%-45s %-28s %-20s %-20s %s\n' "$repo" "$refs" "$latest_tag" "$published" "$release_url"
done <"${tmp_repos_file}"
