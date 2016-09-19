/*
 * endin.c
 *
 * Copyright (c) Chris Putnam 2003-2016
 *
 * Program and source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "is_ws.h"
#include "doi.h"
#include "newstr.h"
#include "newstr_conv.h"
#include "fields.h"
#include "reftypes.h"
#include "bibformats.h"
#include "generic.h"

extern variants end_all[];
extern int end_nall;

/*****************************************************
 PUBLIC: void endin_initparams()
*****************************************************/

static int endin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset );
static int endin_processf( fields *endin, char *p, char *filename, long nref, param *pm );
int endin_typef( fields *endin, char *filename, int nrefs, param *p );
int endin_convertf( fields *endin, fields *info, int reftype, param *p );
int endin_cleanf( bibl *bin, param *p );

void
endin_initparams( param *p, const char *progname )
{
	p->readformat       = BIBL_ENDNOTEIN;
	p->charsetin        = BIBL_CHARSET_DEFAULT;
	p->charsetin_src    = BIBL_SRC_DEFAULT;
	p->latexin          = 0;
	p->xmlin            = 0;
	p->utf8in           = 0;
	p->nosplittitle     = 0;
	p->verbose          = 0;
	p->addcount         = 0;
	p->output_raw       = 0;

	p->readf    = endin_readf;
	p->processf = endin_processf;
	p->cleanf   = endin_cleanf;
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
 PUBLIC: int endin_readf()
*****************************************************/

/* Endnote tag definition:
    character 1 = '%'
    character 2 = alphabetic character or digit (or other characters)
    character 3 = space (ansi 32)
*/
static int
endin_istag( char *buf )
{
	const char others[]="!@#$^&*()+=?[~>";
	if ( buf[0]!='%' ) return 0;
	if ( buf[2]!=' ' ) return 0;
	if ( isalpha( (unsigned char)buf[1] ) ) return 1;
	if ( isdigit( (unsigned char)buf[1] ) ) return 1;
	if ( strchr( others, buf[1] ) ) return 1;
	return 0;
}

static int
readmore( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line )
{
	if ( line->len ) return 1;
	else return newstr_fget( fp, buf, bufsize, bufpos, line );
}

static int
endin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset )
{
	int haveref = 0, inref = 0;
	unsigned char *up;
	char *p;
	*fcharset = CHARSET_UNKNOWN;
	while ( !haveref && readmore( fp, buf, bufsize, bufpos, line ) ) {
		if ( !line->data ) continue;
		p = &(line->data[0]);

		/* Skip <feff> Unicode header information */
		/* <feff> = ef bb bf */
		up = (unsigned char* ) p;
		if ( line->len > 2 && up[0]==0xEF && up[1]==0xBB &&
				up[2]==0xBF ) {
			*fcharset = CHARSET_UNICODE;
			p += 3;
		}

		if ( !*p ) {
			if ( inref ) haveref = 1; /* blank line separates */
			else continue; /* blank line to ignore */
		}
		/* Each reference starts with a tag && ends with a blank line */
		if ( endin_istag( p ) ) {
			if ( reference->len ) newstr_addchar( reference, '\n' );
			newstr_strcat( reference, p );
			inref = 1;
		} else if ( inref && p ) {
			newstr_addchar( reference, '\n' );
		   	newstr_strcat( reference, p );
		}
		newstr_empty( line );
	}
	if ( reference->len ) haveref = 1;
	return haveref;
}

/*****************************************************
 PUBLIC: int endin_processf()
*****************************************************/
static char*
process_endline( newstr *tag, newstr *data, char *p )
{
	int  i;

	i = 0;
	while ( i<2 && *p ) {
		newstr_addchar( tag, *p++);
		i++;
	}
	while ( *p==' ' || *p=='\t' ) p++;

	while ( *p && *p!='\r' && *p!='\n' )
		newstr_addchar( data, *p++ );
	newstr_trimendingws( data );

	while ( *p=='\r' || *p=='\n' ) p++;

	return p;
}

static char *
process_endline2( newstr *tag, newstr *data, char *p )
{
	while ( *p==' ' || *p=='\t' ) p++;
	while ( *p && *p!='\r' && *p!='\n' )
		newstr_addchar( data, *p++ );
	newstr_trimendingws( data );
	while ( *p=='\r' || *p=='\n' ) p++;
	return p;
}

