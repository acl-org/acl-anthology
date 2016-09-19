/*
 * wordin.c
 *
 * Copyright (c) Chris Putnam 2010-2016
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
#include "bibformats.h"

static int wordin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset );
static int wordin_processf( fields *wordin, char *data, char *filename, long nref, param *p );


/*****************************************************
 PUBLIC: void wordin_initparams()
*****************************************************/

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

/*****************************************************
 PUBLIC: int wordin_readf()
*****************************************************/

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

static int
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

/*****************************************************
 PUBLIC: int wordin_processf()
*****************************************************/

typedef struct xml_convert {
	char *in;       /* The input tag */
	char *a, *aval; /* The attribute="attribute_value" pair, if nec. */
	char *out;      /* The output tag */
	int level;
} xml_convert;

/* wordin_person_last()
 *
 * From an xml list, extract the value from the first entry
 * of <b:Last>xxxx</b:Last> and copy into name
 *
 * Additional <b:Last>yyyyy</b:Last> will be ignored.
 *
 * Returns BIBL_ERR_MEMERR on memory error, BIBL_OK otherwise.
 */
static int
wordin_person_last( xml *node, newstr *name )
{
	while ( node && !xml_tagexact( node, "b:Last" ) )
		node = node->next;
	if ( node && node->value->len ) {
		newstr_strcpy( name, node->value->data );
		if ( newstr_memerr( name ) ) return BIBL_ERR_MEMERR;
	}
	return BIBL_OK;
}

/* wordin_person_first()
 *
 * From an xml list, extract the value of any
 * <b:First>xxxx</b:First> and append "|xxxx" to name.
 *
 * Returns BIBL_ERR_MEMERR on memory error, BIBL_OK otherwise
 */
static int
wordin_person_first( xml *node, newstr *name )
{
	for ( ; node; node=node->next ) {
		if ( !xml_tagexact( node, "b:First" ) ) continue;
		if ( node->value->len ) {
			if ( name->len ) newstr_addchar( name, '|' );
			newstr_strcat( name, node->value->data );
			if ( newstr_memerr( name ) ) return BIBL_ERR_MEMERR;
		}
	}
	return BIBL_OK;
}

static int
wordin_person( xml *node, fields *info, char *type )
{
	int status, ret = BIBL_OK;
	newstr name;

	newstr_init( &name );

	status = wordin_person_last( node, &name );
	if ( status!=BIBL_OK ) {
		ret = status;
		goto out;
	}

	status = wordin_person_first( node, &name );
	if ( status!=BIBL_OK ) {
		ret = status;
		goto out;
	}

	status = fields_add( info, type, name.data, 0 );
	if ( status != FIELDS_OK ) ret = BIBL_ERR_MEMERR;
out:
	newstr_free( &name );
	return ret;
}

static int
wordin_people( xml *node, fields *info, char *type )
{
	int ret = BIBL_OK;
	if ( xml_tagexact( node, "b:Author" ) && node->down ) {
		ret = wordin_people( node->down, info, type );
	} else if ( xml_tagexact( node, "b:NameList" ) && node->down ) {
		ret = wordin_people( node->down, info, type );
	} else if ( xml_tagexact( node, "b:Person" ) ) {
		if ( node->down ) ret = wordin_person( node->down, info, type );
		if ( ret!=BIBL_OK ) return ret;
		if ( node->next ) ret = wordin_people( node->next, info, type );
	}
	return ret;
}

