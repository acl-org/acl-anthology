# URL redirects

Permanent public URLs occasionally need to move after crawlers or other sites have
indexed them. Redirects are maintained in `hugo/redirects.yaml`; do not edit the
generated redirect block in `.htaccess` or the generated map directly.

The static build runs `bin/build_redirects.py` and produces two deployment artifacts:

- `build/static/.htaccess`, containing ordered pattern and special-case rules.
- `build/static/.acl-redirects.map`, containing simple exact `301` redirects.

Hugo copies both files to the root of the Anthology build output, beneath any
configured URL prefix. The official production build uses an Apache `RewriteMap`
for exact redirects. Branch previews and mirrors expand exact redirects into their
`.htaccess` instead, so they do not need a map declaration.

## Adding redirects

The registry is grouped into dated batches. Use one batch per date and list every
issue motivating any rule in that batch:

```yaml
version: 1

batches:
  - added: 2026-09-09
    issues:
      - 1234
      - 5678
    redirects:
      - from: /old-page/
        to: /new-page/
```

`added` must be an ISO date, and `issues` must contain one or more positive GitHub
issue numbers. A second batch with the same date is rejected; add its issues and
rules to the existing batch instead. Generated Apache comments retain the date and
issue list so deployed rules remain auditable.

Every redirect needs `from`. Redirecting statuses also need `to`; status `410` must
omit it. Sources are root-relative paths. Targets may be root-relative paths or
absolute HTTPS URLs.

The defaults are:

```yaml
match: exact
status: 301
query: preserve
case_sensitive: true
```

Supported `match` values are:

- `exact`: Match one complete path. Exact rules always take precedence over patterns.
- `prefix`: Match a literal path prefix and append the unmatched suffix to `to`. Use
  trailing slashes when redirecting a directory tree.
- `regex`: Match an Apache-compatible regular expression. It must start with `^/` and
  end with `$`. Targets may use `$1` through `$9` capture-group references.

Prefix and regex entries require `tests`. These are checked during every build and
also guard against redirect chains. The following belongs under a batch's
`redirects` key:

```yaml
- match: regex
  from: '^/old-papers/([0-9]+)/?$'
  to: '/papers/$1/'
  tests:
    - from: /old-papers/17/
      to: /papers/17/
```

Supported redirect statuses are `301`, `302`, `303`, `307`, and `308`. A removed URL
can return `410 Gone`:

```yaml
- from: /withdrawn-resource
  status: 410
  note: Resource was published accidentally
```

Query-string handling is explicit when the default is not suitable:

- `preserve`: Preserve the incoming query string. The target must not contain one.
- `discard`: Discard the incoming query string. The target must not contain one.
- `replace`: Replace it with the query string written in `to`.
- `append`: Add the query string written in `to` to the incoming query string.

For example:

```yaml
- from: /old-search
  to: /search?source=legacy
  status: 302
  query: append
```

Use `case_sensitive: false` only for a historically case-insensitive URL. Such an
entry is emitted as an Apache rule rather than placed in the exact-match map.

Run the focused checks after changing the registry:

```bash
uv run --frozen pytest tests/test_build_redirects.py
UV_FROZEN=1 make static
```

The compiler rejects unknown fields, malformed paths and patterns, duplicate exact
sources, duplicate batch dates, invalid issue lists, self-redirects, redirect chains,
pattern examples whose targets start another redirect, invalid statuses and query
policies, unsafe Apache expansion syntax, and bad capture-group references.

## Raw storage URLs

The build publishes the file store through an `anthology-files` symlink. Friendly
PDF URLs such as `/2026.lrec-1.104.pdf` are internally rewritten to that store; an
internal rewrite does not reveal its target to the client.

However, the production Apache server previously generated directory indexes for
the symlink. For example, `/anthology-files/pdf/lrec/` returned a browsable `Index
of` page containing every physical PDF filename. This allowed crawlers to discover
the storage URLs directly even though Hugo templates and sitemaps did not link them.
The root `.htaccess` now sets `Options -Indexes` to stop that enumeration and
returns `X-Robots-Tag: noindex` when a client requests an `anthology-files` URL
directly. The header tests Apache's original request line, so public PDF URLs that
are internally rewritten into the file store remain indexable.

Known storage URLs remain independently fetchable until they are canonicalized. A
follow-up issue should add permanent redirects from direct storage-file requests to
their friendly URLs. Those rules must check `%{THE_REQUEST}` so they only match paths
requested by the client; matching the rewritten URI would catch normal friendly
URLs on Apache's second rewrite pass and create a redirect loop. Do not use a
`robots.txt` disallow as the replacement: crawlers need to fetch known URLs to see
their permanent redirects.

After search engines have processed the redirects and `noindex` headers, crawling
can also be disabled at the host root if it remains a concern:

```text
User-agent: *
Disallow: /anthology-files/
```

Do not deploy that rule during cleanup. A URL blocked by `robots.txt` cannot be
recrawled, so Google cannot observe its redirect or `X-Robots-Tag` and may retain a
URL-only search result.

## One-time Apache setup

`RewriteMap` declarations are forbidden in `.htaccess`. The generated `.htaccess`
can use a map declared by its virtual host, so one server-side declaration is needed.

Before deploying the first build containing this mechanism, create the map at its
eventual deployment path. The publishing user already needs write access there:

```bash
ssh anthologizer@aclanthology.org \
  'touch /var/www/aclanthology.org/.acl-redirects.map'
```

Then add this inside every production virtual host whose requests traverse the
Anthology document root, normally both the HTTP and HTTPS virtual hosts:

```apache
RewriteEngine On
RewriteMap acl_redirects "txt:/var/www/aclanthology.org/.acl-redirects.map"

<Directory "/var/www/aclanthology.org">
    AllowOverride FileInfo Options
</Directory>
```

Do not reduce a broader existing `AllowOverride` setting. `FileInfo` permits the
rewrite directives and `Options` is already required by the citation CGI settings in
the existing `.htaccess`; this redirect mechanism adds no new override category.

Validate and gracefully reload Apache before deploying the repository change:

```bash
sudo apachectl configtest
sudo apachectl graceful
```

The map declaration remains stable. Apache caches `txt:` map lookups until the map
file's modification time changes, so subsequent site deployments update exact
redirects without an Apache reload. Pattern rules are read from the deployed
`.htaccess` in the usual way. Direct HTTP access to `.acl-redirects.map` returns 404.
