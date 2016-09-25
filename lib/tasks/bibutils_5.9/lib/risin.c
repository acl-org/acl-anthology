/*
 * risin.c
 *
 * Copyright (c) Chris Putnam 2003-2016
 *
 * Source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "newstr.h"
#include "newstr_conv.h"
#include "fields.h"
#include "name.h"
#include "title.h"
#include "serialno.h"
#include "reftypes.h"
#include "doi.h"
#include "bibformats.h"
#include "generic.h"

extern variants ris_all[];
extern int ris_nall;

/*****************************************************
 PUBLIC: void risin_initparams()
*****************************************************/

static int risin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset );
static int risin_processf( fields *risin, char *p, char *filename, long nref, param *pm );
static int risin_typef( fields *risin, char *filename, int nref, param *p );
static int risin_convertf( fields *risin, fields *info, int reftype, param *p );

void
risin_initparams( param *p, const char *progname )
{
	p->readformat       = BIBL_RISIN;
	p->charsetin        = BIBL_CHARSET_DEFAULT;
	p->charsetin_src    = BIBL_SRC_DEFAULT;
	p->latexin          = 0;
	p->xmlin            = 0;
	p->utf8in           = 0;
	p->nosplittitle     = 0;
	p->verbose          = 0;
	p->addcount         = 0;
	p->output_raw       = 0;

	p->readf    = risin_readf;
	p->processf = risin_processf;
	p->cleanf   = NULL;
	p->typef    = risin_typef;
	p->convertf = risin_convertf;
	p->all      = ris_all;
	p->nall     = ris_nall;

	list_init( &(p->asis) );
	list_init( &(p->corps) );

	if ( !progname ) p->progname = NULL;
	else p->progname = strdup( progname );
}

/*****************************************************
 PUBLIC: int risin_readf()
*****************************************************/

/* RIS definition of a tag is strict:
    character 1 = uppercase alphabetic character
    character 2 = uppercase alphabetic character or digit
    character 3 = space (ansi 32)
    character 4 = space (ansi 32)
    character 5 = dash (ansi 45)
    character 6 = space (ansi 32)
*/
static int
risin_istag( char *buf )
{
	if (! (buf[0]>='A' && buf[0]<='Z') ) return 0;
	if (! (((buf[1]>='A' && buf[1]<='Z'))||(buf[1]>='0'&&buf[1]<='9')) ) 
		return 0;
	if (buf[2]!=' ') return 0;
	if (buf[3]!=' ') return 0;
	if (buf[4]!='-') return 0;
	if (buf[5]!=' ') return 0;
	return 1;
}

static int
readmore( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line )
{
	if ( line->len ) return 1;
	else return newstr_fget( fp, buf, bufsize, bufpos, line );
}

static int
risin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, 
		newstr *reference, int *fcharset )
{
	int haveref = 0, inref = 0, readtoofar = 0;
	unsigned char *up;
	char *p;
	*fcharset = CHARSET_UNKNOWN;
	while ( !haveref && readmore( fp, buf, bufsize, bufpos, line ) ) {
		if ( !line->data || line->len==0 ) continue;
		p = &( line->data[0] );
		/* Recognize UTF8 BOM */
		up = (unsigned char * ) p;
		if ( line->len > 2 && 
				up[0]==0xEF && up[1]==0xBB && up[2]==0xBF ) {
			*fcharset = CHARSET_UNICODE;
			p += 3;
		}
		/* Each reference starts with 'TY  - ' && 
		 * ends with 'ER  - ' */
		if ( strncmp(p,"TY  - ",6)==0 ) {
			if ( !inref ) {
				inref = 1;
			} else {
				/* we've read too far.... */
				readtoofar = 1;
				inref = 0;
			}
		}
		if ( risin_istag( p ) ) {
			if ( !inref ) {
				fprintf(stderr,"Warning.  Tagged line not "
					"in properly started reference.\n");
				fprintf(stderr,"Ignored: '%s'\n", p );
			} else if ( !strncmp(p,"ER  -",5) ) {
				inref = 0;
			} else {
				newstr_addchar( reference, '\n' );
				newstr_strcat( reference, p );
			}
		}
		/* not a tag, but we'll append to last values ...*/
		else if ( inref && strncmp(p,"ER  -",5)) {
			newstr_addchar( reference, '\n' );
			newstr_strcat( reference, p );
		}
		if ( !inref && reference->len ) haveref = 1;
		if ( !readtoofar ) newstr_empty( line );
	}
	if ( inref ) haveref = 1;
	return haveref;
}