static int
wordin_pages( xml *node, fields *info )
{
	int i, status, ret = BIBL_OK;
	newstr sp, ep;
	char *p;

	newstrs_init( &sp, &ep, NULL );

	p = xml_data( node );
	while ( *p && *p!='-' )
		newstr_addchar( &sp, *p++ );
	if ( newstr_memerr( &sp ) ) {
		ret = BIBL_ERR_MEMERR;
		goto out;
	}

	if ( *p=='-' ) p++;
	while ( *p )
		newstr_addchar( &ep, *p++ );
	if ( newstr_memerr( &ep ) ) {
		ret = BIBL_ERR_MEMERR;
		goto out;
	}

	if ( sp.len ) {
		status = fields_add( info, "PAGES:START", sp.data, 1 );
		if ( status!=FIELDS_OK ) {
			ret = BIBL_ERR_MEMERR;
			goto out;
		}
	}

	if ( ep.len ) {
		if ( sp.len > ep.len ) {
			for ( i=sp.len-ep.len; i<sp.len; ++i )
				sp.data[i] = ep.data[i-sp.len+ep.len];
			status = fields_add( info, "PAGES:STOP", sp.data, 1 );
		} else
			status = fields_add( info, "PAGES:STOP", ep.data, 1 );
		if ( status!=FIELDS_OK ) {
			ret = BIBL_ERR_MEMERR;
			goto out;
		}
	}

out:
	newstrs_free( &sp, &ep, NULL );
	return ret;
}

static int
wordin_reference( xml *node, fields *info )
{
	int status, ret = BIBL_OK;
	if ( xml_hasdata( node ) ) {
		if ( xml_tagexact( node, "b:Tag" ) ) {
			status = fields_add( info, "REFNUM", xml_data( node ), 0 );
			if ( status!=FIELDS_OK ) ret = BIBL_ERR_MEMERR;
		} else if ( xml_tagexact( node, "b:SourceType" ) ) {
		} else if ( xml_tagexact( node, "b:City" ) ) {
			status = fields_add( info, "ADDRESS", xml_data( node ), 0 );
			if ( status!=FIELDS_OK ) ret = BIBL_ERR_MEMERR;
		} else if ( xml_tagexact( node, "b:Publisher" ) ) {
			status = fields_add( info, "PUBLISHER", xml_data( node ), 0 );
			if ( status!=FIELDS_OK ) ret = BIBL_ERR_MEMERR;
		} else if ( xml_tagexact( node, "b:Title" ) ) {
			status = fields_add( info, "TITLE", xml_data( node ), 0 );
			if ( status!=FIELDS_OK ) ret = BIBL_ERR_MEMERR;
		} else if ( xml_tagexact( node, "b:JournalName" ) ) {
			status = fields_add( info, "TITLE", xml_data( node ), 1 );
			if ( status!=FIELDS_OK ) ret = BIBL_ERR_MEMERR;
		} else if ( xml_tagexact( node, "b:Volume" ) ) {
			status = fields_add( info, "VOLUME", xml_data( node ), 1 );
			if ( status!=FIELDS_OK ) ret = BIBL_ERR_MEMERR;
		} else if ( xml_tagexact( node, "b:Comments" ) ) {
			status = fields_add( info, "NOTES", xml_data( node ), 0 );
			if ( status!=FIELDS_OK ) ret = BIBL_ERR_MEMERR;
		} else if ( xml_tagexact( node, "b:Pages" ) ) {
			ret = wordin_pages( node, info );
		} else if ( xml_tagexact( node, "b:Author" ) && node->down ) {
			ret = wordin_people( node->down, info, "AUTHOR" );
		} else if ( xml_tagexact( node, "b:Editor" ) && node->down ) {
			ret = wordin_people( node->down, info, "EDITOR" );
		}
	}
	if ( ret==BIBL_OK && node->next ) wordin_reference( node->next, info );
	return ret;
}

static int
wordin_assembleref( xml *node, fields *info )
{
	int ret = BIBL_OK;
	if ( xml_tagexact( node, "b:Source" ) ) {
		if ( node->down ) ret = wordin_reference( node->down, info );
	} else if ( node->tag->len==0 && node->down ) {
		ret = wordin_assembleref( node->down, info );
	}
	return ret;
}

static int
wordin_processf( fields *wordin, char *data, char *filename, long nref, param *p )
{
	int status, ret = 1;
	xml top;

	xml_init( &top );
	xml_tree( data, &top );
	status = wordin_assembleref( &top, wordin );
	xml_free( &top );

	if ( status==BIBL_ERR_MEMERR ) ret = 0;
	return ret;
}
