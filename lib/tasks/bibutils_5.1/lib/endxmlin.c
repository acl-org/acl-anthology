/*
 * endxmlin.c
 *
 * Copyright (c) Chris Putnam 2006-2013
 *
 * Program and source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include "newstr.h"
#include "newstr_conv.h"
#include "fields.h"
#include "name.h"
#include "xml.h"
#include "xml_encoding.h"
#include "reftypes.h"
#include "endxmlin.h"
#include "endin.h"

typedef struct {
	char *attrib;
	char *internal;
} attribs;

void
endxmlin_initparams( param *p, const char *progname )
{
	p->readformat       = BIBL_ENDNOTEXMLIN;
	p->charsetin        = BIBL_CHARSET_DEFAULT;
	p->charsetin_src    = BIBL_SRC_DEFAULT;
	p->latexin          = 0;
	p->xmlin            = 1;
	p->utf8in           = 1;
	p->nosplittitle     = 0;
	p->verbose          = 0;
	p->addcount         = 0;
	p->output_raw       = 0;

	p->readf    = endxmlin_readf;
	p->processf = endxmlin_processf;
	p->cleanf   = NULL;
	p->typef    = endin_typef;
	p->convertf = endin_convertf;
	p->all      = end_all;
	p->nall     = end_nall;

	list_init( &(p->asis) );
	list_init( &(p->corps) );

	if ( !progname ) p->progname = NULL;
	else p->progname = strdup( progname );
}

static int
xml_readmore( FILE *fp, char *buf, int bufsize, int *bufpos )
{
	if ( !feof( fp ) && fgets( buf, bufsize, fp ) ) return 0;
	return 1;
}

int
endxmlin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line,
	newstr *reference, int *fcharset )
{
	newstr tmp;
	char *startptr = NULL, *endptr = NULL;
	int haveref = 0, inref = 0, done = 0, file_charset = CHARSET_UNKNOWN, m;
	newstr_init( &tmp );
	while ( !haveref && !done ) {
		if ( line->data ) {
			if ( !inref ) {
				startptr = xml_findstart( line->data, "RECORD" );
				if ( startptr ) inref = 1;
			} else
				endptr = xml_findend( line->data, "RECORD" );
		}

		/* If no <record> tag, we can trim up to last 8 bytes */
		/* Emptying string can lose fragments of <record> tag */
		if ( !startptr ) {
			if ( line->len > 8 ) {
				int n = 8;
				char *p = &(line->data[line->len-1]);
				while ( *p && n ) { p--; n--; }
				newstr_segdel( line, line->data, p ); 
			}
		}

		if ( !startptr || !endptr ) {
			done = xml_readmore( fp, buf, bufsize, bufpos );
			newstr_strcat( line, buf );
		} else {
			/* we can reallocate in the newstr_strcat, so re-find */
			startptr = xml_findstart( line->data, "RECORD" );
			endptr = xml_findend( line->data, "RECORD" );
			newstr_segcpy( reference, startptr, endptr );
			/* clear out information in line */
			newstr_strcpy( &tmp, endptr );
			newstr_newstrcpy( line, &tmp );
			haveref = 1;
		}
		if ( line->data ) {
			m = xml_getencoding( line );
			if ( m!=CHARSET_UNKNOWN ) file_charset = m;
		}
	}
	newstr_free( &tmp );
	*fcharset = file_charset;
	return haveref;
}

/*
 * add data to fields
 */

/*
 * handle fields with (potentially) several style pieces
 *
 *   <datatype>
 *          <style>aaaaa</style>
 *   </datatype>
 *
 *   <datatype>aaaaaa</datatype>
 *
 *   <datatype>
 *          <style>aaa</style><style>aaaa</style>
 *   </datatype>
 */
