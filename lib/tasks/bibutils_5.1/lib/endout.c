/*
 * endout.c
 *
 * Copyright (c) Chris Putnam 2004-2013
 *
 * Program and source code released under the GPL version 2
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
#include "doi.h"
#include "name.h"
#include "endout.h"

void
endout_initparams( param *p, const char *progname )
{
	p->writeformat      = BIBL_ENDNOTEOUT;
	p->format_opts      = 0;
	p->charsetout       = BIBL_CHARSET_DEFAULT;
	p->charsetout_src   = BIBL_SRC_DEFAULT;
	p->latexout         = 0;
	p->utf8out          = BIBL_CHARSET_UTF8_DEFAULT;
	p->utf8bom          = BIBL_CHARSET_BOM_DEFAULT;
	p->xmlout           = 0;
	p->nosplittitle     = 0;
	p->verbose          = 0;
	p->addcount         = 0;
	p->singlerefperfile = 0;

	if ( p->charsetout == BIBL_CHARSET_UNICODE ) {
		p->utf8out = p->utf8bom = 1;
	}

	p->headerf = endout_writeheader;
	p->footerf = NULL;
	p->writef  = endout_write;
}

enum {
	TYPE_UNKNOWN = 0,
	TYPE_GENERIC,                     /* Generic */
	TYPE_ARTWORK,                     /* Artwork */
	TYPE_AUDIOVISUAL,                 /* Audiovisual Material */
	TYPE_BILL,                        /* Bill */
	TYPE_BOOK,                        /* Book */
	TYPE_INBOOK,                      /* Book Section */
	TYPE_CASE,                        /* Case */
	TYPE_CHARTTABLE,                  /* Chart or Table */
	TYPE_CLASSICALWORK,               /* Classical Work */
	TYPE_PROGRAM,                     /* Computer Program */
	TYPE_INPROCEEDINGS,               /* Conference Paper */
	TYPE_PROCEEDINGS,                 /* Conference Proceedings */
	TYPE_EDITEDBOOK,                  /* Edited Book */
	TYPE_EQUATION,                    /* Equation */
	TYPE_ELECTRONICARTICLE,           /* Electronic Article */
	TYPE_ELECTRONICBOOK,              /* Electronic Book */
	TYPE_ELECTRONIC,                  /* Electronic Source */
	TYPE_FIGURE,                      /* Figure */
	TYPE_FILMBROADCAST,               /* Film or Broadcast */
	TYPE_GOVERNMENT,                  /* Government Document */
	TYPE_HEARING,                     /* Hearing */
	TYPE_ARTICLE,                     /* Journal Article */
	TYPE_LEGALRULE,                   /* Legal Rule/Regulation */
	TYPE_MAGARTICLE,                  /* Magazine Article */
	TYPE_MANUSCRIPT,                  /* Manuscript */
	TYPE_MAP,                         /* Map */
	TYPE_NEWSARTICLE,                 /* Newspaper Article */
	TYPE_ONLINEDATABASE,              /* Online Database */
	TYPE_ONLINEMULTIMEDIA,            /* Online Multimedia */
	TYPE_PATENT,                      /* Patent */
	TYPE_COMMUNICATION,               /* Personal Communication */
	TYPE_REPORT,                      /* Report */
	TYPE_STATUTE,                     /* Statute */
	TYPE_THESIS,                      /* Thesis */
	TYPE_MASTERSTHESIS,               /* Thesis */
	TYPE_PHDTHESIS,                   /* Thesis */
	TYPE_DIPLOMATHESIS,               /* Thesis */
	TYPE_DOCTORALTHESIS,              /* Thesis */
	TYPE_HABILITATIONTHESIS,          /* Thesis */
	TYPE_UNPUBLISHED,                 /* Unpublished Work */
};

typedef struct match_type {
	char *name;
	int type;
} match_type;

