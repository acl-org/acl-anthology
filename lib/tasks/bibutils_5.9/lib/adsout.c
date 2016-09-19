/*
 * adsout.c
 *
 * Copyright (c) Richard Mathar 2007-2016
 * Copyright (c) Chris Putnam 2007-2016
 *
 * Program and source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <ctype.h>
#include "utf8.h"
#include "newstr.h"
#include "strsearch.h"
#include "fields.h"
#include "name.h"
#include "bibformats.h"

static void adsout_write( fields *info, FILE *fp, param *p, unsigned long refnum );
static void adsout_writeheader( FILE *outptr, param *p );


void
adsout_initparams( param *p, const char *progname )
{
	p->writeformat      = BIBL_ADSABSOUT;
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

	p->headerf = adsout_writeheader;
	p->footerf = NULL;
	p->writef  = adsout_write;
}

enum {
	TYPE_UNKNOWN = 0,
	TYPE_GENERIC,
	TYPE_ARTICLE,
	TYPE_MAGARTICLE,
	TYPE_BOOK,
	TYPE_INBOOK,
	TYPE_INPROCEEDINGS,
	TYPE_HEARING,
	TYPE_BILL,
	TYPE_CASE,
	TYPE_NEWSPAPER,
	TYPE_COMMUNICATION,
	TYPE_BROADCAST,
	TYPE_MANUSCRIPT,
	TYPE_REPORT,
	TYPE_THESIS,
	TYPE_MASTERSTHESIS,
	TYPE_PHDTHESIS,
	TYPE_DIPLOMATHESIS,
	TYPE_DOCTORALTHESIS,
	TYPE_HABILITATIONTHESIS,
	TYPE_PATENT,
	TYPE_PROGRAM
};

typedef struct match_type {
	char *name;
	int type;
} match_type;

static int
get_type( fields *info )
{
	match_type match_genres[] = {
		{ "academic journal",          TYPE_ARTICLE },
		{ "magazine",                  TYPE_MAGARTICLE },
		{ "conference publication",    TYPE_INPROCEEDINGS },
		{ "hearing",                   TYPE_HEARING },
		{ "Ph.D. thesis",              TYPE_PHDTHESIS },
		{ "Masters thesis",            TYPE_MASTERSTHESIS },
		{ "Diploma thesis",            TYPE_DIPLOMATHESIS },
		{ "Doctoral thesis",           TYPE_DOCTORALTHESIS },
		{ "Habilitation thesis",       TYPE_HABILITATIONTHESIS },
		{ "legislation",               TYPE_BILL },
		{ "newspaper",                 TYPE_NEWSPAPER },
		{ "communication",             TYPE_COMMUNICATION },
		{ "manuscript",                TYPE_MANUSCRIPT },
		{ "report",                    TYPE_REPORT },
		{ "legal case and case notes", TYPE_CASE },
		{ "patent",                    TYPE_PATENT },
	};
	int nmatch_genres = sizeof( match_genres ) / sizeof( match_genres[0] );

	char *tag, *data;
	int i, j, type = TYPE_UNKNOWN;

	for ( i=0; i<info->n; ++i ) {
		tag = info->tag[i].data;
		if ( strcasecmp( tag, "GENRE" )!=0 &&
		     strcasecmp( tag, "NGENRE" )!=0 ) continue;
		data = info->data[i].data;
		for ( j=0; j<nmatch_genres; ++j ) {
			if ( !strcasecmp( data, match_genres[j].name ) ) {
				type = match_genres[j].type;
				fields_setused( info, i );
			}
		}
		if ( type==TYPE_UNKNOWN ) {
			if ( !strcasecmp( data, "periodical" ) )
				type = TYPE_ARTICLE;
			else if ( !strcasecmp( data, "thesis" ) )
				type = TYPE_THESIS;
			else if ( !strcasecmp( data, "book" ) ) {
				if ( info->level[i]==0 ) type = TYPE_BOOK;
				else type = TYPE_INBOOK;
			}
			else if ( !strcasecmp( data, "collection" ) ) {
				if ( info->level[i]==0 ) type = TYPE_BOOK;
				else type = TYPE_INBOOK;
			}
			if ( type!=TYPE_UNKNOWN ) fields_setused( info, i );
		}
	}
	if ( type==TYPE_UNKNOWN ) {
		for ( i=0; i<info->n; ++i ) {
			if ( strcasecmp( info->tag[i].data, "RESOURCE" ) )
				continue;
			data = info->data[i].data;
			if ( !strcasecmp( data, "moving image" ) )
				type = TYPE_BROADCAST;
			else if ( !strcasecmp( data, "software, multimedia" ) )
				type = TYPE_PROGRAM;
			if ( type!=TYPE_UNKNOWN ) fields_setused( info, i );
		}
	}

	/* default to generic */
	if ( type==TYPE_UNKNOWN ) type = TYPE_GENERIC;
	
	return type;
}