static int
endin_processf( fields *endin, char *p, char *filename, long nref, param *pm )
{
	newstr tag, data;
	int status, n;
	newstrs_init( &tag, &data, NULL );
	while ( *p ) {
		newstrs_empty( &tag, &data, NULL );
		if ( endin_istag( p ) ) {
			p = process_endline( &tag, &data, p );
			if ( data.len==0 ) continue;
			status = fields_add( endin, tag.data, data.data, 0 );
			if ( status!=FIELDS_OK ) return 0;
		} else {
			p = process_endline2( &tag, &data, p );
			/* endnote puts %K only on 1st line of keywords */
			n = fields_num( endin );
			if ( n>0 && data.len ) {
			if ( !strncmp( endin->tag[n-1].data, "%K", 2 ) ) {
				status = fields_add( endin, "%K", data.data, 0 );
				if ( status!=FIELDS_OK ) return 0;
			} else {
				newstr_addchar( &(endin->data[n-1]), ' ' );
				newstr_strcat( &(endin->data[n-1]), data.data );
			}
			}
		}
	}
	newstrs_free( &tag, &data, NULL );
	return 1;
}

/*****************************************************
 PUBLIC: int endin_typef()
*****************************************************/

/* Endnote defaults if no %0
 *
 * if %J & %V - journal article
 * if %B - book section
 * if %R & !%T - report
 * if %I & !%B & !%J & !%R - book
 * if !%B & !%J & !%R & !%I - journal article
 */
int
endin_typef( fields *endin, char *filename, int nrefs, param *p )
{
	char *refnum = "";
	int n, reftype, nrefnum, nj, nv, nb, nr, nt, ni;
	n = fields_find( endin, "%0", 0 );
	nrefnum = fields_find( endin, "%F", 0 );
	if ( nrefnum!=-1 ) refnum = endin->data[nrefnum].data;
	if ( n!=-1 ) {
		reftype = get_reftype( endin->data[n].data, nrefs, 
			p->progname, p->all, p->nall, refnum );
	} else {
		nj = fields_find( endin, "%J", 0 );
		nv = fields_find( endin, "%V", 0 );
		nb = fields_find( endin, "%B", 0 );
		nr = fields_find( endin, "%R", 0 );
		nt = fields_find( endin, "%T", 0 );
		ni = fields_find( endin, "%I", 0 );
		if ( nj!=-1 && nv!=-1 ) {
			reftype = get_reftype( "Journal Article", nrefs,
					p->progname, p->all, p->nall, refnum );
		} else if ( nb!=-1 ) {
			reftype = get_reftype( "Book Section", nrefs,
					p->progname, p->all, p->nall, refnum );
		} else if ( nr!=-1 && nt==-1 ) {
			reftype = get_reftype( "Report", nrefs,
					p->progname, p->all, p->nall, refnum );
		} else if ( ni!=-1 && nb==-1 && nj==-1 && nr==-1 ) {
			reftype = get_reftype( "Book", nrefs,
					p->progname, p->all, p->nall, refnum );
		} else if ( nb==-1 && nj==-1 && nr==-1 && ni==-1 ) {
			reftype = get_reftype( "Journal Article", nrefs,
					p->progname, p->all, p->nall, refnum );
		} else {
			reftype = get_reftype( "", nrefs, p->progname, 
					p->all, p->nall, refnum ); /* default */
		}
	}
	return reftype;
}

/*****************************************************
 PUBLIC: void endin_cleanf()
*****************************************************/

/* Wiley puts multiple authors separated by commas on the %A lines.
 * We can detect this by finding the terminal comma in the data.
 *
 * "%A" "Author A. X. Last, Author N. B. Next,"
 */
static int
is_wiley_author( fields *endin, int n )
{
	newstr *t, *d;
	t = &(endin->tag[n]);
	if ( !t->data || strcmp( t->data, "%A" ) ) return 0;
	d = &( endin->data[n] );
	if ( !(d->data) || d->len==0 ) return 0;
	if ( d->data[d->len-1]!=',' ) return 0;
	return 1;
}

static int
cleanup_wiley_author( fields *endin, int n )
{	
	newstr *instring, copy, name;
	int status, nauthor = 0;
	char *p;

	newstrs_init( &copy, &name, NULL );

	instring = &( endin->data[n] );
	newstr_newstrcpy( &copy, instring );

	p = copy.data;
	while ( *p ) {
		if ( *p==',' ) {
			if ( newstr_memerr( &name ) )
				return BIBL_ERR_MEMERR;
			if ( nauthor==0 ) {
				/* ...replace the first author in the field */
				newstr_newstrcpy( instring, &name );
				if ( newstr_memerr( instring ) )
					return BIBL_ERR_MEMERR;
			} else {
				status = fields_add( endin, endin->tag[n].data,
					name.data, endin->level[n] );
				if ( status!=FIELDS_OK )
					return BIBL_ERR_MEMERR;
			}
			newstr_empty( &name );
			nauthor++;
			p++;
			while ( is_ws( *p ) ) p++;
		} else {
			newstr_addchar( &name, *p );
			p++;
		}
	}

	newstrs_free( &copy, &name, NULL );
	return BIBL_OK;
}