static int
get_type( fields *info )
{
	/* Comment out TYPE_GENERIC entries as that is default, but
         * keep in source as record of mapping decision. */
	match_type match_genres[] = {
		/* MARC Authority elements */
		{ "art original",              TYPE_ARTWORK },
		{ "art reproduction",          TYPE_ARTWORK },
		{ "article",                   TYPE_ARTICLE },
		{ "atlas",                     TYPE_MAP },
		{ "autobiography",             TYPE_BOOK },
/*		{ "bibliography",              TYPE_GENERIC },*/
		{ "biography",                 TYPE_BOOK },
		{ "book",                      TYPE_BOOK },
/*		{ "catalog",                   TYPE_GENERIC },*/
		{ "chart",                     TYPE_CHARTTABLE },
/*		{ "comic strip",               TYPE_GENERIC },*/
		{ "conference publication",    TYPE_PROCEEDINGS },
		{ "database",                  TYPE_ONLINEDATABASE },
/*		{ "dictionary",                TYPE_GENERIC },*/
		{ "diorama",                   TYPE_ARTWORK },
/*		{ "directory",                 TYPE_GENERIC },*/
		{ "discography",               TYPE_AUDIOVISUAL },
/*		{ "drama",                     TYPE_GENERIC },*/
		{ "encyclopedia",              TYPE_BOOK },
/*		{ "essay",                     TYPE_GENERIC }, */
/*		{ "festschrift",               TYPE_GENERIC },*/
		{ "fiction",                   TYPE_BOOK },
		{ "filmography",               TYPE_FILMBROADCAST },
		{ "filmstrip",                 TYPE_FILMBROADCAST },
/*		{ "finding aid",               TYPE_GENERIC },*/
/*		{ "flash card",                TYPE_GENERIC },*/
		{ "folktale",                  TYPE_CLASSICALWORK },
		{ "font",                      TYPE_ELECTRONIC },
/*		{ "game",                      TYPE_GENERIC },*/
		{ "government publication",    TYPE_GOVERNMENT },
		{ "graphic",                   TYPE_FIGURE },
		{ "globe",                     TYPE_MAP },
/*		{ "handbook",                  TYPE_GENERIC },*/
		{ "history",                   TYPE_BOOK },
		{ "hymnal",                    TYPE_BOOK },
/*		{ "humor, satire",             TYPE_GENERIC },*/
/*		{ "index",                     TYPE_GENERIC },*/
/*		{ "instruction",               TYPE_GENERIC },*/
/*		{ "interview",                 TYPE_GENERIC },*/
		{ "issue",                     TYPE_ARTICLE },
		{ "journal",                   TYPE_ARTICLE },
/*		{ "kit",                       TYPE_GENERIC },*/
/*		{ "language instruction",      TYPE_GENERIC },*/
/*		{ "law report or digest",      TYPE_GENERIC },*/
/*		{ "legal article",             TYPE_GENERIC },*/
		{ "legal case and case notes", TYPE_CASE },
		{ "legislation",               TYPE_BILL },
		{ "letter",                    TYPE_COMMUNICATION },
		{ "loose-leaf",                TYPE_GENERIC },
		{ "map",                       TYPE_MAP },
/*		{ "memoir",                    TYPE_GENERIC },*/
/*		{ "microscope slide",          TYPE_GENERIC },*/
/*		{ "model",                     TYPE_GENERIC },*/
		{ "motion picture",            TYPE_AUDIOVISUAL },
		{ "multivolume monograph",     TYPE_BOOK },
		{ "newspaper",                 TYPE_NEWSARTICLE },
		{ "novel",                     TYPE_BOOK },
/*		{ "numeric data",              TYPE_GENERIC },*/
/*		{ "offprint",                  TYPE_GENERIC },*/
		{ "online system or service",  TYPE_ELECTRONIC },
		{ "patent",                    TYPE_PATENT },
		{ "periodical",                TYPE_MAGARTICLE },
		{ "picture",                   TYPE_ARTWORK },
/*		{ "poetry",                    TYPE_GENERIC },*/
		{ "programmed text",           TYPE_PROGRAM },
/*		{ "realia",                    TYPE_GENERIC },*/
		{ "rehearsal",                 TYPE_AUDIOVISUAL },
/*		{ "remote sensing image",      TYPE_GENERIC },*/
/*		{ "reporting",                 TYPE_GENERIC },*/
/*		{ "review",                    TYPE_GENERIC },*/
/*		{ "script",                    TYPE_GENERIC },*/
/*		{ "series",                    TYPE_GENERIC },*/
/*		{ "short story",               TYPE_GENERIC },*/
/*		{ "slide",                     TYPE_GENERIC },*/
		{ "sound",                     TYPE_AUDIOVISUAL },
/*		{ "speech",                    TYPE_GENERIC },*/
/*		{ "statistics",                TYPE_GENERIC },*/
/*		{ "survey of literature",      TYPE_GENERIC },*/
		{ "technical drawing",         TYPE_ARTWORK },
		{ "techincal report",          TYPE_REPORT },
		{ "thesis",                    TYPE_THESIS },
/*		{ "toy",                       TYPE_GENERIC },*/
/*		{ "transparency",              TYPE_GENERIC },*/
/*		{ "treaty",                    TYPE_GENERIC },*/
		{ "videorecording",            TYPE_AUDIOVISUAL },
		{ "web site",                  TYPE_ELECTRONIC },
		/* Non-MARC Authority elements */
		{ "academic journal",          TYPE_ARTICLE },
		{ "magazine",                  TYPE_MAGARTICLE },
		{ "hearing",                   TYPE_HEARING },
		{ "Ph.D. thesis",              TYPE_PHDTHESIS },
		{ "Masters thesis",            TYPE_MASTERSTHESIS },
		{ "Diploma thesis",            TYPE_DIPLOMATHESIS },
		{ "Doctoral thesis",           TYPE_DOCTORALTHESIS },
		{ "Habilitation thesis",       TYPE_HABILITATIONTHESIS },
		{ "communication",             TYPE_COMMUNICATION },
		{ "manuscript",                TYPE_MANUSCRIPT },
		{ "report",                    TYPE_REPORT },
		{ "unpublished",               TYPE_UNPUBLISHED },
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
		/* the inbook type should be defined if 'book' in host */
		if ( type==TYPE_BOOK && info->level[i]!=0 ) type = TYPE_INBOOK;
		/* the article types should be defined if it's the host */
		if ( ( type==TYPE_ARTICLE || type==TYPE_MAGARTICLE || type==TYPE_NEWSARTICLE ) && info->level[i]<1 ) type=TYPE_UNKNOWN;
	}
	if ( type==TYPE_UNKNOWN ) {
		for ( i=0; i<info->n; ++i ) {
			if ( strcasecmp( info->tag[i].data, "RESOURCE" ) )
				continue;
			data = info->data[i].data;
			if ( !strcasecmp( data, "moving image" ) )
				type = TYPE_FILMBROADCAST;
			else if ( !strcasecmp( data, "software, multimedia" ) )
				type = TYPE_PROGRAM;
			if ( type!=TYPE_UNKNOWN ) fields_setused( info, i );
		}
	}

	/* default to generic */
	if ( type==TYPE_UNKNOWN ) type = TYPE_GENERIC;
	
	return type;
}