void
endxmlin_datar( xml *node, newstr *s )
{
	if ( node->value && node->value->len )
		newstr_strcat( s, node->value->data );
	if ( node->down && xml_tagexact( node->down, "style" ) )
		endxmlin_datar( node->down, s );
	if ( xml_tagexact( node, "style" ) && node->next )
		endxmlin_datar( node->next, s );
}

void
endxmlin_data( xml *node, char *inttag, fields *info, int level )
{
	newstr s;
	newstr_init( &s );
	endxmlin_datar( node, &s );
	if ( s.len )
		fields_add( info, inttag, s.data, level );
	newstr_free( &s );
}

/* <titles>
 *    <title>
 *       <style>ACTUAL TITLE HERE</style><style>MORE TITLE</style>
 *    </title>
 * </titles>
 */
void
endxmlin_titles( xml *node, fields *info )
{
	attribs a[] = {
		{ "title", "%T" },
		{ "secondary-title", "%B" },
		{ "tertiary-title", "%S" },
		{ "alt-title", "%!" },
		{ "short-title", "SHORTTITLE" },
	};
	int i, n = sizeof( a ) / sizeof ( a[0] );
	newstr title;
	newstr_init( &title );
	for ( i=0; i<n; ++i ) {
		if ( xml_tagexact( node, a[i].attrib ) && node->down ) {
			newstr_empty( &title );
			endxmlin_datar( node, &title );
			newstr_trimstartingws( &title );
			newstr_trimendingws( &title );
			fields_add( info, a[i].internal, title.data, 0);
		}
	}
	if ( node->next ) endxmlin_titles( node->next, info );
	newstr_free( &title );
}

/* <contributors>
 *    <secondary-authors>
 *        <author>
 *             <style>ACTUAL AUTHORS HERE</style>
 *        </author>
 *    </secondary-authors>
 * </contributors>
 */
/* <!ATTLIST author
 *      corp-name CDATA #IMPLIED
 *      first-name CDATA #IMPLIED
 *      initials CDATA #IMPLIED
 *      last-name CDATA #IMPLIED
 *      middle-initial CDATA #IMPLIED
 *      role CDATA #IMPLIED
 *      salutation CDATA #IMPLIED
 *      suffix CDATA #IMPLIED
 *      title CDATA #IMPLIED
 * >
 *
 */
void
endxmlin_contributor( xml *node, fields *info, char *int_tag, int level )
{
	endxmlin_data( node, int_tag, info, level );
	if ( node->next )
		endxmlin_contributor( node->next, info, int_tag, level );
}

static void
endxmlin_contributors( xml *node, fields *info )
{
	attribs contrib[] = {
		{ "authors", "%A" },
		{ "secondary-authors", "%E" },
		{ "tertiary-authors", "%Y" },
		{ "subsidiary-authors", "%?" },
		{ "translated-authors", "%?" },
	};
	int i, n = sizeof( contrib ) / sizeof ( contrib[0] );
	for ( i=0; i<n; ++i ) {
		if ( xml_tagexact( node, contrib[i].attrib ) && node->down )
			endxmlin_contributor( node->down, info, contrib[i].internal, 0 );
	}
	if ( node->next )
		endxmlin_contributors( node->next, info );
}

static void
endxmlin_keyword( xml *node, fields *info )
{
	if ( xml_tagexact( node, "keyword" ) )
		endxmlin_data( node, "%K", info, 0 );
	if ( node->next )
		endxmlin_keyword( node->next, info );
}

static void
endxmlin_keywords( xml *node, fields *info )
{
	if ( node->down && xml_tagexact( node->down, "keyword" ) )
		endxmlin_keyword( node->down, info );
}

/*
 *<electronic-resource-num><style face="normal" font="default" 
 * size="100%">10.1007/BF00356334</style></electronic-resource-num>
 */
static void
endxmlin_ern( xml *node, fields *info )
{
	if ( xml_tagexact( node, "electronic-resource-num" ) )
		endxmlin_data( node, "DOI", info, 0 );
}

