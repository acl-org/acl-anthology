set script-interpreter := ['uv', 'run', '--script']

docker_config_image := "{{.Config.Image}}"
docker_state_running := "{{.State.Running}}"

@_default:
    just -l
    echo -e "\npython:"
    just -l python

# Call recipes from the Python library
mod python

# Run checks
check:
    make check

# Upgrade uv-managed dependencies in root workspace and python/ package
upgrade:
    uv sync --upgrade
    cd python && uv sync --upgrade

# Upgrade Hugo to new version in Github workflows & README
upgrade-hugo-version VERSION:
    sed -i 's/HUGO_VERSION: .*$/HUGO_VERSION: {{ VERSION }}/' .github/workflows/*.yml
    sed -i 's/Hugo [0-9.]\+/Hugo {{ VERSION }}/' README.md README_detailed.md
    sed -i 's/hugo >= [0-9.]\+/hugo >= {{ VERSION }}/' README.md

# Build website in production mode
build:
  make site

# Build website in development mode and serve via Hugo's webserver
serve ENV='development' NOBIB='true':
    make NOBIB={{ NOBIB }} static hugo_data bib
    cd build/ && hugo server --environment {{ ENV }}

# Start a reusable local GROBID service for PDF extraction
grobid:
    #!/usr/bin/env bash
    set -euo pipefail

    grobid_version=${GROBID_VERSION:-0.9.0}
    grobid_image=${GROBID_IMAGE:-grobid/grobid:${grobid_version}-full}
    grobid_container=${GROBID_CONTAINER:-acl-anthology-grobid}
    grobid_port=${GROBID_PORT:-8070}
    grobid_url=${GROBID_URL:-http://localhost:${grobid_port}}
    grobid_platform=${GROBID_PLATFORM:-linux/amd64}
    startup_timeout=${GROBID_STARTUP_TIMEOUT:-300}

    if ! command -v docker >/dev/null 2>&1; then
      echo "FATAL    Docker is required to run GROBID."
      echo "         Install Docker Desktop: https://docs.docker.com/desktop/"
      exit 1
    fi
    if ! docker info >/dev/null 2>&1; then
      echo "FATAL    Docker is installed, but its daemon is not running."
      echo "         Start Docker Desktop, then run 'just grobid' again."
      exit 1
    fi

    existing_image=$(docker inspect --format '{{ docker_config_image }}' "$grobid_container" 2>/dev/null || true)
    replaced_container=false
    if [[ -n $existing_image && $existing_image != "$grobid_image" ]]; then
      echo "INFO     Replacing $grobid_container ($existing_image) with $grobid_image..."
      docker rm -f "$grobid_container" >/dev/null
      existing_image=""
      replaced_container=true
    fi
    if [[ $replaced_container != true ]] && curl -fsS "$grobid_url/api/isalive" 2>/dev/null | grep -qx true; then
      echo "INFO     GROBID is already ready at $grobid_url."
      exit 0
    fi

    if [[ -n $existing_image ]]; then
      if [[ $(docker inspect --format '{{ docker_state_running }}' "$grobid_container") != true ]]; then
        echo "INFO     Starting existing GROBID container..."
        docker start "$grobid_container" >/dev/null
      else
        echo "INFO     Waiting for the running GROBID container..."
      fi
    else
      echo "INFO     Pulling and starting $grobid_image..."
      docker run --detach \
        --name "$grobid_container" \
        --platform "$grobid_platform" \
        --init \
        --ulimit core=0 \
        --publish "$grobid_port:8070" \
        "$grobid_image" >/dev/null
    fi

    echo "INFO     Waiting for GROBID to become ready..."
    for _ in $(seq 1 "$startup_timeout"); do
      if curl -fsS "$grobid_url/api/isalive" 2>/dev/null | grep -qx true; then
        version=$(curl -fsS "$grobid_url/api/version" 2>/dev/null || true)
        echo "INFO     GROBID ${version:-unknown} is ready at $grobid_url."
        exit 0
      fi
      if [[ $(docker inspect --format '{{ docker_state_running }}' "$grobid_container" 2>/dev/null) != true ]]; then
        echo "FATAL    GROBID stopped before becoming ready. Recent logs:"
        docker logs --tail 50 "$grobid_container"
        exit 1
      fi
      sleep 1
    done

    echo "FATAL    GROBID did not become ready within $startup_timeout seconds. Recent logs:"
    docker logs --tail 50 "$grobid_container"
    exit 1

# Extract full text for every PDF without a current extraction
fulltext: grobid
    #!/usr/bin/env bash
    set -euo pipefail

    anthology_files=${ANTHOLOGYFILES:-/var/www/anthology-files}
    grobid_jobs=${GROBID_JOBS:-4}
    grobid_port=${GROBID_PORT:-8070}
    grobid_url=${GROBID_URL:-http://localhost:${grobid_port}}

    uv run python bin/grobid/extract_pdf_fulltext.py --all \
      --jobs "$grobid_jobs" \
      --grobid-url "$grobid_url" \
      --pdf-root "$anthology_files/pdf" \
      --output-root "$anthology_files/grobid"

# Fetch an Anthology item and print it
[script]
print ANTHOLOGYID:
    from acl_anthology import Anthology
    from rich import print
    item = Anthology.from_within_repo().get("{{ ANTHOLOGYID }}")
    print(item)

# Fetch an Anthology item and print its XML representation
[script]
print-xml ANTHOLOGYID:
    from acl_anthology import Anthology
    from acl_anthology.utils.xml import indent
    from lxml import etree
    item = Anthology.from_within_repo().get("{{ ANTHOLOGYID }}").to_xml()
    indent(item)
    print(etree.tostring(item, encoding="utf-8").decode())