static void
output_type( FILE *fp, int type, param *p )
{
	/* These are restricted to Endnote-defined types */
	match_type genrenames[] = {
		{ "Generic",                TYPE_GENERIC },
		{ "Artwork",                TYPE_ARTWORK },
		{ "Audiovisual Material",   TYPE_AUDIOVISUAL },
		{ "Bill",                   TYPE_BILL },
		{ "Book",                   TYPE_BOOK },
		{ "Book Section",           TYPE_INBOOK },
		{ "Case",                   TYPE_CASE },
		{ "Chart or Table",         TYPE_CHARTTABLE },
		{ "Classical Work",         TYPE_CLASSICALWORK },
		{ "Computer Program",       TYPE_PROGRAM },
		{ "Conference Paper",       TYPE_INPROCEEDINGS },
		{ "Conference Proceedings", TYPE_PROCEEDINGS },
		{ "Edited Book",            TYPE_EDITEDBOOK },
		{ "Equation",               TYPE_EQUATION },
		{ "Electronic Article",     TYPE_ELECTRONICARTICLE },
		{ "Electronic Book",        TYPE_ELECTRONICBOOK },
		{ "Electronic Source",      TYPE_ELECTRONIC },
		{ "Figure",                 TYPE_FIGURE },
		{ "Film or Broadcast",      TYPE_FILMBROADCAST },
		{ "Government Document",    TYPE_GOVERNMENT },
		{ "Hearing",                TYPE_HEARING },
		{ "Journal Article",        TYPE_ARTICLE },
		{ "Legal Rule/Regulation",  TYPE_LEGALRULE },
		{ "Magazine Article",       TYPE_MAGARTICLE },
		{ "Manuscript",             TYPE_MANUSCRIPT },
		{ "Map",                    TYPE_MAP },
		{ "Newspaper Article",      TYPE_NEWSARTICLE },
		{ "Online Database",        TYPE_ONLINEDATABASE },
		{ "Online Multimedia",      TYPE_ONLINEMULTIMEDIA },
		{ "Patent",                 TYPE_PATENT },
		{ "Personal Communication", TYPE_COMMUNICATION },
		{ "Report",                 TYPE_REPORT },
		{ "Statute",                TYPE_STATUTE },
		{ "Thesis",                 TYPE_THESIS }, 
		{ "Thesis",                 TYPE_PHDTHESIS },
		{ "Thesis",                 TYPE_MASTERSTHESIS },
		{ "Thesis",                 TYPE_DIPLOMATHESIS },
		{ "Thesis",                 TYPE_DOCTORALTHESIS },
		{ "Thesis",                 TYPE_HABILITATIONTHESIS },
		{ "Unpublished Work",       TYPE_UNPUBLISHED },
	};
	int ngenrenames = sizeof( genrenames ) / sizeof( genrenames[0] );
	int i, found = 0;
	fprintf( fp, "%%0 ");
	for ( i=0; i<ngenrenames && !found; ++i ) {
		if ( genrenames[i].type == type ) {
			fprintf( fp, "%s", genrenames[i].name );
			found = 1;
		}
	}
	if ( !found ) {
		fprintf( fp, "Generic" );
		if ( p->progname ) fprintf( stderr, "%s: ", p->progname );
		fprintf( stderr, "Cannot identify type %d\n", type );
	}
	fprintf( fp, "\n" );
}