static int
output_title( FILE *fp, fields *f, char *full, char *sub, char *adstag, int level )
{
	newstr *fulltitle, *subtitle, *vol, *iss, *sn, *en, *ar;
	int output = 0;

	fulltitle = fields_findv( f, level, FIELDS_STRP, full );
	subtitle  = fields_findv( f, level, FIELDS_STRP, sub );

	if ( fulltitle && fulltitle->len ) {

		output = 1;

		fprintf( fp, "%s %s", adstag, fulltitle->data );
		if ( subtitle && subtitle->len ) {
			if ( fulltitle->data[ fulltitle->len - 1 ] != '?' )
				fprintf( fp, ": " );
			else fprintf( fp, " " );
			fprintf( fp, "%s", subtitle->data );
		}

		vol = fields_findv( f, LEVEL_ANY, FIELDS_STRP, "VOLUME" );
		if ( vol && vol->len ) fprintf( fp, ", vol. %s", vol->data );

		iss = fields_findv_firstof( f, LEVEL_ANY, FIELDS_STRP, "ISSUE",
			"NUMBER", NULL );
		if ( iss && iss->len ) fprintf( fp, ", no. %s", iss->data );

		sn = fields_findv( f, LEVEL_ANY, FIELDS_STRP, "PAGES:START" );
		en = fields_findv( f, LEVEL_ANY, FIELDS_STRP, "PAGES:STOP" );
		ar = fields_findv( f, LEVEL_ANY, FIELDS_STRP, "ARTICLENUMBER" );
		if ( sn && sn->len ) {
			if ( en && en->len )
				fprintf( fp, ", pp." );
			else
				fprintf( fp, ", p." );
			fprintf( fp, " %s", sn->data );
		} else if ( ar && ar->len ) {
			fprintf( fp, ", p. %s", ar->data );
		}
		if ( en && en->len ) {
			fprintf( fp, "-%s", en->data );
		}

		fprintf( fp, "\n" );
	}

	return output;
}

static void
output_people( FILE *fp, fields *f, char *tag1, char *tag2, char *tag3, char *adstag, int level )
{
	newstr oneperson;
	vplist a;
	int i;
	newstr_init( &oneperson );
	vplist_init( &a );
	fields_findv_eachof( f, level, FIELDS_CHRP, &a, tag1, tag2, tag3, NULL );
	extern void  fields_findv_eachof( fields *f, int level, int mode, vplist *a, ... );
	for ( i=0; i<a.n; ++i ) {
		if ( i==0 ) fprintf( fp, "%s ", adstag );
		else fprintf( fp, "; " );
		name_build_withcomma( &oneperson, (char *) vplist_get( &a, i) );
		fprintf( fp, "%s", oneperson.data );
	}
	if ( a.n ) fprintf( fp, "\n" );
	vplist_free( &a );
	newstr_free( &oneperson );
}

static void
output_pages( FILE *fp, fields *f )
{
	newstr *sn = fields_findv( f, LEVEL_ANY, FIELDS_STRP, "PAGES:START" );
	newstr *en = fields_findv( f, LEVEL_ANY, FIELDS_STRP, "PAGES:STOP" );
	newstr *ar = fields_findv( f, LEVEL_ANY, FIELDS_STRP, "ARTICLENUMBER" );
	if ( sn && sn->len!=0 ) fprintf( fp, "%%P %s\n", sn->data );
	else if ( ar && ar->len!=0 ) fprintf( fp, "%%P %s\n", ar->data );
	if ( en && en->len!=0 ) fprintf( fp, "%%L %s\n", en->data );
}