static int
endin_cleanref( fields *endin )
{
	int i, n, status;
	n = fields_num( endin );
	for ( i=0; i<n; ++i ) {
		if ( is_wiley_author( endin, i ) ) {
			status = cleanup_wiley_author( endin, i );
			if ( status!=BIBL_OK ) return status;
		}
	}
	return BIBL_OK;
}

int
endin_cleanf( bibl *bin, param *p )
{
        long i;
        for ( i=0; i<bin->nrefs; ++i )
                endin_cleanref( bin->ref[i] );
	return BIBL_OK;
}

/*****************************************************
 PUBLIC: int endin_convertf(), returns BIBL_OK or BIBL_ERR_MEMERR
*****************************************************/

/* month_convert()
 * convert month name to number in format MM, e.g. "January" -> "01"
 * if converted, return 1
 * otherwise return 0
 */
static int
month_convert( char *in, char *out )
{
	char *month1[12]={
		"January",   "February",
		"March",     "April",
		"May",       "June",
		"July",      "August",
		"September", "October",
		"November",  "December"
	};
	char *month2[12]={
		"Jan", "Feb",
		"Mar", "Apr",
		"May", "Jun",
		"Jul", "Aug",
		"Sep", "Oct",
		"Nov", "Dec"
	};
	int i, found = -1;

	for ( i=0; i<12 && found==-1; ++i ) {
		if ( !strcasecmp( in, month1[i] ) ) found = i;
		if ( !strcasecmp( in, month2[i] ) ) found = i;
	}

	if ( found==-1 ) return 0;

	if ( found > 8 )
		sprintf( out, "%d", found+1 );
	else
		sprintf( out, "0%d", found+1 );

	return 1;
}

static int
endin_date( fields *bibin, newstr *intag, newstr *invalue, int level, param *pm, char *outtag, fields *bibout )
{
	char *tags[3][2] = {
		{ "DATE:YEAR",  "PARTDATE:YEAR" },
		{ "DATE:MONTH", "PARTDATE:MONTH" },
		{ "DATE:DAY",   "PARTDATE:DAY" }
	};
	char *p = invalue->data;
	char month[10], *m;
	int part, status;
	newstr date;

	newstr_init( &date );

	if ( !strncasecmp( outtag, "PART", 4 ) ) part = 1;
	else part = 0;

	/* %D YEAR */
	if ( !strcasecmp( intag->data, "%D" ) ) {
		newstr_cpytodelim( &date, skip_ws( p ), "", 0 );
		if ( newstr_memerr( &date ) ) return BIBL_ERR_MEMERR;
		if ( date.len>0 ) {
			status = fields_add( bibout, tags[0][part], date.data, level );
			if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		}
	}

	/* %8 MONTH DAY, YEAR */
	/* %8 MONTH, YEAR */
	/* %8 MONTH YEAR */
	else if ( !strcasecmp( intag->data, "%8" ) ) {

		/* ...get month */
		p = newstr_cpytodelim( &date, skip_ws( p ), " ,\n", 0 );
		if ( newstr_memerr( &date ) ) return BIBL_ERR_MEMERR;
		if ( date.len>0 ) {
			if ( month_convert( date.data, month ) ) m = month;
			else m = date.data;
			status = fields_add( bibout, tags[1][part], m, level );
			if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		}

		p = skip_ws( p );
		if ( *p==',' ) p++;

		/* ...get days */
		p = newstr_cpytodelim( &date, skip_ws( p ), ",\n", 0 );
		if ( newstr_memerr( &date ) ) return BIBL_ERR_MEMERR;
		if ( date.len>0 && date.len<3 ) {
			status = fields_add( bibout, tags[2][part], date.data, level );
			if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		} else if ( date.len==4 ) {
			status = fields_add( bibout, tags[0][part], date.data, level );
			if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		}

		p = skip_ws( p );
		if ( *p==',' ) p++;

		/* ...get year */
		p = newstr_cpytodelim( &date, skip_ws( p ), " \t\n\r", 0 );
		if ( newstr_memerr( &date ) ) return BIBL_ERR_MEMERR;
		if ( date.len > 0 ) {
			status = fields_add( bibout, tags[0][part], date.data, level );
			if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		}
	}
	newstr_free( &date );
	return BIBL_OK;
}