static void
output_title( FILE *fp, fields *info, char *full, char *sub, char *endtag, 
		int level )
{
	newstr *mainttl = fields_findv( info, level, FIELDS_STRP, full );
	newstr *subttl  = fields_findv( info, level, FIELDS_STRP, sub );

	if ( !mainttl ) return;

	fprintf( fp, "%s %s", endtag, mainttl->data );
	if ( subttl ) {
		if ( mainttl->len > 0 &&
		     mainttl->data[ mainttl->len-1 ]!='?' )
				fprintf( fp, ":" );
		fprintf( fp, " %s", subttl->data );
	}
	fprintf( fp, "\n" );
}

static void
output_people( FILE *fp, fields *info, char *tag, char *entag, int level )
{
	newstr oneperson;
	int i, n, flvl;
	char *ftag;
	newstr_init( &oneperson );
	n = fields_num( info );
	for ( i=0; i<n; ++i ) {
		flvl = fields_level( info, i );
		if ( level!=LEVEL_ANY && flvl!=level ) continue;
		ftag = fields_tag( info, i, FIELDS_CHRP );
		if ( !strcasecmp( ftag, tag ) ) {
			name_build_withcomma( &oneperson, fields_value( info, i, FIELDS_CHRP ) );
			fprintf( fp, "%s %s\n", entag, oneperson.data );
		}
	}
	newstr_free( &oneperson );
}

