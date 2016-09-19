/*
 * isiout.c
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
#include "utf8.h"
#include "newstr.h"
#include "strsearch.h"
#include "fields.h"
#include "bibutils.h"
#include "bibformats.h"

static void isiout_write( fields *info, FILE *fp, param *p, unsigned long refnum );
static void isiout_writeheader( FILE *outptr, param *p );

void
isiout_initparams( param *p, const char *progname )
{
	p->writeformat      = BIBL_ISIOUT;
	p->format_opts      = 0;
	p->charsetout       = BIBL_CHARSET_DEFAULT;
	p->charsetout_src   = BIBL_SRC_DEFAULT;
	p->latexout         = 0;
	p->utf8out          = BIBL_CHARSET_UTF8_DEFAULT;
	p->utf8bom          = BIBL_CHARSET_BOM_DEFAULT;
	p->xmlout           = BIBL_XMLOUT_FALSE;
	p->nosplittitle     = 0;
	p->verbose          = 0;
	p->addcount         = 0;
	p->singlerefperfile = 0;

	if ( p->charsetout == BIBL_CHARSET_UNICODE ) {
		p->utf8out = p->utf8bom = 1;
	}

	p->headerf = isiout_writeheader;
	p->footerf = NULL;
	p->writef  = isiout_write;
}

enum {
        TYPE_UNKNOWN = 0,
        TYPE_ARTICLE = 1,
        TYPE_INBOOK  = 2,
        TYPE_BOOK    = 3,
};

static void
output_type( FILE *fp, int type )
{
	fprintf( fp, "PT " );
	if ( type==TYPE_ARTICLE ) fprintf( fp, "Journal" );
	else if ( type==TYPE_INBOOK ) fprintf( fp, "Chapter" );
	else if ( type==TYPE_BOOK ) fprintf( fp, "Book" );
	else fprintf( fp, "Unknown" );
	fprintf( fp, "\n" );
}

static int 
get_type( fields *f )
{
        int type = TYPE_UNKNOWN, i, n, level;
	char *tag, *value;
	n = fields_num( f );
        for ( i=0; i<n; ++i ) {
		tag = fields_tag( f, i, FIELDS_CHRP );
                if ( strcasecmp( tag, "GENRE" ) &&
                     strcasecmp( tag, "NGENRE") ) continue;
		value = fields_value( f, i, FIELDS_CHRP );
		level = fields_level( f, i );
                if ( !strcasecmp( value, "periodical" ) ||
                     !strcasecmp( value, "academic journal" ) ||
		     !strcasecmp( value, "journal article" ) ) {
                        type = TYPE_ARTICLE;
                } else if ( !strcasecmp( value, "book" ) ) {
                        if ( level==0 ) type=TYPE_BOOK;
                        else type=TYPE_INBOOK;
		} else if ( !strcasecmp( value, "book chapter" ) ) {
			type = TYPE_INBOOK;
                }
        }
        return type;
}

static void
output_titlecore( FILE *fp, fields *f, char *isitag, int level,
	char *maintag, char *subtag )
{
	newstr *mainttl = fields_findv( f, level, FIELDS_STRP, maintag );
	newstr *subttl  = fields_findv( f, level, FIELDS_STRP, subtag );

	if ( !mainttl ) return;

	fprintf( fp, "%s %s", isitag, mainttl->data );
	if ( subttl ) {
		if ( mainttl->len > 0 &&
		     mainttl->data[ mainttl->len - 1 ]!='?' )
				fprintf( fp, ":" );
		fprintf( fp, " %s", subttl->data );
	}
	fprintf( fp, "\n" );
}

static void
output_title( FILE *fp, fields *f, char *isitag, int level )
{
	output_titlecore( fp, f, isitag, level, "TITLE", "SUBTITLE" );
}

static void
output_abbrtitle( FILE *fp, fields *f, char *isitag, int level )
{
	output_titlecore( fp, f, isitag, level, "SHORTTITLE", "SHORTSUBTITLE" );
}

static void
output_keywords( FILE *fp, fields *f )
{
	vplist kw;
	int i;
	vplist_init( &kw );
	fields_findv_each( f, LEVEL_ANY, FIELDS_CHRP, &kw, "KEYWORD" );
	if ( kw.n ) {
		fprintf( fp, "DE " );
		for ( i=0; i<kw.n; ++i ) {
			if ( i>0 ) fprintf( fp, "; " );
			fprintf( fp, "%s", (char *)vplist_get( &kw, i ) );
		}
		fprintf( fp, "\n" );
	}
	vplist_free( &kw );
}

static void
output_person( FILE *fp, char *name )
{
	newstr family, given, suffix;
	char *p = name;

	newstrs_init( &family, &given, &suffix, NULL );

	while ( *p && *p!='|' )
		newstr_addchar( &family, *p++ );

	while ( *p=='|' && *(p+1)!='|' ) {
		p++;
		if ( *p!='|' ) newstr_addchar( &given, *p++ );
		while ( *p && *p!='|' ) p++;
	}

	if ( *p=='|' && *(p+1)=='|' ) {
		p += 2;
		while ( *p && *p!='|' ) newstr_addchar( &suffix, *p++ );
	}

	if ( family.len ) fprintf( fp, "%s", family.data );
	if ( suffix.len ) {
		if ( family.len ) fprintf( fp, " %s", suffix.data );
		else fprintf( fp, "%s", suffix.data );
	}
	if ( given.len ) fprintf( fp, ", %s", given.data );

	newstrs_free( &family, &given, &suffix, NULL );
}

static void
output_people( FILE *fp, fields *f, char *tag, char *isitag, int level )
{
	vplist people;
	int i;
	vplist_init( &people );
	fields_findv_each( f, level, FIELDS_CHRP, &people, tag );
	if ( people.n ) {
		fprintf( fp, "%s ", isitag );
		for ( i=0; i<people.n; ++i ) {
			if ( i!=0 ) fprintf( fp, "   " );
			output_person( fp, (char *)vplist_get( &people, i ) );
			fprintf( fp, "\n" );
		}
	}
	vplist_free( &people );
}

static void
output_easy( FILE *fp, fields *f, char *tag, char *isitag, int level )
{
	char *value = fields_findv( f, level, FIELDS_CHRP, tag );
	if ( value ) fprintf( fp, "%s %s\n", isitag, value );
}

static void
output_easyall( FILE *fp, fields *f, char *tag, char *isitag, int level )
{
	vplist a;
	int i;
	vplist_init( &a );
	fields_findv_each( f, level, FIELDS_CHRP, &a, tag );
	for ( i=0; i<a.n; ++i )
		fprintf( fp, "%s %s\n", isitag, (char *) vplist_get( &a, i ) );
	vplist_free( &a );
}

static void
output_date( FILE *fp, fields *f )
{
	char *month = fields_findv_firstof( f, LEVEL_ANY, FIELDS_CHRP,
		"PARTDATE:MONTH", "DATE:MONTH", NULL );
	char *year  = fields_findv_firstof( f, LEVEL_ANY, FIELDS_CHRP,
		"PARTDATE:YEAR", "DATE:YEAR", NULL );
	if ( month ) fprintf( fp, "PD %s\n", month );
	if ( year )  fprintf( fp, "PY %s\n", year );
}

static void
output_verbose( fields *f, unsigned long refnum )
{
	char *tag, *value;
	int i, n, level;
	fprintf( stderr, "REF #%lu----\n", refnum+1 );
	n = fields_num( f );
	for ( i=0; i<n; ++i ) {
		tag   = fields_tag( f, i, FIELDS_CHRP_NOUSE );
		value = fields_value( f, i, FIELDS_CHRP_NOUSE );
		level = fields_level( f, i );
		fprintf( stderr, "\t'%s'\t'%s'\t%d\n",
			tag, value, level );
	}
}

static void
isiout_write( fields *f, FILE *fp, param *p, unsigned long refnum )
{
        int type = get_type( f );

	if ( p->format_opts & BIBL_FORMAT_VERBOSE )
		output_verbose( f, refnum );

        output_type( fp, type );
	output_people( fp, f, "AUTHOR", "AU", 0 );
	output_easyall( fp, f, "AUTHOR:CORP", "AU", 0 );
	output_easyall( fp, f, "AUTHOR:ASIS", "AU", 0 );
/*      output_people( fp, f, "AUTHOR", "A2", 1 );
        output_people( fp, f, "AUTHOR:CORP", "A2", 1 );
        output_people( fp, f, "AUTHOR:ASIS", "A2", 1 );
        output_people( fp, f, "AUTHOR", "A3", 2 );
        output_people( fp, f, "AUTHOR:CORP", "A3", 2 );
        output_people( fp, f, "AUTHOR:ASIS", "A3", 2 );
        output_people( fp, f, "EDITOR", "ED", -1 );
	output_people( fp, f, "EDITOR:CORP", "ED", -1 );
        output_people( fp, f, "EDITOR:ASIS", "ED", -1 );*/

        output_title( fp, f, "TI", 0 );
        if ( type==TYPE_ARTICLE ) {
		output_title( fp, f, "SO", 1 );
		output_abbrtitle( fp, f, "JI", 1 );
		output_title( fp, f, "SE", 2 );
	} else if ( type==TYPE_INBOOK ) {
		output_title( fp, f, "BT", 1 );
		output_title( fp, f, "SE", 2 );
	} else { /* type==BOOK */
		output_title( fp, f, "SE", 1 );
	}

	output_date( fp, f );

	output_easy( fp, f, "PAGES:START",   "BP", -1 );
	output_easy( fp, f, "PAGES:STOP",    "EP", -1 );
        output_easy( fp, f, "ARTICLENUMBER", "AR", -1 );
	output_easy( fp, f, "PAGES:TOTAL",   "PG", -1 );

        output_easy( fp, f, "VOLUME",         "VL", -1 );
        output_easy( fp, f, "ISSUE",          "IS", -1 );
        output_easy( fp, f, "NUMBER",         "IS", -1 );
	output_easy( fp, f, "DOI",            "DI", -1 );
	output_easy( fp, f, "ISIREFNUM",      "UT", -1 );
	output_easy( fp, f, "LANGUAGE",       "LA", -1 );
	output_easy( fp, f, "ISIDELIVERNUM",  "GA", -1 );
	output_keywords( fp, f );
	output_easy( fp, f, "ABSTRACT",       "AB", -1 );
	output_easy( fp, f, "TIMESCITED",     "TC", -1 );
	output_easy( fp, f, "NUMBERREFS",     "NR", -1 );
	output_easy( fp, f, "CITEDREFS",      "CR", -1 );
	output_easy( fp, f, "ADDRESS",        "PI", -1 );

/*        output_easy( fp, f, "PUBLISHER", "PB", -1 );
        output_easy( fp, f, "DEGREEGRANTOR", "PB", -1 );
        output_easy( fp, f, "ADDRESS", "CY", -1 );
        output_easy( fp, f, "ABSTRACT", "AB", -1 );
        output_easy( fp, f, "ISSN", "SN", -1 );
        output_easy( fp, f, "ISBN", "SN", -1 );
        output_easyall( fp, f, "URL", "UR", -1 );
        output_easyall( fp, f, "FILEATTACH", "UR", -1 );
        output_pubmed( fp, f, refnum );
        output_easyall( fp, f, "NOTES", "N1", -1 );
        output_easyall( fp, f, "REFNUM", "ID", -1 );*/
        fprintf( fp, "ER\n\n" );
        fflush( fp );
}

static void
isiout_writeheader( FILE *outptr, param *p )
{
	if ( p->utf8bom ) utf8_writebom( outptr );
}
