#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-${1:-https://api.edunova.xin}}"
FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-${2:-https://edunova.xin}}"
COURSE_ID="${COURSE_ID:-${3:-17}}"
TOKEN="${TOKEN:-${4:-}}"
APP_DIR="${APP_DIR:-/home/admin/project/edunova}"

FAILURES=0

hr() {
  printf '\n==== %s ====\n' "$1"
}

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  FAILURES=$((FAILURES + 1))
}

pass() {
  printf 'PASS: %s\n' "$1"
}

curl_json() {
  local url="$1"
  shift
  curl -fsS "$url" "$@"
}

auth_headers=()
if [[ -n "$TOKEN" ]]; then
  auth_headers=(-H "Authorization: Bearer $TOKEN")
fi

hr "Configuration"
printf 'API_BASE=%s\n' "$API_BASE"
printf 'FRONTEND_ORIGIN=%s\n' "$FRONTEND_ORIGIN"
printf 'COURSE_ID=%s\n' "$COURSE_ID"
printf 'APP_DIR=%s\n' "$APP_DIR"
if [[ -n "$TOKEN" ]]; then
  pass "Authorization token provided"
else
  printf 'INFO: no TOKEN provided, public-access checks only\n'
fi

hr "Local Health"
if local_health="$(curl_json "http://127.0.0.1:5001/api/health")"; then
  if PAYLOAD="$local_health" python3 - <<'PY'
import json, os
data = json.loads(os.environ["PAYLOAD"])
raise SystemExit(0 if data.get("status") == "ok" else 1)
PY
  then
    pass "Gunicorn health endpoint returned status=ok"
  else
    fail "Gunicorn health payload did not contain status=ok"
  fi
else
  fail "Unable to reach local Gunicorn health endpoint"
fi

hr "Public Health"
if public_health="$(curl_json "$API_BASE/api/health")"; then
  if PAYLOAD="$public_health" python3 - <<'PY'
import json, os
data = json.loads(os.environ["PAYLOAD"])
raise SystemExit(0 if data.get("status") == "ok" else 1)
PY
  then
    pass "Public health endpoint returned status=ok"
  else
    fail "Public health payload did not contain status=ok"
  fi
else
  fail "Unable to reach public health endpoint"
fi

hr "CORS Preflight"
preflight_headers="$(mktemp)"
if curl -fsS -D "$preflight_headers" -o /dev/null -X OPTIONS "$API_BASE/api/courses" \
  -H "Origin: $FRONTEND_ORIGIN" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: authorization"; then
  if grep -iq "^access-control-allow-origin: $FRONTEND_ORIGIN" "$preflight_headers" \
    && grep -iq "^access-control-allow-headers: .*Authorization" "$preflight_headers" \
    && grep -iq "^access-control-allow-methods: .*GET.*OPTIONS" "$preflight_headers"; then
    pass "Course list preflight contains required CORS headers"
  else
    fail "Course list preflight headers are incomplete"
  fi
else
  fail "Course list preflight request failed"
fi

detail_preflight_headers="$(mktemp)"
if curl -fsS -D "$detail_preflight_headers" -o /dev/null -X OPTIONS "$API_BASE/api/courses/$COURSE_ID" \
  -H "Origin: $FRONTEND_ORIGIN" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: authorization"; then
  if grep -iq "^access-control-allow-origin: $FRONTEND_ORIGIN" "$detail_preflight_headers" \
    && grep -iq "^access-control-allow-headers: .*Authorization" "$detail_preflight_headers" \
    && grep -iq "^access-control-allow-methods: .*GET.*OPTIONS" "$detail_preflight_headers"; then
    pass "Course detail preflight contains required CORS headers"
  else
    fail "Course detail preflight headers are incomplete"
  fi
else
  fail "Course detail preflight request failed"
fi

rm -f "$preflight_headers" "$detail_preflight_headers"

hr "Course List"
if course_list="$(curl_json "$API_BASE/api/courses?page=1&per_page=9&search=&category=&difficulty=" "${auth_headers[@]}")"; then
  if PAYLOAD="$course_list" python3 - <<'PY'
import json, os
data = json.loads(os.environ["PAYLOAD"])
raise SystemExit(0 if isinstance(data.get("courses"), list) and "total" in data else 1)
PY
  then
    pass "Course list endpoint returned courses[] and total"
  else
    fail "Course list payload shape is unexpected"
  fi
else
  fail "Course list request failed"
fi

hr "Course Detail"
if course_detail="$(curl_json "$API_BASE/api/courses/$COURSE_ID" "${auth_headers[@]}")"; then
  if PAYLOAD="$course_detail" python3 - <<'PY'
import json, os
data = json.loads(os.environ["PAYLOAD"])
raise SystemExit(0 if data.get("id") and data.get("name") else 1)
PY
  then
    pass "Course detail endpoint returned id and name"
  else
    fail "Course detail payload shape is unexpected"
  fi
else
  fail "Course detail request failed"
fi

hr "Materials"
if materials="$(curl_json "$API_BASE/api/courses/$COURSE_ID/materials" "${auth_headers[@]}")"; then
  if PAYLOAD="$materials" python3 - <<'PY'
import json, os
data = json.loads(os.environ["PAYLOAD"])
raise SystemExit(0 if isinstance(data.get("materials"), list) and "total" in data else 1)
PY
  then
    pass "Materials endpoint returned materials[] and total"
  else
    fail "Materials payload shape is unexpected"
  fi
else
  fail "Materials request failed"
fi

hr "Result"
if [[ "$FAILURES" -gt 0 ]]; then
  printf 'Self-check finished with %s failure(s).\n' "$FAILURES" >&2
  exit 1
fi

printf 'Self-check passed with no failures.\n'