static int
mont2mont( const char *m )
{
	static char *monNames[]= { "jan", "feb", "mar", "apr", "may", 
			"jun", "jul", "aug", "sep", "oct", "nov", "dec" };
	int i;
	if ( isdigit( (unsigned char)m[0] ) ) return atoi( m );
        else {
		for ( i=0; i<12; i++ ) {
			if ( !strncasecmp( m, monNames[i], 3 ) ) return i+1;
		}
	}
        return 0;
}

static int
get_month( fields *f, int level )
{
	newstr *month = fields_findv_firstof( f, level, FIELDS_STRP,
			"DATE:MONTH", "PARTDATE:MONTH", NULL );
	if ( month && month->len ) return mont2mont( month->data );
	else return 0;
}

static void
output_date( FILE *fp, fields *f, char *adstag, int level )
{
	newstr *year = fields_findv_firstof( f, level, FIELDS_STRP,
		"DATE:YEAR", "PARTDATE:YEAR", NULL );
	int month;
	if ( year && year->len ) {
		month = get_month( f, level );
		fprintf( fp, "%s %02d/%s\n", adstag, month, year->data );
	}
}

#include "adsout_journals.c"

static void
output_4digit_value( char *pos, long long n )
{
	char buf[6];
	n = n % 10000; /* truncate to 0->9999, will fit in buf[6] */
#ifdef WIN32
	sprintf( buf, "%I64d", n );
#else
	sprintf( buf, "%lld", n );
#endif
	if ( n < 10 )        strncpy( pos+3, buf, 1 );
	else if ( n < 100 )  strncpy( pos+2, buf, 2 );
	else if ( n < 1000 ) strncpy( pos+1, buf, 3 );
	else                 strncpy( pos,   buf, 4 );
}

static char
get_firstinitial( fields *f )
{
	char *name;
	int n;

	n = fields_find( f, "AUTHOR", LEVEL_MAIN );
	if ( n==-1 ) n = fields_find( f, "AUTHOR", LEVEL_ANY );

	if ( n!=-1 ) {
		name = fields_value( f, n, FIELDS_CHRP );
		return name[0];
	} else return '\0';
}

static int
get_journalabbr( fields *f )
{
	char *jrnl;
	int n, j;

	n = fields_find( f, "TITLE", LEVEL_HOST );
	if ( n!=-1 ) {
		jrnl = fields_value( f, n, FIELDS_CHRP );
		for ( j=0; j<njournals; j++ ) {
			if ( !strcasecmp( jrnl, journals[j]+6 ) )
				return j;
		}
	}
	return -1;
}

static void
output_Rtag( FILE *fp, fields *f, char *adstag, int type )
{
	char out[20], ch;
	int n, i;
	long long page;

	strcpy( out, "..................." );

	/** YYYY */
	n = fields_find( f, "DATE:YEAR", LEVEL_ANY );
	if ( n==-1 ) n = fields_find( f, "PARTDATE:YEAR", LEVEL_ANY );
	if ( n!=-1 ) output_4digit_value( out, atoi( fields_value( f, n, FIELDS_CHRP ) ) );

	/** JJJJ */
	n = get_journalabbr( f );
	if ( n!=-1 ) {
		i = 0;
		while ( i<5 && journals[n][i]!=' ' && journals[n][i]!='\t' ) {
			out[4+i] = journals[n][i];
			i++;
		}
	}

	/** VVVV */
	n = fields_find( f, "VOLUME", LEVEL_ANY );
	if ( n!=-1 ) output_4digit_value( out+9, atoi( fields_value( f, n, FIELDS_CHRP ) ) );

	/** MPPPP */
	n = fields_find( f, "PAGES:START", LEVEL_ANY );
	if ( n==-1 ) n = fields_find( f, "ARTICLENUMBER", LEVEL_ANY );
	if ( n!=-1 ) {
		page = atoll( fields_value( f, n, FIELDS_CHRP ) );
		output_4digit_value( out+14, page );
		if ( page>=10000 ) {
			ch = 'a' + (page/10000);
			out[13] = ch;
		}
	}

	/** A */
        ch = toupper( (unsigned char) get_firstinitial( f ) );
	if ( ch!='\0' ) out[18] = ch;

	fprintf( fp, "%s %s\n", adstag, out );
}