static void
output_pages( FILE *fp, fields *info )
{
	char *sn = fields_findv( info, LEVEL_ANY, FIELDS_CHRP, "PAGESTART" );
	char *en = fields_findv( info, LEVEL_ANY, FIELDS_CHRP, "PAGEEND" );
	char *ar;
	if ( sn || en ) {
		fprintf( fp, "%%P ");
		if ( sn ) fprintf( fp, "%s", sn );
		if ( sn && en ) fprintf( fp, "-" );
		if ( en ) fprintf( fp, "%s", en );
		fprintf( fp, "\n" );
	} else {
		ar = fields_findv( info, LEVEL_ANY, FIELDS_CHRP, "ARTICLENUMBER" );
		if ( ar ) fprintf( fp, "%%P %s\n", ar );
	}
}

static void
output_doi( FILE *fp, fields *f )
{
	newstr doi_url;
	int i, n;

	newstr_init( &doi_url );

	n = fields_num( f );
	for ( i=0; i<n; ++i ) {
		if ( !fields_match_tag( f, i, "DOI" ) ) continue;
		doi_to_url( f, i, "URL", &doi_url );
		if ( doi_url.len )
			fprintf( fp, "%%U %s\n", doi_url.data );
	}

	newstr_free( &doi_url );
}

static void
output_pmid( FILE *fp, fields *f )
{
	newstr pmid_url;
	int i, n;

	newstr_init( &pmid_url );

	n = fields_num( f );
	for ( i=0; i<n; ++i ) {
		if ( !fields_match_tag( f, i, "PMID" ) ) continue;
		pmid_to_url( f, i, "URL", &pmid_url );
		if ( pmid_url.len )
			fprintf( fp, "%%U %s\n", pmid_url.data );
	}

	newstr_free( &pmid_url );
}

static void
output_arxiv( FILE *fp, fields *f )
{
	newstr arxiv_url;
	int i, n;

	newstr_init( &arxiv_url );

	n = fields_num( f );
	for ( i=0; i<n; ++i ) {
		if ( !fields_match_tag( f, i, "ARXIV" ) ) continue;
		arxiv_to_url( f, i, "URL", &arxiv_url );
		if ( arxiv_url.len )
			fprintf( fp, "%%U %s\n", arxiv_url.data );
	}

	newstr_free( &arxiv_url );
}

static void
output_jstor( FILE *fp, fields *f )
{
	newstr jstor_url;
	int i, n;

	newstr_init( &jstor_url );

	n = fields_num( f );
	for ( i=0; i<n; ++i ) {
		if ( !fields_match_tag( f, i, "JSTOR" ) ) continue;
		jstor_to_url( f, i, "URL", &jstor_url );
		if ( jstor_url.len )
			fprintf( fp, "%%U %s\n", jstor_url.data );
	}

	newstr_free( &jstor_url );
}

static void
output_year( FILE *fp, fields *info, int level )
{
	char *year = fields_findv_firstof( info, level, FIELDS_CHRP,
			"YEAR", "PARTYEAR", NULL );
	if ( year )
		fprintf( fp, "%%D %s\n", year );
}

