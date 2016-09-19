/*
 * copacin.c
 *
 * Copyright (c) Chris Putnam 2004-2016
 *
 * Program and source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "is_ws.h"
#include "newstr.h"
#include "newstr_conv.h"
#include "list.h"
#include "name.h"
#include "fields.h"
#include "reftypes.h"
#include "bibformats.h"
#include "generic.h"

extern variants copac_all[];
extern int copac_nall;

/*****************************************************
 PUBLIC: void copacin_initparams()
*****************************************************/

static int copacin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset );
static int copacin_processf( fields *bibin, char *p, char *filename, long nref, param *pm );
static int copacin_convertf( fields *bibin, fields *info, int reftype, param *pm );

void
copacin_initparams( param *p, const char *progname )
{
	p->readformat       = BIBL_COPACIN;
	p->charsetin        = BIBL_CHARSET_DEFAULT;
	p->charsetin_src    = BIBL_SRC_DEFAULT;
	p->latexin          = 0;
	p->xmlin            = 0;
	p->utf8in           = 0;
	p->nosplittitle     = 0;
	p->verbose          = 0;
	p->addcount         = 0;
	p->output_raw       = 0;

	p->readf    = copacin_readf;
	p->processf = copacin_processf;
	p->cleanf   = NULL;
	p->typef    = NULL;
	p->convertf = copacin_convertf;
	p->all      = copac_all;
	p->nall     = copac_nall;

	list_init( &(p->asis) );
	list_init( &(p->corps) );

	if ( !progname ) p->progname = NULL;
	else p->progname = strdup( progname );
}

/*****************************************************
 PUBLIC: int copacin_readf()
*****************************************************/

/* Endnote-Refer/Copac tag definition:
    character 1 = alphabetic character
    character 2 = alphabetic character
    character 3 = dash
    character 4 = space
*/
static int
copacin_istag( char *buf )
{
	if (! ((buf[0]>='A' && buf[0]<='Z')) || (buf[0]>='a' && buf[0]<='z') )
		return 0;
	if (! ((buf[1]>='A' && buf[1]<='Z')) || (buf[1]>='a' && buf[1]<='z') )
		return 0;
	if (buf[2]!='-' ) return 0;
	if (buf[3]!=' ' ) return 0;
	return 1; 
}
static int
readmore( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line )
{
	if ( line->len ) return 1;
	else return newstr_fget( fp, buf, bufsize, bufpos, line );
}

static int
copacin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset )
{
	int haveref = 0, inref=0;
	char *p;
	*fcharset = CHARSET_UNKNOWN;
	while ( !haveref && readmore( fp, buf, bufsize, bufpos, line ) ) {
		/* blank line separates */
		if ( line->data==NULL ) continue;
		if ( inref && line->len==0 ) haveref=1; 
		p = &(line->data[0]);
		/* Recognize UTF8 BOM */
		if ( line->len > 2 &&
				(unsigned char)(p[0])==0xEF &&
				(unsigned char)(p[1])==0xBB &&
				(unsigned char)(p[2])==0xBF ) {
			*fcharset = CHARSET_UNICODE;
			p += 3;
		}
		if ( copacin_istag( p ) ) {
			if ( inref ) newstr_addchar( reference, '\n' );
			newstr_strcat( reference, p );
			newstr_empty( line );
			inref = 1;
		} else if ( inref ) {
			if ( p ) {
				/* copac puts tag only on 1st line */
				newstr_addchar( reference, ' ' );
				if ( *p ) p++;
				if ( *p ) p++;
				if ( *p ) p++;
			   	newstr_strcat( reference, p );
			}
			newstr_empty( line );
		} else {
			newstr_empty( line );
		}
	}
	return haveref;
}

/*****************************************************
 PUBLIC: int copacin_processf()
*****************************************************/

static char*
copacin_addtag2( char *p, newstr *tag, newstr *data )
{
	int  i;
	i =0;
	while ( i<3 && *p ) {
		newstr_addchar( tag, *p++ );
		i++;
	}
	while ( *p==' ' || *p=='\t' ) p++;
	while ( *p && *p!='\r' && *p!='\n' ) {
		newstr_addchar( data, *p );
		p++;
	}
	newstr_trimendingws( data );
	while ( *p=='\n' || *p=='\r' ) p++;
	return p;
}