static void
endxmlin_language( xml *node, fields *info )
{
	if ( xml_tagexact( node, "language" ) )
		endxmlin_data( node, "%G", info, 0 );
}

/*
 * <urls>
 *    <pdf-urls>
 *           <url>internal-pdf://Zukin_1995_The_Cultures_of_Cities-0000551425/Zukin_1995_The_Cultures_of_Cities.pdf</url>
 *    </pdf-urls>
 * </urls>
 */
static void
endxmlin_fileattach( xml *node, fields *info )
{
	if ( xml_tagexact( node, "url" ) )
		endxmlin_data( node, "FILEATTACH", info, 0 );
	if ( node->down ) endxmlin_fileattach( node->down, info );
	if ( node->next ) endxmlin_fileattach( node->next, info );
}

static void
endxmlin_urls( xml *node, fields *info )
{
	if ( xml_tagexact( node, "pdf-urls" ) && node->down )
		endxmlin_fileattach( node->down, info );
	else if ( xml_tagexact( node, "url" ) )
		endxmlin_data( node, "%U", info, 0 );
	else {
		if ( node->down ) {
			if ( xml_tagexact( node->down, "related-urls" ) ||
			     xml_tagexact( node->down, "pdf-urls" ) ||
			     xml_tagexact( node->down, "url" ) )
				endxmlin_urls( node->down, info );
		}
	}
	if ( node->next )
		endxmlin_urls( node->next, info );
}

static void
endxmlin_pubdates( xml *node, fields *info )
{
	if ( xml_tagexact( node, "date" ) )
		endxmlin_data( node, "%8", info, 0 );
	else {
		if ( node->down && xml_tagexact( node->down, "date" ) )
			endxmlin_pubdates( node->down, info );
	}
}

static void
endxmlin_dates( xml *node, fields *info )
{
	if ( xml_tagexact( node, "year" ) )
		endxmlin_data( node, "%D", info, 0 );
	else {
		if ( node->down ) {
			if ( xml_tagexact( node->down, "year" ) )
				endxmlin_dates( node->down, info );
			if ( xml_tagexact( node->down, "pub-dates" ) )
				endxmlin_pubdates( node->down, info );
		}
	}
	if ( node->next )
		endxmlin_dates( node->next, info );
}

/*
 * <ref-type name="Journal Article">17</ref-type>
 */
static void
endxmlin_reftype( xml *node, fields *info )
{
	newstr *s;
	s = xml_getattrib( node, "name" );
	if ( s && s->dim ) {
		fields_add( info, "%0", s->data, 0 );
		newstr_free( s );
	}
}