/*****************************************************
 PUBLIC: int risin_processf()
*****************************************************/

static char*
process_line2( newstr *tag, newstr *data, char *p )
{
	while ( *p==' ' || *p=='\t' ) p++;
	while ( *p && *p!='\r' && *p!='\n' )
		newstr_addchar( data, *p++ );
	while ( *p=='\r' || *p=='\n' ) p++;
	return p;
}

static char*
process_line( newstr *tag, newstr *data, char *p )
{
	int i = 0;
	while ( i<6 && *p ) {
		if ( i<2 ) newstr_addchar( tag, *p );
		p++;
		i++;
	}
	while ( *p==' ' || *p=='\t' ) p++;
	while ( *p && *p!='\r' && *p!='\n' )
		newstr_addchar( data, *p++ );
	newstr_trimendingws( data );
	while ( *p=='\n' || *p=='\r' ) p++;
	return p;
}

static int
risin_processf( fields *risin, char *p, char *filename, long nref, param *pm )
{
	newstr tag, data;
	int status, n;

	newstrs_init( &tag, &data, NULL );

	while ( *p ) {
		if ( risin_istag( p ) )
			p = process_line( &tag, &data, p );
		/* no anonymous fields allowed */
		if ( tag.len ) {
			status = fields_add( risin, tag.data, data.data, 0 );
			if ( status!=FIELDS_OK ) return 0;
		} else {
			p = process_line2( &tag, &data, p );
			n = fields_num( risin );
			if ( data.len && n>0 ) {
				newstr *od;
				od = fields_value( risin, n-1, FIELDS_STRP );
				newstr_addchar( od, ' ' );
				newstr_strcat( od, data.data );
			}
		}
		newstrs_empty( &tag, &data, NULL );
	}

	newstrs_free( &tag, &data, NULL );
	return 1;
}

/*****************************************************
 PUBLIC: int risin_typef()
*****************************************************/

static int
risin_typef( fields *risin, char *filename, int nref, param *p )
{
	char *refnum = "";
	int n, reftype, nreftype;
	n = fields_find( risin, "TY", 0 );
	nreftype = fields_find( risin, "ID", 0 );
	if ( nreftype!=-1 ) refnum = risin[n].data->data;
	if ( n!=-1 )
		reftype = get_reftype( (risin[n].data)->data, nref, p->progname,
			p->all, p->nall, refnum );
	else
		reftype = get_reftype( "", nref, p->progname, p->all, p->nall, refnum ); /*default */
	return reftype;
}

/*****************************************************
 PUBLIC: int risin_convertf()
*****************************************************/

static int
is_uri_file_scheme( char *p )
{
	if ( !strncmp( p, "file:", 5 ) ) return 5;
	return 0;
}

static int
risin_linkedfile( fields *bibin, newstr *intag, newstr *invalue, int level, param *pm, char *outtag, fields *bibout )
{
	int fstatus, n;
	char *p;

	/* if URL is file:///path/to/xyz.pdf, only store "///path/to/xyz.pdf" */
	n = is_uri_file_scheme( invalue->data );
	if ( n ) {
		/* skip past "file:" and store only actual path */
		p = invalue->data + n;
		fstatus = fields_add( bibout, outtag, p, level );
		if ( fstatus==FIELDS_OK ) return BIBL_OK;
		else return BIBL_ERR_MEMERR;
	}

	/* if URL is http:, ftp:, etc. store as a URL */
	n = is_uri_remote_scheme( invalue->data );
	if ( n!=-1 ) {
		fstatus = fields_add( bibout, "URL", invalue->data, level );
		if ( fstatus==FIELDS_OK ) return BIBL_OK;
		else return BIBL_ERR_MEMERR;
	}

	/* badly formed, RIS wants URI, but store value anyway */
	fstatus = fields_add( bibout, outtag, invalue->data, level );
	if ( fstatus==FIELDS_OK ) return BIBL_OK;
	else return BIBL_ERR_MEMERR;
}