static int
endin_type( fields *bibin, newstr *intag, newstr *invalue, int level, param *pm, char *outtag, fields *bibout )
{
	lookups types[] = {
		{ "GENERIC",                "ARTICLE" },
		{ "BOOK",                   "BOOK" },
		{ "MANUSCRIPT",             "MANUSCRIPT" },
		{ "CONFERENCE PROCEEDINGS", "INPROCEEDINGS"},
		{ "REPORT",                 "REPORT" },
		{ "COMPUTER PROGRAM",       "BOOK" },
		{ "AUDIOVISUAL MATERIAL",   "AUDIOVISUAL" },
		{ "ARTWORK",                "BOOK" },
		{ "PATENT",                 "BOOK" },
		{ "BILL",                   "BILL" },
		{ "CASE",                   "CASE" },
		{ "JOURNAL ARTICLE",        "ARTICLE" },
		{ "MAGAZINE ARTICLE",       "ARTICLE" },
		{ "BOOK SECTION",           "INBOOK" },
		{ "EDITED BOOK",            "BOOK" },
		{ "NEWSPAPER ARTICLE",      "NEWSARTICLE" },
		{ "THESIS",                 "PHDTHESIS" },
		{ "PERSONAL COMMUNICATION", "COMMUNICATION" },
		{ "ELECTRONIC SOURCE",      "TEXT" },
		{ "FILM OR BROADCAST",      "AUDIOVISUAL" },
		{ "MAP",                    "MAP" },
		{ "HEARING",                "HEARING" },
		{ "STATUTE",                "STATUTE" },
		{ "CHART OR TABLE",         "CHART" },
		{ "WEB PAGE",               "WEBPAGE" },
	};
	int  ntypes = sizeof( types ) / sizeof( lookups );
	int  i, status, found=0;
	for ( i=0; i<ntypes; ++i ) {
		if ( !strcasecmp( types[i].oldstr, invalue->data ) ) {
			found = 1;
			status = fields_add( bibout, "INTERNAL_TYPE", types[i].newstr, level );
			if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		}
	}
	if ( !found ) {
		fprintf( stderr, "Did not identify reference type '%s'\n", invalue->data );
		fprintf( stderr, "Defaulting to journal article type\n");
		status = fields_add( bibout, "INTERNAL_TYPE", types[0].newstr, level );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	return BIBL_OK;
}

static void
endin_notag( param *p, char *tag, char *data )
{
	if ( p->verbose ) {
		if ( p->progname ) fprintf( stderr, "%s: ", p->progname );
		fprintf( stderr, "Cannot find tag '%s'='%s'\n", tag, data );
	}
}

int
endin_convertf( fields *bibin, fields *bibout, int reftype, param *p )
{
	static int (*convertfns[NUM_REFTYPES])(fields *, newstr *, newstr *, int, param *, char *, fields *) = {
		[ 0 ... NUM_REFTYPES-1 ] = generic_null,
		[ SIMPLE       ] = generic_simple,
		[ TITLE        ] = generic_title,
		[ PERSON       ] = generic_person,
		[ SERIALNO     ] = generic_serialno,
		[ PAGES        ] = generic_pages,
		[ NOTES        ] = generic_notes,
		[ TYPE         ] = endin_type,
		[ DATE         ] = endin_date,
        };

	int i, level, process, nfields, fstatus, status = BIBL_OK;
	char *outtag;
	newstr *intag, *invalue;

	nfields = fields_num( bibin );
	for ( i=0; i<nfields; ++i ) {

		/* Ensure we have data */
		if ( fields_nodata( bibin, i ) ) {
			fields_setused( bibin, i );
			continue;
		}

		intag = fields_tag( bibin, i, FIELDS_STRP );
		invalue = fields_value( bibin, i, FIELDS_STRP );

		/*
		 * Refer format tags start with '%'.  If we have one
		 * that doesn't, assume that it comes from endx2xml
		 * and just copy and paste to output
		 */
		if ( intag->len && intag->data[0]!='%' ) {
			fstatus = fields_add( bibout, intag->data, invalue->data, bibin->level[i] );
			if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
			continue;
		}

		if ( !translate_oldtag( intag->data, reftype, p->all, p->nall, &process, &level, &outtag ) ) {
			endin_notag( p, intag->data, invalue->data );
			continue;
		}

		fields_setused( bibin, i );

		status = convertfns[ process ]( bibin, intag, invalue, level, p, outtag, bibout );
		if ( status!=BIBL_OK ) return status;

	}

	return status;
}