static void
output_monthday( FILE *fp, fields *info, int level )
{
	char *months[12] = { "January", "February", "March", "April",
		"May", "June", "July", "August", "September", "October",
		"November", "December" };
	int m;
	char *month = fields_findv_firstof( info, level, FIELDS_CHRP,
			"MONTH", "PARTMONTH", NULL );
	char *day   = fields_findv_firstof( info, level, FIELDS_CHRP,
			"DAY", "PARTDAY", NULL );
	if ( month || day ) {
		fprintf( fp, "%%8 " );
		if ( month ) {
			m = atoi( month );
			if ( m>0 && m<13 ) fprintf( fp, "%s", months[m-1] );
			else fprintf( fp, "%s", month );
		}
		if ( month && day ) fprintf( fp, " " );
		if ( day ) fprintf( fp, "%s", day );
		fprintf( fp, "\n" );
	}
}

static void
output_thesishint( FILE *fp, int type )
{
	if ( type==TYPE_MASTERSTHESIS )
		fprintf( fp, "%%9 Masters thesis\n" );
	else if ( type==TYPE_PHDTHESIS )
		fprintf( fp, "%%9 Ph.D. thesis\n" );
	else if ( type==TYPE_DIPLOMATHESIS )
		fprintf( fp, "%%9 Diploma thesis\n" );
	else if ( type==TYPE_DOCTORALTHESIS )
		fprintf( fp, "%%9 Doctoral thesis\n" );
	else if ( type==TYPE_HABILITATIONTHESIS )
		fprintf( fp, "%%9 Habilitation thesis\n" );
}

static void
output_easyall( FILE *fp, fields *info, char *tag, char *entag, int level )
{
	vplist a;
	int i;
	vplist_init( &a );
	fields_findv_each( info, level, FIELDS_CHRP, &a, tag );
	for ( i=0; i<a.n; ++i )
		fprintf( fp, "%s %s\n", entag, (char *) vplist_get( &a, i ) );
	vplist_free( &a );
}

static void
output_easy( FILE *fp, fields *info, char *tag, char *entag, int level )
{
	char *value = fields_findv( info, level, FIELDS_CHRP, tag );
	if ( value ) fprintf( fp, "%s %s\n", entag, value );
}