static void
output_easyall( FILE *fp, fields *f, char *tag, char *adstag, char *prefix, int level )
{
	vplist a;
	int i;
	vplist_init( &a );
	fields_findv_each( f, level, FIELDS_CHRP, &a, tag );
	for ( i=0; i<a.n; ++i )
		fprintf( fp, "%s %s%s\n", adstag, prefix, (char *) vplist_get( &a, i ) );
	vplist_free( &a );
}

static void
output_easy( FILE *fp, fields *f, char *tag, char *adstag, int level )
{
	char *value = fields_findv( f, level, FIELDS_CHRP, tag );
	if ( value && value[0]!='\0' ) fprintf( fp, "%s %s\n", adstag, value );
}

static void
output_keys( FILE *fp, fields *f, char *tag, char *adstag, int level )
{
	vplist a;
	int i;
	vplist_init( &a );
	fields_findv_each( f, level, FIELDS_CHRP, &a, tag );
	for ( i=0; i<a.n; ++i ) {
		if ( i==0 ) fprintf( fp, "%s ", adstag );
		else fprintf( fp, ", " );
		fprintf( fp, "%s", (char *) vplist_get( &a, i ) );
	}
	if ( a.n ) fprintf( fp, "\n" );
	vplist_free( &a );
}

static void
adsout_write( fields *f, FILE *fp, param *p, unsigned long refnum )
{
	int type, status;
	fields_clearused( f );
	type = get_type( f );

	output_people(  fp, f, "AUTHOR", "AUTHOR:ASIS", "AUTHOR:CORP", "%A", LEVEL_MAIN );
	output_people(  fp, f, "EDITOR", "EDITOR:ASIS", "EDITOR:CORP", "%E", LEVEL_ANY );
	output_easy(    fp, f, "TITLE",       "%T", LEVEL_ANY );

	if ( type==TYPE_ARTICLE || type==TYPE_MAGARTICLE ) {
		status = output_title( fp, f, "TITLE", "SUBTITLE", "%J", LEVEL_HOST );
		if ( status==0 )
			(void) output_title( fp, f, "SHORTTITLE", "SHORTSUBTITLE", "%J", LEVEL_HOST );
	}

	output_date(    fp, f,               "%D", LEVEL_ANY );
	output_easy(    fp, f, "VOLUME",     "%V", LEVEL_ANY );
	output_easy(    fp, f, "ISSUE",      "%N", LEVEL_ANY );
	output_easy(    fp, f, "NUMBER",     "%N", LEVEL_ANY );
	output_easy(    fp, f, "LANGUAGE",   "%M", LEVEL_ANY );
	output_easyall( fp, f, "NOTES",      "%X", "", LEVEL_ANY );
	output_easy(    fp, f, "ABSTRACT",   "%B", LEVEL_ANY );
	output_keys(    fp, f, "KEYWORD",    "%K", LEVEL_ANY );
	output_easyall( fp, f, "URL",        "%U", "", LEVEL_ANY );
	output_easyall( fp, f, "ARXIV",      "%U", "http://arxiv.org/abs/", LEVEL_ANY );
	output_easyall( fp, f, "JSTOR",      "%U", "http://www.jstor.org/stable/", LEVEL_ANY );
	output_easyall( fp, f, "PMID",       "%U", "http://www.ncbi.nlm.nih.gov/pubmed/", LEVEL_ANY );
	output_easyall( fp, f, "PMC",        "%U", "http://www.ncbi.nlm.nih.gov/pmc/articles/", LEVEL_ANY );
	output_easyall( fp, f, "FILEATTACH", "%U", "", LEVEL_ANY );
	output_easyall( fp, f, "FIGATTACH",  "%U", "", LEVEL_ANY );
	output_pages( fp, f );
	output_easyall( fp, f, "DOI",        "%Y", "", LEVEL_ANY );
        fprintf( fp, "%%W PHY\n%%G AUTHOR\n" );
	output_Rtag( fp, f, "%R", type );
	fprintf( fp, "\n" );
	fflush( fp );
}

static void
adsout_writeheader( FILE *outptr, param *p )
{
	if ( p->utf8bom ) utf8_writebom( outptr );
}

