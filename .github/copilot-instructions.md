# ACL Anthology Copilot Instructions

## Project Overview
The ACL Anthology is a digital archive of NLP/CL research papers with both a static website generator and a Python package for metadata access. The project manages scholarly publication metadata through XML files and generates a Hugo-based website.

## Architecture & Data Flow

### Core Data Model
- **Authoritative XML files** in `data/xml/` contain all paper metadata (schema: `data/xml/schema.rnc`)
- **YAML configuration** in `data/yaml/` defines venues, SIGs, and name variants
- **Hugo static site** generated from processed JSON data in `build/data/`
- **Python package** (`python/acl_anthology/`) provides programmatic access to metadata

### Build Process Pipeline
1. **XML Processing**: `bin/create_hugo_data.py` converts XML → JSON for Hugo templates
2. **Bibliography Generation**: `bin/create_extra_bib.py` creates BibTeX/MODS/Endnote exports  
3. **Hugo Site Generation**: Hugo processes JSON data → static HTML site
4. **Asset Management**: PDF files, attachments managed separately with checksums

Key build targets in `Makefile`:
- `make all` - Full build (check + site)
- `make hugo_data` - Generate JSON data files only
- `make site` - Generate complete website
- `make check` - Validate XML schema compliance

## Critical ID System

### Modern Format (post-2020)
- Format: `YEAR.VENUE-VOLUME.NUMBER` (e.g., `2020.acl-main.12`)
- **VENUE**: lowercase alphanumeric venue identifier (no years!)
- **VOLUME**: volume name (`main`, `short`, `1`, etc.)
- **NUMBER**: paper number within volume

### Legacy Format (pre-2020)  
- Various letter-based schemes (P19-1234, W19-5012, etc.)
- Limited paper capacity, inflexible venue encoding

## Development Workflows

### XML Metadata Management
- All paper metadata lives in `data/xml/{COLLECTION_ID}.xml` files
- Use `bin/ingest_aclpub2.py` for bulk ingestion from conference data
- Individual modifications via scripts like `bin/add_author_id.py`, `bin/fix_titles.py`
- **Always validate with `make check`** after XML changes

### Author Name Handling
- Complex disambiguation system for author identity resolution
- Name variants stored in `data/yaml/name_variants.yaml`
- Scripts: `bin/find_name_variants.py`, `bin/auto_name_variants.py`
- Person IDs assigned automatically but can be explicitly set

### Testing Strategy
```bash
# Python package tests
cd python && poetry run pytest

# Full site build test  
make check site

# Integration tests on full data
pytest -m integration
```

## Project-Specific Patterns

### XML Structure Philosophy
- **Separation of content and presentation**: Raw metadata in XML, formatting via Hugo templates
- **Hierarchical organization**: Collections → Volumes → Papers
- **Checksum validation**: All file references include SHA-256 checksums (8-char prefix)

### Script Naming Conventions
- `add_*.py` - Add new metadata fields
- `fix_*.py` - Correct existing data
- `ingest_*.py` - Import data from external sources  
- `create_*.py` - Generate derived files

### Hugo Data Export Pattern
```python
# All export scripts follow this pattern:
def export_ENTITY(anthology, builddir, dryrun):
    # Process anthology data
    data = {...}
    if not dryrun:
        with open(f"{builddir}/data/{entity}.json", "wb") as f:
            f.write(ENCODER.encode(data))
```

## Environment Setup

### Dependencies
- **Python 3.10+** with packages from `bin/requirements.txt`
- **Hugo 0.126.0+** (extended version required)
- **bibutils** for citation format conversion
- **jing** for XML validation

### Development Commands
```bash
# Setup environment
python3 -m venv venv && source venv/bin/activate
pip install -r bin/requirements.txt

# Quick data regeneration (development)
make NOBIB=true hugo_data hugo

# Full production build
make all
```

## Key Integration Points

### External Data Sources
- **ACLPub2**: Conference management system data ingestion
- **Papers with Code**: Research code linking
- **CrossRef**: DOI metadata synchronization
- **Google Scholar**: Author profile integration

### File Management
- PDFs and attachments stored separately from metadata
- Environment variables: `ANTHOLOGY_PREFIX`, `ANTHOLOGYFILES`
- Symlinked as `anthology-files` in generated site

## Common Pitfalls
- **Never include years in venue identifiers** - venues are persistent entities
- **XML changes require `make check`** - schema validation is mandatory
- **Author name disambiguation is automatic** - manual overrides via explicit IDs only
- **Hugo memory usage is ~18GB** - normal on large sites, may cause swapping
- **Venue vs Event confusion** - venues are persistent, events are year-specific instances

## File Locations for Common Tasks
- **Add new venue**: `data/yaml/venues/{venue-id}.yaml`
- **Fix paper metadata**: Edit `data/xml/{collection}.xml` directly
- **Modify site templates**: `hugo/layouts/` 
- **Update build process**: `Makefile` and `bin/create_hugo_data.py`
