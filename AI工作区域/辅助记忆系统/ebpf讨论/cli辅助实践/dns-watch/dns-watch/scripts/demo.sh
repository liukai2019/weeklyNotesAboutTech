#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LIBC_PATH=${LIBC_PATH:-/lib/x86_64-linux-gnu/libc.so.6}

if [[ ${EUID} -ne 0 ]]; then
	echo "Run with sudo so dns-watch can attach uprobes in this WSL2 environment." >&2
	exit 1
fi

make -C "${ROOT_DIR}"

cleanup() {
	if [[ -n "${target_pid:-}" ]]; then
		wait "${target_pid}" 2>/dev/null || true
	fi
}
trap cleanup EXIT

sh -c 'sleep 2; exec curl -s http://example.com >/dev/null' &
target_pid=$!

echo "Tracing PID ${target_pid} with dns-watch. Expect one example.com event line."
timeout -s INT 10s "${ROOT_DIR}/dns-watch" -p "${target_pid}" -l "${LIBC_PATH}" || {
	status=$?
	if [[ ${status} -ne 124 ]]; then
		exit "${status}"
	fi
}
