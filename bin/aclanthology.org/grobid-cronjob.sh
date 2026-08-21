#!/bin/bash
#
# Routine server job: keep GROBID running and extract full text for any PDF
# that does not yet have an up-to-date extraction under $ANTHOLOGYFILES/grobid.
#
# Install as a cron entry, e.g. nightly at 03:20:
#
#   20 3 * * * /home/anthology/acl-anthology/bin/aclanthology.org/grobid-cronjob.sh >> /var/log/anthology/grobid.log 2>&1
#
# Everything is configured through the environment; the defaults match a
# checkout at ~/acl-anthology serving files from ~/anthology-files.

set -euo pipefail

GITDIR=${GITDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}
export ANTHOLOGYFILES=${ANTHOLOGYFILES:-$HOME/anthology-files}

# Set to true to fast-forward the checkout before scanning, so PDFs ingested
# since the last run are visible. Leave false if something else updates it.
GROBID_GIT_PULL=${GROBID_GIT_PULL:-false}

GROBID_IMAGE=${GROBID_IMAGE:-grobid/grobid:0.9.0-full}
GROBID_CONTAINER=${GROBID_CONTAINER:-acl-anthology-grobid}
GROBID_PORT=${GROBID_PORT:-8070}
export GROBID_URL=${GROBID_URL:-http://localhost:$GROBID_PORT}
GROBID_STARTUP_TIMEOUT=${GROBID_STARTUP_TIMEOUT:-300}

# Concurrent extraction requests, and an optional cap on how many papers a
# single run may send to GROBID (useful while backfilling the corpus).
GROBID_JOBS=${GROBID_JOBS:-4}
GROBID_LIMIT=${GROBID_LIMIT:-}

LOCKFILE=${GROBID_LOCKFILE:-/tmp/acl-anthology-grobid-fulltext.lock}

# cron runs with a minimal PATH that usually omits ~/.local/bin.
UV=${UV:-uv}

log() {
    echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') $*"
}

# Runs can be long; never let a second one start on top of the first.
if [[ -z ${GROBID_CRONJOB_LOCKED:-} ]]; then
    if ! command -v flock >/dev/null 2>&1; then
        log "FATAL flock is required to serialize runs (util-linux)"
        exit 1
    fi
    export GROBID_CRONJOB_LOCKED=1
    exit_code=0
    flock --nonblock --conflict-exit-code 99 "$LOCKFILE" "$0" "$@" || exit_code=$?
    if [[ $exit_code -eq 99 ]]; then
        log "another extraction run holds $LOCKFILE; exiting"
        exit 0
    fi
    exit "$exit_code"
fi

if ! command -v "$UV" >/dev/null 2>&1; then
    log "FATAL uv was not found on PATH=$PATH; set UV=/path/to/uv"
    exit 1
fi

grobid_is_alive() {
    curl -fsS "$GROBID_URL/api/isalive" 2>/dev/null | grep -qx true
}

# Docker is only needed to run the service. Point GROBID_URL at a GROBID
# installed some other way, or on another host, and it is never used.
if ! grobid_is_alive; then
    if ! docker info >/dev/null 2>&1; then
        log "FATAL no GROBID at $GROBID_URL, and Docker is not available to start one"
        exit 1
    fi

    if docker inspect "$GROBID_CONTAINER" >/dev/null 2>&1; then
        log "starting existing container $GROBID_CONTAINER"
        docker start "$GROBID_CONTAINER" >/dev/null
    else
        log "creating container $GROBID_CONTAINER from $GROBID_IMAGE"
        docker run --detach \
            --name "$GROBID_CONTAINER" \
            --restart unless-stopped \
            --init \
            --ulimit core=0 \
            --publish "127.0.0.1:$GROBID_PORT:8070" \
            "$GROBID_IMAGE" >/dev/null
    fi

    log "waiting up to ${GROBID_STARTUP_TIMEOUT}s for GROBID at $GROBID_URL"
    for _ in $(seq 1 "$GROBID_STARTUP_TIMEOUT"); do
        if grobid_is_alive; then
            break
        fi
        if [[ $(docker inspect --format '{{.State.Running}}' "$GROBID_CONTAINER" 2>/dev/null) != true ]]; then
            log "FATAL GROBID stopped before becoming ready; recent logs:"
            docker logs --tail 50 "$GROBID_CONTAINER"
            exit 1
        fi
        sleep 1
    done
fi

if ! grobid_is_alive; then
    log "FATAL GROBID did not become ready; recent logs:"
    docker logs --tail 50 "$GROBID_CONTAINER" 2>/dev/null || true
    exit 1
fi

cd "$GITDIR"
if [[ $GROBID_GIT_PULL == true ]]; then
    log "updating checkout in $GITDIR"
    git pull --ff-only -q
fi

extract_args=(
    --all
    --jobs "$GROBID_JOBS"
    --pdf-root "$ANTHOLOGYFILES/pdf"
    --output-root "$ANTHOLOGYFILES/grobid"
)
if [[ -n $GROBID_LIMIT ]]; then
    extract_args+=(--limit "$GROBID_LIMIT")
fi

log "extracting full text (jobs=$GROBID_JOBS, limit=${GROBID_LIMIT:-none})"
"$UV" run python bin/grobid/extract_pdf_fulltext.py "${extract_args[@]}"
log "extraction finished"
