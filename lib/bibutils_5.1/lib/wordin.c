/*
 * wordin.c
 *
 * Copyright (c) Chris Putnam 2010-2013
 *
 * Source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include "is_ws.h"
#include "newstr.h"
#include "newstr_conv.h"
#include "fields.h"
#include "xml.h"
#include "xml_encoding.h"
#include "wordin.h"

void
wordin_initparams( param *p, const char *progname )
{
	p->readformat       = BIBL_WORDIN;
	p->charsetin        = BIBL_CHARSET_DEFAULT;
	p->charsetin_src    = BIBL_SRC_DEFAULT;
	p->latexin          = 0;
	p->xmlin            = 1;
	p->utf8in           = 1;
	p->nosplittitle     = 0;
	p->verbose          = 0;
	p->addcount         = 0;
	p->output_raw       = BIBL_RAW_WITHMAKEREFID |
	                      BIBL_RAW_WITHCHARCONVERT;

	p->readf    = wordin_readf;
	p->processf = wordin_processf;
	p->cleanf   = NULL;
	p->typef    = NULL;
	p->convertf = NULL;
	p->all      = NULL;
	p->nall     = 0;

	list_init( &(p->asis) );
	list_init( &(p->corps) );

	if ( !progname ) p->progname = NULL;
	else p->progname = strdup( progname );
}

static char *
wordin_findstartwrapper( char *buf, int *ntype )
{
	char *startptr = xml_findstart( buf, "b:Source" );
	return startptr;
}

static char *
wordin_findendwrapper( char *buf, int ntype )
{
	char *endptr = xml_findend( buf, "b:Source" );
	return endptr;
}

int
wordin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset )
{
	newstr tmp;
	char *startptr = NULL, *endptr;
	int haveref = 0, inref = 0, file_charset = CHARSET_UNKNOWN, m, type = 1;
	newstr_init( &tmp );
	while ( !haveref && newstr_fget( fp, buf, bufsize, bufpos, line ) ) {
		if ( line->data ) {
			m = xml_getencoding( line );
			if ( m!=CHARSET_UNKNOWN ) file_charset = m;
		}
		if ( line->data ) {
			startptr = wordin_findstartwrapper( line->data, &type );
		}
		if ( startptr || inref ) {
			if ( inref ) newstr_strcat( &tmp, line->data );
			else {
				newstr_strcat( &tmp, startptr );
				inref = 1;
			}
			endptr = wordin_findendwrapper( tmp.data, type );
			if ( endptr ) {
				newstr_segcpy( reference, tmp.data, endptr );
				haveref = 1;
			}
		}
	}
	newstr_free( &tmp );
	*fcharset = file_charset;
	return haveref;
}

static inline int
xml_hasdata( xml *node )
{
	if ( node && node->value && node->value->data ) return 1;
	return 0;
}

static inline char *
xml_data( xml *node )
{
	return node->value->data;
}

static inline int
xml_tagwithdata( xml *node, char *tag )
{
	if ( !xml_hasdata( node ) ) return 0;
	return xml_tagexact( node, tag );
}

typedef struct xml_convert {
	char *in;       /* The input tag */
	char *a, *aval; /* The attribute="attribute_value" pair, if nec. */
	char *out;      /* The output tag */
	int level;
} xml_convert;

static void
wordin_person( xml *node, fields *info, char *type )
{
	xml *last, *first;
	newstr name;

	newstr_init( &name );

	last = node;
	while ( last && !xml_tagexact( last, "b:Last" ) )
		last = last->next;
	if ( last ) newstr_strcpy( &name, last->value->data );

	first = node;
	while ( first ) {
		if ( xml_tagexact( first, "b:First" ) ) {
			if ( name.len ) newstr_addchar( &name, '|' );
			newstr_strcat( &name, first->value->data );
		}
		first = first->next;
	}

	fields_add( info, type, name.data, 0 );

	newstr_free( &name );
}

static void
wordin_people( xml *node, fields *info, char *type )
{
	if ( xml_tagexact( node, "b:Author" ) && node->down ) {
		wordin_people( node->down, info, type );
	} else if ( xml_tagexact( node, "b:NameList" ) && node->down ) {
		wordin_people( node->down, info, type );
	} else if ( xml_tagexact( node, "b:Person" ) ) {
		if ( node->down ) wordin_person( node->down, info, type );
		if ( node->next ) wordin_people( node->next, info, type );
	}
}

static void
wordin_pages( xml *node, fields *info )
{
	newstr sp, ep;
	char *p;
	int i;
	newstrs_init( &sp, &ep, NULL );
/*
	newstr_init( &sp );
	newstr_init( &ep );
*/
	p = xml_data( node );
	while ( *p && *p!='-' )
		newstr_addchar( &sp, *p++ );
	if ( *p=='-' ) p++;
	while ( *p )
		newstr_addchar( &ep, *p++ );
	if ( sp.len ) fields_add( info, "PAGESTART", sp.data, 1 );
	if ( ep.len ) {
		if ( sp.len > ep.len ) {
			for ( i=sp.len-ep.len; i<sp.len; ++i )
				sp.data[i] = ep.data[i-sp.len+ep.len];
			fields_add( info, "PAGEEND", sp.data, 1 );
		} else
			fields_add( info, "PAGEEND", ep.data, 1 );
	}
	newstrs_free( &sp, &ep, NULL );
/*
	newstr_free( &sp );
	newstr_free( &ep );
*/
}

static void
wordin_reference( xml *node, fields *info )
{
	if ( xml_hasdata( node ) ) {
		if ( xml_tagexact( node, "b:Tag" ) ) {
			fields_add( info, "REFNUM", xml_data( node ), 0 );
		} else if ( xml_tagexact( node, "b:SourceType" ) ) {
		} else if ( xml_tagexact( node, "b:City" ) ) {
			fields_add( info, "ADDRESS", xml_data( node ), 0 );
		} else if ( xml_tagexact( node, "b:Publisher" ) ) {
			fields_add( info, "PUBLISHER", xml_data( node ), 0 );
		} else if ( xml_tagexact( node, "b:Title" ) ) {
			fields_add( info, "TITLE", xml_data( node ), 0 );
		} else if ( xml_tagexact( node, "b:JournalName" ) ) {
			fields_add( info, "TITLE", xml_data( node ), 1 );
		} else if ( xml_tagexact( node, "b:Volume" ) ) {
			fields_add( info, "VOLUME", xml_data( node ), 1 );
		} else if ( xml_tagexact( node, "b:Comments" ) ) {
			fields_add( info, "NOTES", xml_data( node ), 0 );
		} else if ( xml_tagexact( node, "b:Pages" ) ) {
			wordin_pages( node, info );
		} else if ( xml_tagexact( node, "b:Author" ) && node->down ) {
			wordin_people( node->down, info, "AUTHOR" );
		} else if ( xml_tagexact( node, "b:Editor" ) && node->down ) {
			wordin_people( node->down, info, "EDITOR" );
		}
	}
	if ( node->next ) wordin_reference( node->next, info );
}

static void
wordin_assembleref( xml *node, fields *info )
{
	if ( xml_tagexact( node, "b:Source" ) ) {
		if ( node->down ) wordin_reference( node->down, info );
	} else if ( node->tag->len==0 && node->down ) {
		wordin_assembleref( node->down, info );
	}
}

int
wordin_processf( fields *wordin, char *data, char *filename, long nref )
{
	xml top;
	xml_init( &top );
	xml_tree( data, &top );
	wordin_assembleref( &top, wordin );
	xml_free( &top );
	return 1;
}
