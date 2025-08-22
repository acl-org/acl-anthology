---
applyTo: 'data/xml/*.xml'
---

# Processing ACL Anthology Author Page Issues

This guide provides instructions for processing GitHub issues requesting author page corrections in the ACL Anthology. There are two types of requests: **merging** and **splitting** author pages.

## Prerequisites & Requirements

All author page requests **must** include:
- **GitHub issue number** (e.g., `#123`)
- **The author ID** (e.g., `matt-post` or `matt-post-rochester`)
- **Valid ORCID ID** (format: `0000-0000-0000-0000`)
- **Institution** where highest (anticipated) degree was/will be obtained
- **Requested action** (merge or split)
- **Clear identification** of which papers belong to the author (in the case of a split)

Ideally, this input will be in the form of a JSON object. Here is an example input for merging:

```json
{
    "github_issue": "#123",
    "canonical": "Post, Matt",
    "variants": [
        "Post, Matthew",
        "Post, Matthew J"
    ],
    "author_id": "matt-post", 
    "orcid": "0000-0000-0000-0000",
    "institution": "University of Rochester",
    "action": "merge",
}
```

and for splitting:

```json
{
    "github_issue": "#123",
    "author_id": "matt-post-rochester",
    "orcid": "0000-0000-0000-0000",
    "institution": "University of Rochester",
    "action": "split",
    "papers": [
        "2024.acl-main.17",
        "2018.wmt-1.67"
    ]
}
```

## Workflow Overview

1. **Setup**: Ensure master branch is up to date, create working branch
2. **Process**: Make required changes based on request type (merge or split)
3. **Validate**: Run checks to ensure changes are correct
4. **Submit**: Commit changes and create PR referencing the issue

## Initial Setup

### 1. Update and Create Branch

```bash
# Ensure master is up to date
git checkout master
git pull origin master

# Create branch using the pattern: author-page-{author_id}
git checkout -b author-page-{author_id}
```

**Branch naming examples**:
- Merge: `author-page-matt-post`
- Split: `author-page-matt-post-rochester`

## Request Type 1: Merging Author Pages

**Use case**: Author has published under multiple name variants and wants them consolidated under a canonical name.

**Example**: "Matt Post" and "Matthew Post" should be merged under "Matt Post".

### Steps:

1. **Add entry to `data/yaml/name_variants.yaml`**:
   ```yaml
   - canonical: {first: Matt, last: Post}
     orcid: 0000-0000-0000-0000
     institution: Johns Hopkins University  # Include even though not currently used
     variants:
     - {first: Matthew, last: Post}
   ```

2. **Check out the branch, merging off master**:

```bash
# Ensure master is up to date
git checkout master
git pull origin master

# Create branch using the pattern: author-page-{author_id}
git checkout -b author-page-{author_id}
```

3. **Commit to the branch, noting the Github issue being closed**

```bash
git add data/yaml/name_variants.yaml
git commit -m "Merging author pages for {author_name} (closes #{issue_number})"
```

**Important notes**:
- Canonical name should be the author's preferred variant
- Include all name variants found in the XML files
- The `institution` field should be included for future use
- Do not create an `id` field (this is only for splitting)

## Request Type 2: Splitting Author Pages

**Use case**: Multiple authors published under the same name and need to be separated.

**Example**: Papers under "Matt Post" are actually from different people - separate out the papers belonging to the requester.

### Steps:

#### 2.1 Create Author ID for Requester

Add entry to `data/yaml/name_variants.yaml`:
```yaml
- canonical: {first: Matt, last: Post}
  id: matt-post-rochester  # Format: firstname-lastname-institution
  orcid: 0000-0000-0000-0000
  institution: University of Rochester
```

**ID format rules**:
- Lowercase only
- Hyphens replace spaces
- Use recognizable institution abbreviation
- Examples: `yang-liu-umich`, `john-smith-stanford`, `jane-doe-google`