void
endout_write( fields *info, FILE *fp, param *p, unsigned long refnum )
{
	int type;

	fields_clearused( info );

	type = get_type( info );

	output_type( fp, type, p );

	output_title( fp, info, "TITLE",      "SUBTITLE",      "%T", LEVEL_MAIN );
	output_title( fp, info, "SHORTTITLE", "SHORTSUBTITLE", "%!", LEVEL_MAIN );

	output_people( fp, info, "AUTHOR",     "%A", LEVEL_MAIN );
	output_people( fp, info, "EDITOR",     "%E", LEVEL_MAIN );
	if ( type==TYPE_ARTICLE || type==TYPE_MAGARTICLE || type==TYPE_ELECTRONICARTICLE || type==TYPE_NEWSARTICLE )
		output_people( fp, info, "EDITOR", "%E", LEVEL_HOST );
	else if ( type==TYPE_INBOOK || type==TYPE_INPROCEEDINGS ) {
		output_people( fp, info, "EDITOR", "%E", LEVEL_HOST );
	} else {
		output_people( fp, info, "EDITOR", "%Y", LEVEL_HOST );
	}
	output_people( fp, info, "TRANSLATOR", "%H", LEVEL_ANY  );

	output_people( fp, info, "AUTHOR",     "%Y", LEVEL_SERIES );
	output_people( fp, info, "EDITOR",     "%Y", LEVEL_SERIES );

	if ( type==TYPE_CASE )
		output_easy(    fp, info, "AUTHOR:CORP", "%I", LEVEL_MAIN );
	else if ( type==TYPE_HEARING )
		output_easyall( fp, info, "AUTHOR:CORP", "%S", LEVEL_MAIN );
	else if ( type==TYPE_NEWSARTICLE )
		output_people(  fp, info, "REPORTER",    "%A", LEVEL_MAIN );
	else if ( type==TYPE_COMMUNICATION )
		output_people(  fp, info, "RECIPIENT",   "%E", LEVEL_ANY  );
	else {
		output_easyall( fp, info, "AUTHOR:CORP",     "%A", LEVEL_MAIN );
		output_easyall( fp, info, "AUTHOR:ASIS",     "%A", LEVEL_MAIN );
		output_easyall( fp, info, "EDITOR:CORP",     "%E", LEVEL_ANY  );
		output_easyall( fp, info, "EDITOR:ASIS",     "%E", LEVEL_ANY  );
		output_easyall( fp, info, "TRANSLATOR:CORP", "%H", LEVEL_ANY  );
		output_easyall( fp, info, "TRANSLATOR:ASIS", "%H", LEVEL_ANY  );
	}

	if ( type==TYPE_ARTICLE || type==TYPE_MAGARTICLE || type==TYPE_ELECTRONICARTICLE || type==TYPE_NEWSARTICLE )
		output_title( fp, info, "TITLE", "SUBTITLE", "%J", LEVEL_HOST );
	else if ( type==TYPE_INBOOK || type==TYPE_INPROCEEDINGS ) {
		output_title( fp, info, "TITLE", "SUBTITLE", "%B", LEVEL_HOST );
	} else {
		output_title( fp, info, "TITLE", "SUBTITLE", "%S", LEVEL_HOST );
	}

	if ( type!=TYPE_CASE && type!=TYPE_HEARING ) {
		output_title( fp, info, "TITLE", "SUBTITLE", "%S", LEVEL_SERIES );
	}

	output_year( fp, info, LEVEL_ANY );
	output_monthday( fp, info, LEVEL_ANY );

	output_easy( fp, info, "VOLUME",             "%V", LEVEL_ANY );
	output_easy( fp, info, "ISSUE",              "%N", LEVEL_ANY );
	output_easy( fp, info, "NUMBER",             "%N", LEVEL_ANY );
	output_easy( fp, info, "EDITION",            "%7", LEVEL_ANY );
	output_easy( fp, info, "PUBLISHER",          "%I", LEVEL_ANY );
	output_easy( fp, info, "ADDRESS",            "%C", LEVEL_ANY );
	output_easy( fp, info, "DEGREEGRANTOR",      "%C", LEVEL_ANY );
	output_easy( fp, info, "DEGREEGRANTOR:CORP", "%C", LEVEL_ANY );
	output_easy( fp, info, "DEGREEGRANTOR:ASIS", "%C", LEVEL_ANY );
	output_easy( fp, info, "SERIALNUMBER",       "%@", LEVEL_ANY );
	output_easy( fp, info, "ISSN",               "%@", LEVEL_ANY );
	output_easy( fp, info, "ISBN",               "%@", LEVEL_ANY );
	output_easy( fp, info, "LANGUAGE",           "%G", LEVEL_ANY );
	output_easy( fp, info, "REFNUM",             "%F", LEVEL_ANY );
	output_easyall( fp, info, "NOTES",           "%O", LEVEL_ANY );
	output_easy( fp, info, "ABSTRACT",           "%X", LEVEL_ANY );
	output_easy( fp, info, "CLASSIFICATION",     "%L", LEVEL_ANY );
	output_easyall( fp, info, "KEYWORD",         "%K", LEVEL_ANY );
	output_easyall( fp, info, "NGENRE",          "%9", LEVEL_ANY );
	output_thesishint( fp, type );
	output_easyall( fp, info, "URL",             "%U", LEVEL_ANY ); 
	output_easyall( fp, info, "FILEATTACH",      "%U", LEVEL_ANY ); 
	output_doi( fp, info );
	output_pmid( fp, info );
	output_arxiv( fp, info );
	output_jstor( fp, info );
	output_pages( fp, info );
	fprintf( fp, "\n" );
	fflush( fp );
}

void
endout_writeheader( FILE *outptr, param *p )
{
	if ( p->utf8bom ) utf8_writebom( outptr );
}