static void
endxmlin_record( xml *node, fields *info )
{
	attribs a[] = {
		{ "volume", "%V" },
		{ "num-vol", "%6" },
		{ "pages",  "%P" },
		{ "number", "%N" },
		{ "issue",  "%N" },
		{ "label",  "%F" },
		{ "auth-address", "%C" },
		{ "auth-affiliation", "%C" },
		{ "pub-location", "%C" },
		{ "publisher", "%I" },
		{ "abstract", "%X" },
		{ "edition", "%7" },
		{ "reprint-edition", "%)" },
		{ "section", "%&" },
		{ "accession-num", "%M" },
		{ "call-num", "%L" },
		{ "isbn", "%@" },
		{ "notes", "%O" },
		{ "custom1", "%1" },
		{ "custom2", "%2" },
		{ "custom3", "%3" },
		{ "custom4", "%4" },
		{ "custom5", "%#" },
		{ "custom6", "%$" },
	};
	int i, n = sizeof ( a ) / sizeof( a[0] );
	if ( xml_tagexact( node, "DATABASE" ) ) {
/*		endxmlin_database( node, info );*/
	} else if ( xml_tagexact( node, "SOURCE-APP" ) ) {
/*		endxmlin_sourceapp( node, info );*/
	} else if ( xml_tagexact( node, "REC-NUMBER" ) ) {
	} else if ( xml_tagexact( node, "ref-type" ) ) {
		endxmlin_reftype( node, info );
	} else if ( xml_tagexact( node, "contributors" ) ) {
		if ( node->down ) endxmlin_contributors( node->down, info );
	} else if ( xml_tagexact( node, "titles" ) ) {
		if ( node->down ) endxmlin_titles( node->down, info );
	} else if ( xml_tagexact( node, "keywords" ) ) {
		endxmlin_keywords( node, info );
	} else if ( xml_tagexact( node, "urls" ) ) {
		endxmlin_urls( node, info );
	} else if ( xml_tagexact( node, "electronic-resource-num" ) ) {
		endxmlin_ern( node, info );
	} else if ( xml_tagexact( node, "dates" ) ) {
		endxmlin_dates( node, info );
	} else if ( xml_tagexact( node, "language" ) ) {
		endxmlin_language( node, info );
	} else if ( xml_tagexact( node, "periodical" ) ) {
	} else if ( xml_tagexact( node, "secondary-volume" ) ) {
	} else if ( xml_tagexact( node, "secondary-issue" ) ) {
	} else if ( xml_tagexact( node, "reprint-status" ) ) {
	} else if ( xml_tagexact( node, "orig-pub" ) ) {
	} else if ( xml_tagexact( node, "report-id" ) ) {
	} else if ( xml_tagexact( node, "coden" ) ) {
	} else if ( xml_tagexact( node, "caption" ) ) {
	} else if ( xml_tagexact( node, "research-notes" ) ) {
	} else if ( xml_tagexact( node, "work-type" ) ) {
	} else if ( xml_tagexact( node, "reviewed-item" ) ) {
	} else if ( xml_tagexact( node, "availability" ) ) {
	} else if ( xml_tagexact( node, "remote-source" ) ) {
	} else if ( xml_tagexact( node, "meeting-place" ) ) {
	} else if ( xml_tagexact( node, "work-location" ) ) {
	} else if ( xml_tagexact( node, "work-extent" ) ) {
	} else if ( xml_tagexact( node, "pack-method" ) ) {
	} else if ( xml_tagexact( node, "size" ) ) {
	} else if ( xml_tagexact( node, "repro-ratio" ) ) {
	} else if ( xml_tagexact( node, "remote-database-name" ) ) {
	} else if ( xml_tagexact( node, "remote-database-provider" ) ) {
	} else if ( xml_tagexact( node, "access-date" ) ) {
	} else if ( xml_tagexact( node, "modified-data" ) ) {
	} else if ( xml_tagexact( node, "misc1" ) ) {
	} else if ( xml_tagexact( node, "misc2" ) ) {
	} else if ( xml_tagexact( node, "misc3" ) ) {
	} else {
		for ( i=0; i<n; ++i ) {
			if ( xml_tagexact( node, a[i].attrib ) ) 
				endxmlin_data( node, a[i].internal, info, 0 );
		}
	}
	if ( node->next ) endxmlin_record( node->next, info );
}

static void
endxmlin_assembleref( xml *node, fields *info )
{
	if ( node->tag->len==0 ) {
		if ( node->down ) endxmlin_assembleref( node->down, info );
		return;
	} else if ( xml_tagexact( node, "RECORD" ) ) {
		if ( node->down ) endxmlin_record( node->down, info );
	}
}

/* endxmlin_processf first operates by converting to endnote input
 * the endnote->mods conversion happens in convertf.
 *
 * this is necessary as the xml format is as nasty and as overloaded
 * as the tags used in the Refer format output
 */
int
endxmlin_processf( fields *fin, char *data, char *filename, long nref )
{
	xml top;
	xml_init( &top );
	xml_tree( data, &top );
	endxmlin_assembleref( &top, fin );
	xml_free( &top );
	return 1;
}