#### 2.2 Tag Author's Papers

Use the `bin/add_author_id.py` script to efficiently add the ID to all papers belonging to the requester:

```bash
# Add ID to all papers by the author's first and last name
bin/add_author_id.py matt-post-rochester --first-name "Matt" --last-name "Post"
```

This will add the `id` attribute to matching `<author>` tags:

```xml
<!-- Before -->
<author><first>Matt</first><last>Post</last></author>

<!-- After -->
<author id="matt-post-rochester"><first>Matt</first><last>Post</last></author>
```

**Note**: The script automatically maintains proper XML formatting and preserves indentation.

#### 2.3 Handle Remaining Papers

For papers that don't belong to the requester (the "other" Matt Post):

If there is no entry in the YAML file, create one.
```yaml
- canonical: {first: Matt, last: Post}
  id: matt-post
  comment: "May refer to several people"
```

Then, use the `bin/add_author_id.py` script to efficiently add the ID to all untagged papers:

```bash
# Add ID to all papers by the author's first and last name
bin/add_author_id.py matt-post --first-name "Matt" --last-name "Post"
```

### Helper Tools

- `bin/add_author_id.py author-id --last-name "LastName"` - Bulk add ID to matching authors
- `bin/add_explicit_author_id.py` - Add IDs based on existing disambiguation

## Validation & Testing

### Required Checks

```bash
# Validate XML schema compliance
make check

# Test data generation
make hugo_data
```

### Common Issues to Avoid

- **Invalid ORCID format**: Must be exactly `0000-0000-0000-0000`
- **XML formatting**: Don't break single-line `<author>` tags into multiple lines
- **Duplicate IDs**: Ensure new author IDs are unique
- **Missing canonical**: Canonical name must match one existing name variant

## File Locations

- **Name variants**: `data/yaml/name_variants.yaml`
- **Paper metadata**: `data/xml/{year}.{venue}.xml` (e.g., `2020.acl-main.xml`)

## Examples

### Merge Example
```yaml
# Merging "John P. Smith" and "John Smith" 
- canonical: {first: John P., last: Smith}
  orcid: 0000-0002-1234-5678
  institution: Stanford University
  variants:
  - {first: John, last: Smith}
  - {first: J. P., last: Smith}
```

### Split Example
```yaml
# Splitting "Yang Liu" - requester from University of Michigan
- canonical: {first: Yang, last: Liu}
  id: yang-liu-umich
  orcid: 0000-0003-1234-5678
  institution: University of Michigan

# Generic entry for remaining papers
- canonical: {first: Yang, last: Liu}
  id: yang-liu
  comment: "May refer to several people"
```

## Completion

### 1. Commit Changes

```bash
# Add all modified files
git add data/yaml/name_variants.yaml data/xml/*.xml

# Commit with reference to issue number
git commit -m "Process author page request for {Author Name}

Closes #{issue_number}

- {Brief description of changes made}
"

# Push branch
git push origin author-page-{author_id}
```

### 2. Create Pull Request

- **Title**: `Author page: {Author Name} ({merge|split})`
- **Body**: Reference the GitHub issue number and summarize changes
- **Labels**: Add appropriate labels (`author-page`, `merge` or `split`)

The PR will trigger automated builds and tests. Once merged, the changes will be reflected in the next site build.
For each paper belonging to the disambiguated author, add `id` attribute to XML:

**Example**: In `data/xml/2020.acl.xml`:
```xml
<paper id="123">
  <author id="yang-liu-umich"><first>Yang</first><last>Liu</last></author>
  <!-- Other metadata -->
</paper>
```

