/*
 * endxmlin.c
 *
 * Copyright (c) Chris Putnam 2006-2016
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
#include "bibformats.h"

typedef struct {
	char *attrib;
	char *internal;
} attribs;

extern variants end_all[];
extern int end_nall;

static int endxmlin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset );
static int endxmlin_processf( fields *endin, char *p, char *filename, long nref, param *pm );
extern int endin_typef( fields *endin, char *filename, int nrefs, param *p );
extern int endin_convertf( fields *endin, fields *info, int reftype, param *p );
extern int endin_cleanf( bibl *bin, param *p );


/*****************************************************
 PUBLIC: void endxmlin_initparams()
*****************************************************/
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

/*****************************************************
 PUBLIC: int endxmlin_readf()
*****************************************************/

static int
xml_readmore( FILE *fp, char *buf, int bufsize, int *bufpos )
{
	if ( !feof( fp ) && fgets( buf, bufsize, fp ) ) return 0;
	return 1;
}

static int
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

/*****************************************************
 PUBLIC: int endxmlin_processf()
*****************************************************/

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
static int
endxmlin_datar( xml *node, newstr *s )
{
	int status;
	if ( node->value && node->value->len ) {
		newstr_strcat( s, node->value->data );
		if ( newstr_memerr( s ) ) return BIBL_ERR_MEMERR;
	}
	if ( node->down && xml_tagexact( node->down, "style" ) ) {
		status = endxmlin_datar( node->down, s );
		if ( status!=BIBL_OK ) return status;
	}
	if ( xml_tagexact( node, "style" ) && node->next ) {
		status = endxmlin_datar( node->next, s );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

static int
endxmlin_data( xml *node, char *inttag, fields *info, int level )
{
	int status;
	newstr s;
	newstr_init( &s );
	status = endxmlin_datar( node, &s );
	if ( status!=BIBL_OK ) return status;
	if ( s.len ) {
		status = fields_add( info, inttag, s.data, level );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	newstr_free( &s );
	return BIBL_OK;
}

/* <titles>
 *    <title>
 *       <style>ACTUAL TITLE HERE</style><style>MORE TITLE</style>
 *    </title>
 * </titles>
 */
static int
endxmlin_titles( xml *node, fields *info )
{
	attribs a[] = {
		{ "title", "%T" },
		{ "secondary-title", "%B" },
		{ "tertiary-title", "%S" },
		{ "alt-title", "%!" },
		{ "short-title", "SHORTTITLE" },
	};
	int i, status, n = sizeof( a ) / sizeof ( a[0] );
	newstr title;
	newstr_init( &title );
	for ( i=0; i<n; ++i ) {
		if ( xml_tagexact( node, a[i].attrib ) && node->down ) {
			newstr_empty( &title );
			status = endxmlin_datar( node, &title );
			if ( status!=BIBL_OK ) return BIBL_ERR_MEMERR;
			newstr_trimstartingws( &title );
			newstr_trimendingws( &title );
			status = fields_add( info, a[i].internal, title.data, 0);
			if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		}
	}
	if ( node->next ) {
		status = endxmlin_titles( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	newstr_free( &title );
	return BIBL_OK;
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
static int
endxmlin_contributor( xml *node, fields *info, char *int_tag, int level )
{
	int status;
	status = endxmlin_data( node, int_tag, info, level );
	if ( status!=BIBL_OK ) return status;
	if ( node->next ) {
		status = endxmlin_contributor( node->next, info, int_tag, level );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

static int
endxmlin_contributors( xml *node, fields *info )
{
	attribs a[] = {
		{ "authors", "%A" },
		{ "secondary-authors", "%E" },
		{ "tertiary-authors", "%Y" },
		{ "subsidiary-authors", "%?" },
		{ "translated-authors", "%?" },
	};
	int i, status, n = sizeof( a ) / sizeof ( a[0] );
	for ( i=0; i<n; ++i ) {
		if ( xml_tagexact( node, a[i].attrib ) && node->down ) {
			status = endxmlin_contributor( node->down, info, a[i].internal, 0 );
			if ( status!=BIBL_OK ) return status;
		}
	}
	if ( node->next ) {
		status = endxmlin_contributors( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

static int
endxmlin_keyword( xml *node, fields *info )
{
	int status;
	if ( xml_tagexact( node, "keyword" ) ) {
		status = endxmlin_data( node, "%K", info, 0 );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) {
		status = endxmlin_keyword( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

static int
endxmlin_keywords( xml *node, fields *info )
{
	if ( node->down && xml_tagexact( node->down, "keyword" ) )
		return endxmlin_keyword( node->down, info );
	return BIBL_OK;
}

/*
 *<electronic-resource-num><style face="normal" font="default" 
 * size="100%">10.1007/BF00356334</style></electronic-resource-num>
 */
static int
endxmlin_ern( xml *node, fields *info )
{
	if ( xml_tagexact( node, "electronic-resource-num" ) )
		return endxmlin_data( node, "DOI", info, 0 );
	return BIBL_OK;
}

static int
endxmlin_language( xml *node, fields *info )
{
	if ( xml_tagexact( node, "language" ) )
		return endxmlin_data( node, "%G", info, 0 );
	return BIBL_OK;
}

/*
 * <urls>
 *    <pdf-urls>
 *           <url>internal-pdf://Zukin_1995_The_Cultures_of_Cities-0000551425/Zukin_1995_The_Cultures_of_Cities.pdf</url>
 *    </pdf-urls>
 * </urls>
 */
static int
endxmlin_fileattach( xml *node, fields *info )
{
	int status;
	if ( xml_tagexact( node, "url" ) ) {
		status = endxmlin_data( node, "FILEATTACH", info, 0 );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->down ) {
		status = endxmlin_fileattach( node->down, info );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) {
		status = endxmlin_fileattach( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

static int
endxmlin_urls( xml *node, fields *info )
{
	int status;
	if ( xml_tagexact( node, "pdf-urls" ) && node->down ) {
		status = endxmlin_fileattach( node->down, info );
		if ( status!=BIBL_OK ) return status;
	} else if ( xml_tagexact( node, "url" ) ) {
		status = endxmlin_data( node, "%U", info, 0 );
		if ( status!=BIBL_OK ) return status;
	} else {
		if ( node->down ) {
			if ( xml_tagexact( node->down, "related-urls" ) ||
			     xml_tagexact( node->down, "pdf-urls" ) ||
			     xml_tagexact( node->down, "url" ) ) {
				status = endxmlin_urls( node->down, info );
				if ( status!=BIBL_OK ) return status;
			}
		}
	}
	if ( node->next ) {
		status = endxmlin_urls( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

static int
endxmlin_pubdates( xml *node, fields *info )
{
	if ( xml_tagexact( node, "date" ) )
		return endxmlin_data( node, "%8", info, 0 );
	else {
		if ( node->down && xml_tagexact( node->down, "date" ) )
			return endxmlin_pubdates( node->down, info );
	}
	return BIBL_OK;
}

static int
endxmlin_dates( xml *node, fields *info )
{
	int status;
	if ( xml_tagexact( node, "year" ) ) {
		status = endxmlin_data( node, "%D", info, 0 );
		if ( status!=BIBL_OK ) return status;
	} else {
		if ( node->down ) {
			if ( xml_tagexact( node->down, "year" ) ) {
				status = endxmlin_dates( node->down, info );
				if ( status!=BIBL_OK ) return status;
			}
			if ( xml_tagexact( node->down, "pub-dates" ) ) {
				status = endxmlin_pubdates( node->down, info );
				if ( status!=BIBL_OK );
			}
		}
	}
	if ( node->next ) {
		status = endxmlin_dates( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

/*
 * <ref-type name="Journal Article">17</ref-type>
 */
static int
endxmlin_reftype( xml *node, fields *info )
{
	int status;
	newstr *s;
	s = xml_getattrib( node, "name" );
	if ( s && s->len ) {
		status = fields_add( info, "%0", s->data, 0 );
		newstr_free( s );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	return BIBL_OK;
}

static int
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
	int i, status, n = sizeof ( a ) / sizeof( a[0] );
	if ( xml_tagexact( node, "DATABASE" ) ) {
	} else if ( xml_tagexact( node, "SOURCE-APP" ) ) {
	} else if ( xml_tagexact( node, "REC-NUMBER" ) ) {
	} else if ( xml_tagexact( node, "ref-type" ) ) {
		status = endxmlin_reftype( node, info );
		if ( status!=BIBL_OK ) return status;
	} else if ( xml_tagexact( node, "contributors" ) ) {
		if ( node->down ) {
			status = endxmlin_contributors( node->down, info );
			if ( status!=BIBL_OK ) return status;
		}
	} else if ( xml_tagexact( node, "titles" ) ) {
		if ( node->down ) endxmlin_titles( node->down, info );
	} else if ( xml_tagexact( node, "keywords" ) ) {
		status = endxmlin_keywords( node, info );
		if ( status!=BIBL_OK ) return status;
	} else if ( xml_tagexact( node, "urls" ) ) {
		status = endxmlin_urls( node, info );
		if ( status!=BIBL_OK ) return status;
	} else if ( xml_tagexact( node, "electronic-resource-num" ) ) {
		status = endxmlin_ern( node, info );
		if ( status!=BIBL_OK ) return status;
	} else if ( xml_tagexact( node, "dates" ) ) {
		status = endxmlin_dates( node, info );
		if ( status!=BIBL_OK ) return status;
	} else if ( xml_tagexact( node, "language" ) ) {
		status = endxmlin_language( node, info );
		if ( status!=BIBL_OK ) return status;
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
			if ( xml_tagexact( node, a[i].attrib ) ) {
				status = endxmlin_data( node, a[i].internal, info, 0 );
				if ( status!=BIBL_OK ) return status;
			}
		}
	}
	if ( node->next ) {
		status = endxmlin_record( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

static int
endxmlin_assembleref( xml *node, fields *info )
{
	int status;
	if ( node->tag->len==0 ) {
		if ( node->down )
			return endxmlin_assembleref( node->down, info );
	} else if ( xml_tagexact( node, "RECORD" ) ) {
		if ( node->down ) {
			status = endxmlin_record( node->down, info );
			if ( status!=BIBL_OK ) return status;
		}
	}
	return BIBL_OK;
}

/* endxmlin_processf first operates by converting to endnote input
 * the endnote->mods conversion happens in convertf.
 *
 * this is necessary as the xml format is as nasty and as overloaded
 * as the tags used in the Refer format output
 */
static int
endxmlin_processf( fields *fin, char *data, char *filename, long nref, param *pm )
{
	int status;
	xml top;

	xml_init( &top );
	xml_tree( data, &top );
	status = endxmlin_assembleref( &top, fin );
	xml_free( &top );

	if ( status==BIBL_OK ) return 1;
	return 0;
}
