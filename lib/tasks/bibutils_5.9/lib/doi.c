/*
 * doi.c
 *
 * doi_to_url()
 * Handle outputing DOI as a URL (Endnote and RIS formats)
 *     1) Append http://dx.doi.org as necessary
 *     2) Check for overlap with pre-existing URL for the DOI
 *
 * is_doi()
 * Check for DOI buried in another field.
 *
 * Copyright (c) Chris Putnam 2008-2016
 *
 * Source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "newstr.h"
#include "fields.h"

static void
construct_url( char *prefix, newstr *id, newstr *id_url )
{
	if ( !strncasecmp( id->data, "http:", 5 ) )
		newstr_newstrcpy( id_url, id );
	else {
		newstr_strcpy( id_url, prefix );
		if ( id->data[0]!='/' ) newstr_addchar( id_url, '/' );
		newstr_newstrcat( id_url, id );
	}
}

static int
url_exists( fields *f, char *urltag, newstr *doi_url )
{
	int i, n;
	if ( urltag ) {
		n = fields_num( f );
		for ( i=0; i<n; ++i ) {
			if ( strcmp( fields_tag( f, i, FIELDS_CHRP ), urltag ) ) continue;
			if ( strcmp( fields_value( f, i, FIELDS_CHRP ), doi_url->data ) ) continue;
			return 1;
		}
	}
	return 0;
}

static void
xxx_to_url( fields *f, int n, char *http_prefix, char *urltag, newstr *xxx_url )
{
	newstr_empty( xxx_url );
	construct_url( http_prefix, fields_value( f, n, FIELDS_STRP ), xxx_url );
	if ( url_exists( f, urltag, xxx_url ) )
		newstr_empty( xxx_url );
}
void
doi_to_url( fields *f, int n, char *urltag, newstr *url )
{
	xxx_to_url( f, n, "http://dx.doi.org", urltag, url );
}
void
jstor_to_url( fields *f, int n, char *urltag, newstr *url )
{
	xxx_to_url( f, n, "http://www.jstor.org/stable", urltag, url );
}
void
pmid_to_url( fields *f, int n, char *urltag, newstr *url )
{
	xxx_to_url( f, n, "http://www.ncbi.nlm.nih.gov/pubmed", urltag, url );
}
void
pmc_to_url( fields *f, int n, char *urltag, newstr *url )
{
	xxx_to_url( f, n, "http://www.ncbi.nlm.nih.gov/pmc/articles", urltag, url );
}
void
arxiv_to_url( fields *f, int n, char *urltag, newstr *url )
{
	xxx_to_url( f, n, "http://arxiv.org/abs", urltag, url );
}

/* Rules for the pattern:
 *   '#' = number
 *   isalpha() = match precisely (matchcase==1) or match regardless of case
 *   	(matchcase==0)
 *   all others must match precisely
 */
static int
string_pattern( char *s, char *pattern, int matchcase )
{
	int patlen, match, i;
	patlen = strlen( pattern );
	if ( strlen( s ) < patlen ) return 0; /* too short */
	for ( i=0; i<patlen; ++i ) {
		match = 0;
		if ( pattern[i]=='#' ) {
			if ( isdigit( (unsigned char)s[i] ) ) match = 1;
		} else if ( !matchcase && isalpha( (unsigned char)pattern[i] ) ) {
			if ( tolower((unsigned char)pattern[i])==tolower((unsigned char)s[i])) match = 1;
		} else {
			if ( pattern[i] == s[i] ) match = 1;
		}
		if ( !match ) return 0;
	}
	return 1;
}

/* science direct is now doing "M3  - doi: DOI: 10.xxxx/xxxxx" */
int
is_doi( char *s )
{
	if ( string_pattern( s, "##.####/", 0 ) ) return 0;
	if ( string_pattern( s, "doi:##.####/", 0 ) ) return 4;
	if ( string_pattern( s, "doi: ##.####/", 0 ) ) return 5;
	if ( string_pattern( s, "doi: DOI: ##.####/", 0 ) ) return 10;
	return -1;
}

/* determine if string has the header of a Universal Resource Identifier
 *
 * returns -1, if not true
 * returns offset that skips over the URI scheme, if true
 */
int
is_uri_remote_scheme( char *p )
{
	char *scheme[]   = { "http:", "https:", "ftp:", "git:", "gopher:" };
	int  schemelen[] = { 5,       6,         4,       4,     7 };
        int i, nschemes = sizeof( scheme ) / sizeof( scheme[0] );
        for ( i=0; i<nschemes; ++i ) {
                if ( !strncasecmp( p, scheme[i], schemelen[i] ) ) return schemelen[i];
        }
        return -1;
}

int
is_reference_database( char *p )
{
	char *scheme[]   = { "arXiv:", "pubmed:", "medline:", "isi:" };
	int  schemelen[] = { 6,        7,         8,          4 };
        int i, nschemes = sizeof( scheme ) / sizeof( scheme[0] );
        for ( i=0; i<nschemes; ++i ) {
                if ( !strncasecmp( p, scheme[i], schemelen[i] ) ) return schemelen[i];
        }
        return -1;
}

/* many fields have been abused to embed URLs, DOIs, etc. */
int
is_embedded_link( char *s )
{
	if ( is_uri_remote_scheme( s ) != -1 ) return 1;
	if ( is_reference_database( s ) != -1 ) return 1;
	if ( is_doi( s ) !=-1 ) return 1;
	return 0;
}
