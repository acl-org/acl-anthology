/*
 * risin.c
 *
 * Copyright (c) Chris Putnam 2003-2013
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
#include "risin.h"

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

int
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

int
risin_processf( fields *risin, char *p, char *filename, long nref )
{
	newstr tag, data;
	int n;

	newstrs_init( &tag, &data, NULL );

	while ( *p ) {
		if ( risin_istag( p ) ) {
		p = process_line( &tag, &data, p );
		/* no anonymous fields allowed */
		if ( tag.len )
			fields_add( risin, tag.data, data.data, 0 );
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

/* oxfordjournals hide the DOI in the NOTES N1 field */
static int
risin_addnotes( fields *f, char *tag, newstr *s, int level )
{
	int doi = is_doi( s->data );
	if ( doi!=-1 )
		return fields_add( f, "DOI", &(s->data[doi]), level );
	else
		return fields_add( f, tag, s->data, level );
}

static int
is_uri_file_scheme( char *p )
{
	if ( !strncmp( p, "file:", 5 ) ) return 5;
	return 0;
}

static int
is_uri_remote_scheme( char *p )
{
	char *scheme[] = { "http:", "ftp:", "git:", "gopher:" };
	int i, len, nschemes = sizeof( scheme ) / sizeof( scheme[0] );
	for ( i=0; i<nschemes; ++i ) {
		len = strlen( scheme[i] );
		if ( !strncmp( p, scheme[i], len ) ) return len;
	}
	return 0;
}

static int
risin_addfile( fields *f, char *tag, newstr *s, int level )
{
	char *p;
	int n;

	/* if URL is file:///path/to/xyz.pdf, only store "///path/to/xyz.pdf" */
	n = is_uri_file_scheme( s->data );
	if ( n ) {
		/* skip past "file:" and store only actual path */
		p = s->data + n;
		return fields_add( f, tag, p, level );
	}

	/* if URL is http:, ftp:, etc. store as a URL */
	n = is_uri_remote_scheme( s->data );
	if ( n ) {
		return fields_add( f, "URL", s->data, level );
	}

	/* badly formed, RIS wants URI, but store value anyway */
	return fields_add( f, tag, s->data, level );
}

/* scopus puts DOI in the DO or DI tag, but it needs cleaning */
static int
risin_adddoi( fields *f, char *tag, newstr *s, int level )
{
	int doi = is_doi( s->data );
	if ( doi!=-1 )
		return fields_add( f, "DOI", &(s->data[doi]), level );
	else return 1;
}

static int
risin_adddate( fields *f, char *tag, newstr *d, int level )
{
	char *p = d->data;
	newstr date;
	int part = ( !strncasecmp( tag, "PART", 4 ) ), ok;

	newstr_init( &date );
	while ( *p && *p!='/' ) newstr_addchar( &date, *p++ );
	if ( *p=='/' ) p++;
	if ( date.len>0 ) {
		if ( part ) ok = fields_add( f, "PARTYEAR", date.data, level );
		else        ok = fields_add( f, "YEAR",     date.data, level );
		if ( !ok ) return 0;
	}

	newstr_empty( &date );
	while ( *p && *p!='/' ) newstr_addchar( &date, *p++ );
	if ( *p=='/' ) p++;
	if ( date.len>0 ) {
		if ( part ) ok = fields_add( f, "PARTMONTH", date.data, level );
		else        ok = fields_add( f, "MONTH",     date.data, level );
		if ( !ok ) return 0;
	}

	newstr_empty( &date );
	while ( *p && *p!='/' ) newstr_addchar( &date, *p++ );
	if ( *p=='/' ) p++;
	if ( date.len>0 ) {
		if ( part ) ok = fields_add( f, "PARTDAY", date.data, level );
		else        ok = fields_add( f, "DAY",     date.data, level );
		if ( !ok ) return 0;
	}

	newstr_empty( &date );
	while ( *p ) newstr_addchar( &date, *p++ );
	if ( date.len>0 ) {
		if ( part ) ok = fields_add( f, "PARTDATEOTHER", date.data,level);
		else        ok = fields_add( f, "DATEOTHER", date.data, level );
		if ( !ok ) return 0;
	}
	newstr_free( &date );
	return 1;
}

int
risin_typef( fields *risin, char *filename, int nref, param *p, variants *all, int nall )
{
	char *refnum = "";
	int n, reftype, nreftype;
	n = fields_find( risin, "TY", 0 );
	nreftype = fields_find( risin, "ID", 0 );
	if ( nreftype!=-1 ) refnum = risin[n].data->data;
	if ( n!=-1 )
		reftype = get_reftype( (risin[n].data)->data, nref, p->progname,
			all, nall, refnum );
	else
		reftype = get_reftype( "", nref, p->progname, all, nall, refnum ); /*default */
	return reftype;
}

static void
risin_report_notag( param *p, char *tag )
{
	if ( p->verbose && strcmp( tag, "TY" ) ) {
		if ( p->progname ) fprintf( stderr, "%s: ", p->progname );
		fprintf( stderr, "Did not identify RIS tag '%s'\n", tag );
	}
}

int
risin_convertf( fields *risin, fields *f, int reftype, param *p, variants *all, int nall )
{
	int process, level, i, n, nfields, ok;
	char *outtag, *tag, *value;
	newstr *t, *d;

	nfields = fields_num( risin );

	for ( i=0; i<nfields; ++i ) {
		t = fields_tag( risin, i, FIELDS_STRP );
		n = translate_oldtag( t->data, reftype, all, nall, &process, &level, &outtag );
		if ( n==-1 ) {
			risin_report_notag( p, t->data );
			continue;
		}
		if ( process==ALWAYS ) continue; /* add in core code */

		d = fields_value( risin, i, FIELDS_STRP );

		switch ( process ) {

		case SIMPLE:
			ok = fields_add( f, outtag, d->data, level );
			break;

		case PERSON:
			ok = name_add( f, outtag, d->data, level, &(p->asis), &(p->corps) );
			break;

		case TITLE:
			ok = title_process( f, outtag, d->data, level, p->nosplittitle );
			break;

		case SERIALNO:
			ok = addsn( f, d->data, level );
			break;

		case DATE:
			ok = risin_adddate( f, outtag, d, level );
			break;

		case NOTES:
			ok = risin_addnotes( f, outtag, d, level );
			break;

		case DOI:
			ok = risin_adddoi( f, outtag, d, level );
			break;

		case LINKEDFILE:
			ok = risin_addfile( f, outtag, d, level );
			break;

		default:
			ok = 1;
			break;

		}
		if ( !ok ) return BIBL_ERR_MEMERR;
	}

	/* look for thesis-type hint */
	if ( !strcasecmp( all[reftype].type, "THES" ) ) {
		for ( i=0; i<nfields; ++i ) {
			tag = fields_tag( risin, i, FIELDS_CHRP );
			if ( strcasecmp( tag, "U1" ) ) continue;
			value = fields_value( risin, i, FIELDS_CHRP );
			if ( !strcasecmp(value,"Ph.D. Thesis")||
			     !strcasecmp(value,"Masters Thesis")||
			     !strcasecmp(value,"Diploma Thesis")||
			     !strcasecmp(value,"Doctoral Thesis")||
			     !strcasecmp(value,"Habilitation Thesis")) {
				ok = fields_add( f, "GENRE", value, 0 );
				if ( !ok ) return BIBL_ERR_MEMERR;
			}
		}
	}

	return BIBL_OK;
}
