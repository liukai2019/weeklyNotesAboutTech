#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LIBC_PATH=${LIBC_PATH:-/lib/x86_64-linux-gnu/libc.so.6}
OUTPUT_FILE=$(mktemp)

cleanup() {
	rm -f "${OUTPUT_FILE}"
	if [[ -n "${watcher_pid:-}" ]]; then
		kill "${watcher_pid}" 2>/dev/null || true
		wait "${watcher_pid}" 2>/dev/null || true
	fi
	if [[ -n "${target_pid:-}" ]]; then
		wait "${target_pid}" 2>/dev/null || true
	fi
}
trap cleanup EXIT

make -C "${ROOT_DIR}"

nm -D "${LIBC_PATH}" | grep -q ' getaddrinfo@@'

if [[ ${EUID} -ne 0 ]]; then
	echo "Runtime verification needs sudo in this environment. Re-run with: sudo $0" >&2
	exit 1
fi

sh -c 'sleep 2; exec curl -s http://example.com >/dev/null' &
target_pid=$!

timeout -s INT 10s "${ROOT_DIR}/dns-watch" -p "${target_pid}" -l "${LIBC_PATH}" >"${OUTPUT_FILE}" &
watcher_pid=$!

wait "${target_pid}" || true
if ! wait "${watcher_pid}"; then
	status=$?
	if [[ ${status} -ne 124 ]]; then
		exit "${status}"
	fi
fi

grep -Eq 'query_name=example\.com .*resolver_call_latency_ms=' "${OUTPUT_FILE}"
cat "${OUTPUT_FILE}"