**Formatting Requirements**:
- Keep `<author>` tags on single line (don't expand to multiple lines)
- Preserve existing indentation and spacing patterns
- Use existing XML formatting tools to maintain consistency

**Tools available**:
- `bin/add_author_id.py author-id --last-name "LastName"` - Bulk add ID to author
- `bin/add_explicit_author_id.py` - Add IDs based on existing disambiguation

#### 4.3 Handle Remaining Papers  
For papers that don't belong to the author with the explicit ID:
1. **Option A**: Leave unchanged (they remain under generic ID)
2. **Option B**: Create another explicit ID for the other author if requested

#### 4.4 Update Similar Authors (if applicable)
If multiple authors have similar names, add `similar` field:
```yaml
- canonical: {first: Yang, last: Liu}
  id: yang-liu-umich
  orcid: 0000-0000-0000-0000
  similar: [yang-liu-edinburgh, yang-liu-pk]
```

## ID Generation Rules

### Author ID Format
- **Structure**: `firstname-lastname-institution`
- **Rules**: 
  - Lowercase only
  - Hyphens replace spaces and special characters
  - Institution should be recognizable abbreviation
  - Examples: `yang-liu-umich`, `john-smith-stanford`

### Institution Abbreviations
Common patterns:
- Universities: `umich`, `stanford`, `cmu`, `mit`
- Companies: `google`, `microsoft`, `facebook`
- Use domain-based abbreviations when possible

## Validation and Testing

### Required Checks
```bash
# Validate XML schema compliance
make check

# Test site generation with changes
make hugo_data

# Full build test (if making significant changes)
make site
```

### Formatting Consistency
- **XML**: Preserve single-line formatting for `<author>` and `<editor>` tags
- **YAML**: Follow existing indentation (2 spaces) and structure in `name_variants.yaml`
- **Use project tools**: Scripts like `bin/add_author_id.py` maintain proper formatting automatically
- **Indentation**: Use `anthology.utils.indent()` function for XML pretty-printing when needed

### Common Issues
- **Invalid ORCID format**: Must be `0000-0000-0000-0000`
- **XML schema violations**: Missing required fields, invalid nesting
- **Name mismatches**: Canonical name not matching any existing papers
- **Duplicate IDs**: Ensure new author IDs are unique

## File Locations

- **Name variants**: `data/yaml/name_variants.yaml`
- **XML metadata**: `data/xml/{collection}.xml` (e.g., `2020.acl.xml`)
- **Validation script**: `make check`
- **Author ID tools**: `bin/add_author_id.py`, `bin/add_explicit_author_id.py`

## Examples

### Merge Example
```yaml
# Merging "John P. Smith" and "John Smith" profiles
- canonical: {first: John P., last: Smith}
  orcid: 0000-0002-1234-5678
  variants:
  - {first: John, last: Smith}
  - {first: J. P., last: Smith}
```

### Split Example  
```yaml
# Splitting "Yang Liu" into institution-specific profiles
- canonical: {first: Yang, last: Liu}
  id: yang-liu-umich
  orcid: 0000-0003-1234-5678
  comment: University of Michigan
  similar: [yang-liu-edinburgh]
```

With corresponding XML updates:
```xml
<author id="yang-liu-umich"><first>Yang</first><last>Liu</last></author>
```

**Note**: Maintain single-line format for author tags as shown above.

## Post-Processing

### 1. Commit and Push Changes
```bash
# Add all changes
git add data/yaml/name_variants.yaml data/xml/*.xml

# Commit with descriptive message
git commit -m "Author page correction: {author-name} ({merge|split})"

# Push branch
git push origin author-page-{authorid}
```

### 2. Create Pull Request
- **Title**: `Author page correction: {Author Name} ({merge|split})`
- **Body**: Include link to original GitHub issue and summary of changes
- **Labels**: Add `correction`, `metadata` labels
- **Assignees**: Add `anthology-assist`

### 3. Post-PR Actions
1. **Update GitHub issue**: Comment with link to PR and close original issue
2. **Monitor build**: Ensure site builds successfully after merge
3. **Verify author pages**: Check that author pages display correctly on staging/live site
4. **Archive decision**: Document rationale for complex disambiguation cases