static char *
copacin_nextline( char *p )
{
	while ( *p && *p!='\n' && *p!='\r') p++;
	while ( *p=='\n' || *p=='\r' ) p++;
	return p;
}

static int
copacin_processf( fields *copacin, char *p, char *filename, long nref, param *pm )
{
	newstr tag, data;
	int status;
	newstr_init( &tag );
	newstr_init( &data );
	while ( *p ) {
		p = skip_ws( p );
		if ( copacin_istag( p ) ) {
			p = copacin_addtag2( p, &tag, &data );
			/* don't add empty strings */
			if ( tag.len && data.len ) {
				status = fields_add( copacin, tag.data, data.data, 0 );
				if ( status!=FIELDS_OK ) return 0;
			}
			newstr_empty( &tag );
			newstr_empty( &data );
		}
		else p = copacin_nextline( p );
	}
	newstr_free( &tag );
	newstr_free( &data );
	return 1;
}

/*****************************************************
 PUBLIC: int copacin_convertf(), returns BIBL_OK or BIBL_ERR_MEMERR
*****************************************************/

/* copac names appear to always start with last name first, but don't
 * always seem to have a comma after the name
 *
 * editors seem to be stuck in as authors with the tag "[Editor]" in it
 */
static int
copacin_person( fields *bibin, newstr *intag, newstr *invalue, int level, param *pm, char *outtag, fields *bibout )
{
	char *usetag = outtag, editor[]="EDITOR";
	newstr usename, *s;
	list tokens;
	int comma = 0, i, ok;

	if ( list_find( &(pm->asis), invalue->data ) !=-1  ||
	     list_find( &(pm->corps), invalue->data ) !=-1 ) {
		ok = name_add( bibout, outtag, invalue->data, level, &(pm->asis), &(pm->corps) );
		if ( ok ) return BIBL_OK;
		else return BIBL_ERR_MEMERR;
	}

	list_init( &tokens );
	newstr_init( &usename );

	list_tokenize( &tokens, invalue, " ", 1 );
	for ( i=0; i<tokens.n; ++i ) {
		s = list_get( &tokens, i );
		if ( !strcmp( s->data, "[Editor]" ) ) {
			usetag = editor;
			newstr_strcpy( s, "" );
		} else if ( s->len && s->data[s->len-1]==',' ) {
			comma++;
		}
	}

	if ( comma==0 && tokens.n ) {
		s = list_get( &tokens, 0 );
		newstr_addchar( s, ',' );
	}

	for ( i=0; i<tokens.n; ++i ) {
		s = list_get( &tokens, i );
		if ( s->len==0 ) continue;
		if ( i ) newstr_addchar( &usename, ' ' );
		newstr_newstrcat( &usename, s );
	}

	list_free( &tokens );

	ok = name_add( bibout, usetag, usename.data, level, &(pm->asis), &(pm->corps) );

	newstr_free( &usename );

	if ( ok ) return BIBL_OK;
	else return BIBL_ERR_MEMERR;
}

static void
copacin_report_notag( param *p, char *tag )
{
	if ( p->verbose ) {
		if ( p->progname ) fprintf( stderr, "%s: ", p->progname );
		fprintf( stderr, "Cannot find tag '%s'\n", tag );
	}
}

static int
copacin_convertf( fields *bibin, fields *bibout, int reftype, param *p )
{
	static int (*convertfns[NUM_REFTYPES])(fields *, newstr *, newstr *, int, param *, char *, fields *) = {
		[ 0 ... NUM_REFTYPES-1 ] = generic_null,
		[ SIMPLE       ] = generic_simple,
		[ TITLE        ] = generic_title,
		[ NOTES        ] = generic_notes,
		[ SERIALNO     ] = generic_serialno,
		[ PERSON       ] = copacin_person
	};

	int  process, level, i, nfields, status = BIBL_OK;
	newstr *intag, *invalue;
	char *outtag;

	nfields = fields_num( bibin );
	for ( i=0; i<nfields; ++i ) {

		intag = fields_tag( bibin, i, FIELDS_STRP );

		if ( !translate_oldtag( intag->data, reftype, p->all, p->nall, &process, &level, &outtag ) ) {
			copacin_report_notag( p, intag->data );
			continue;
		}

		invalue = fields_value( bibin, i, FIELDS_STRP );

		status = convertfns[ process ] ( bibin, intag, invalue, level, p, outtag, bibout );
		if ( status!=BIBL_OK ) return status;

	}

	return status;
}