/* scopus puts DOI in the DO or DI tag, but it needs cleaning */
static int
risin_doi( fields *bibin, newstr *intag, newstr *invalue, int level, param *pm, char *outtag, fields *bibout )
{
	int fstatus, doi;
	doi = is_doi( invalue->data );
	if ( doi!=-1 ) {
		fstatus = fields_add( bibout, "DOI", &(invalue->data[doi]), level );
		if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	return BIBL_OK;
}

static int
risin_date( fields *bibin, newstr *intag, newstr *invalue, int level, param *pm, char *outtag, fields *bibout )
{
	char *p = invalue->data;
	newstr date;
	int part, status;

	part = ( !strncasecmp( outtag, "PART", 4 ) );

	newstr_init( &date );
	while ( *p && *p!='/' ) newstr_addchar( &date, *p++ );
	if ( *p=='/' ) p++;
	if ( date.len>0 ) {
		if ( part ) status = fields_add( bibout, "PARTDATE:YEAR", date.data, level );
		else        status = fields_add( bibout, "DATE:YEAR",     date.data, level );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}

	newstr_empty( &date );
	while ( *p && *p!='/' ) newstr_addchar( &date, *p++ );
	if ( *p=='/' ) p++;
	if ( date.len>0 ) {
		if ( part ) status = fields_add( bibout, "PARTDATE:MONTH", date.data, level );
		else        status = fields_add( bibout, "DATE:MONTH",     date.data, level );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}

	newstr_empty( &date );
	while ( *p && *p!='/' ) newstr_addchar( &date, *p++ );
	if ( *p=='/' ) p++;
	if ( date.len>0 ) {
		if ( part ) status = fields_add( bibout, "PARTDATE:DAY", date.data, level );
		else        status = fields_add( bibout, "DATE:DAY",     date.data, level );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}

	newstr_empty( &date );
	while ( *p ) newstr_addchar( &date, *p++ );
	if ( date.len>0 ) {
		if ( part ) status = fields_add( bibout, "PARTDATE:OTHER", date.data,level);
		else        status = fields_add( bibout, "DATE:OTHER", date.data, level );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	newstr_free( &date );
	return BIBL_OK;
}

/* look for thesis-type hint */
static int
risin_thesis_hints( fields *bibin, int reftype, param *p, fields *bibout )
{
	int i, nfields, fstatus;
	char *tag, *value;

	if ( strcasecmp( p->all[reftype].type, "THES" ) ) return BIBL_OK;

	nfields = fields_num( bibin );
	for ( i=0; i<nfields; ++i ) {
		tag = fields_tag( bibin, i, FIELDS_CHRP );
		if ( strcasecmp( tag, "U1" ) ) continue;
		value = fields_value( bibin, i, FIELDS_CHRP );
		if ( !strcasecmp(value,"Ph.D. Thesis")||
		     !strcasecmp(value,"Masters Thesis")||
		     !strcasecmp(value,"Diploma Thesis")||
		     !strcasecmp(value,"Doctoral Thesis")||
		     !strcasecmp(value,"Habilitation Thesis")) {
			fstatus = fields_add( bibout, "GENRE", value, 0 );
			if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		}
	}
	return BIBL_OK;
}

static void
risin_report_notag( param *p, char *tag )
{
	if ( p->verbose && strcmp( tag, "TY" ) ) {
		if ( p->progname ) fprintf( stderr, "%s: ", p->progname );
		fprintf( stderr, "Did not identify RIS tag '%s'\n", tag );
	}
}

static int
risin_convertf( fields *bibin, fields *bibout, int reftype, param *p )
{
	static int (*convertfns[NUM_REFTYPES])(fields *, newstr *, newstr *, int, param *, char *, fields *) = {
		[ 0 ... NUM_REFTYPES-1 ] = generic_null,
		[ SIMPLE       ] = generic_simple,
		[ TITLE        ] = generic_title,
		[ PERSON       ] = generic_person,
		[ SERIALNO     ] = generic_serialno,
		[ NOTES        ] = generic_notes,
		[ DATE         ] = risin_date,
		[ DOI          ] = risin_doi,
		[ LINKEDFILE   ] = risin_linkedfile,
        };
	int process, level, i, nfields, status = BIBL_OK;
	newstr *intag, *invalue;
	char *outtag;

	nfields = fields_num( bibin );

	for ( i=0; i<nfields; ++i ) {
		intag = fields_tag( bibin, i, FIELDS_STRP );
		if ( !translate_oldtag( intag->data, reftype, p->all, p->nall, &process, &level, &outtag ) ) {
			risin_report_notag( p, intag->data );
			continue;
		}
		invalue = fields_value( bibin, i, FIELDS_STRP );

		status = convertfns[ process ] ( bibin, intag, invalue, level, p, outtag, bibout );
		if ( status!=BIBL_OK ) return status;
	}

	if ( status == BIBL_OK ) status = risin_thesis_hints( bibin, reftype, p, bibout );

	if ( status==BIBL_OK && p->verbose ) fields_report( bibout, stderr );

	return status;
}
