/*
 * bibtexout.c
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
#include "newstr.h"
#include "strsearch.h"
#include "utf8.h"
#include "xml.h"
#include "fields.h"
#include "name.h"
#include "bibl.h"
#include "doi.h"
#include "bibformats.h"

static void bibtexout_write( fields *info, FILE *fp, param *p, unsigned long refnum );
static void bibtexout_writeheader( FILE *outptr, param *p );

void
bibtexout_initparams( param *p, const char *progname )
{
	p->writeformat      = BIBL_BIBTEXOUT;
	p->format_opts      = 0;
	p->charsetout       = BIBL_CHARSET_DEFAULT;
	p->charsetout_src   = BIBL_SRC_DEFAULT;
	p->latexout         = 1;
	p->utf8out          = BIBL_CHARSET_UTF8_DEFAULT;
	p->utf8bom          = BIBL_CHARSET_BOM_DEFAULT;
	p->xmlout           = BIBL_XMLOUT_FALSE;
	p->nosplittitle     = 0;
	p->verbose          = 0;
	p->addcount         = 0;
	p->singlerefperfile = 0;

	p->headerf = bibtexout_writeheader;
	p->footerf = NULL;
	p->writef  = bibtexout_write;

	if ( !p->progname && progname )
		p->progname = strdup( progname );
}

enum {
	TYPE_UNKNOWN = 0,
	TYPE_ARTICLE,
	TYPE_INBOOK,
	TYPE_INPROCEEDINGS,
	TYPE_PROCEEDINGS,
	TYPE_INCOLLECTION,
	TYPE_COLLECTION,
	TYPE_BOOK,
	TYPE_PHDTHESIS,
	TYPE_MASTERSTHESIS,
	TYPE_REPORT,
	TYPE_MANUAL,
	TYPE_UNPUBLISHED,
	TYPE_ELECTRONIC,
	TYPE_MISC
};

static void
output_citekey( FILE *fp, fields *info, unsigned long refnum, int format_opts )
{
	int n = fields_find( info, "REFNUM", -1 );
	char *p;
	if ( n!=-1 ) {
		p = info->data[n].data;
		while ( p && *p && *p!='|' ) {
			if ( format_opts & BIBL_FORMAT_BIBOUT_STRICTKEY ) {
				if ( isdigit((unsigned char)*p) || (*p>='A' && *p<='Z') ||
				     (*p>='a' && *p<='z' ) )
					fprintf( fp, "%c", *p );
			}
			else {
				if ( *p!=' ' && *p!='\t' ) {
					fprintf( fp, "%c", *p );
				}
			}
			p++;
		}
	}
}

static int
bibtexout_type( fields *info, char *filename, int refnum, param *p )
{
	char *genre;
	int type = TYPE_UNKNOWN, i, maxlevel, n, level;

	/* determine bibliography type */
	for ( i=0; i<info->n; ++i ) {
		if ( strcasecmp( info->tag[i].data, "GENRE" ) &&
		     strcasecmp( info->tag[i].data, "NGENRE" ) ) continue;
		genre = info->data[i].data;
		level = info->level[i];
		if ( !strcasecmp( genre, "periodical" ) ||
		     !strcasecmp( genre, "academic journal" ) ||
		     !strcasecmp( genre, "magazine" ) ||
		     !strcasecmp( genre, "newspaper" ) ||
		     !strcasecmp( genre, "article" ) )
			type = TYPE_ARTICLE;
		else if ( !strcasecmp( genre, "instruction" ) )
			type = TYPE_MANUAL;
		else if ( !strcasecmp( genre, "unpublished" ) )
			type = TYPE_UNPUBLISHED;
		else if ( !strcasecmp( genre, "conference publication" ) ) {
			if ( level==0 ) type=TYPE_PROCEEDINGS;
			else type = TYPE_INPROCEEDINGS;
		} else if ( !strcasecmp( genre, "collection" ) ) {
			if ( level==0 ) type=TYPE_COLLECTION;
			else type = TYPE_INCOLLECTION;
		} else if ( !strcasecmp( genre, "report" ) )
			type = TYPE_REPORT;
		else if ( !strcasecmp( genre, "book chapter" ) )
			type = TYPE_INBOOK;
		else if ( !strcasecmp( genre, "book" ) ) {
			if ( level==0 ) type = TYPE_BOOK;
			else type = TYPE_INBOOK;
		} else if ( !strcasecmp( genre, "thesis" ) ) {
			if ( type==TYPE_UNKNOWN ) type=TYPE_PHDTHESIS;
		} else if ( !strcasecmp( genre, "Ph.D. thesis" ) )
			type = TYPE_PHDTHESIS;
		else if ( !strcasecmp( genre, "Masters thesis" ) )
			type = TYPE_MASTERSTHESIS;
		else  if ( !strcasecmp( genre, "electronic" ) )
			type = TYPE_ELECTRONIC;
	}
	if ( type==TYPE_UNKNOWN ) {
		for ( i=0; i<info->n; ++i ) {
			if ( strcasecmp( info->tag[i].data, "ISSUANCE" ) ) continue;
			if ( !strcasecmp( info->data[i].data, "monographic" ) ) {
				if ( info->level[i]==0 ) type = TYPE_BOOK;
				else if ( info->level[i]==1 ) type=TYPE_MISC;
			}
		}
	}

	/* default to BOOK type */
	if ( type==TYPE_UNKNOWN ) {
		maxlevel = fields_maxlevel( info );
		if ( maxlevel > 0 ) type = TYPE_MISC;
		else {
			if ( p->progname ) fprintf( stderr, "%s: ", p->progname );
			fprintf( stderr, "Cannot identify TYPE "
				"in reference %d ", refnum+1 );
			n = fields_find( info, "REFNUM", -1 );
			if ( n!=-1 ) 
				fprintf( stderr, " %s", info->data[n].data);
			fprintf( stderr, " (defaulting to @Misc)\n" );
			type = TYPE_MISC;
		}
	}
	return type;
}

static void
output_type( FILE *fp, int type, int format_opts )
{
	typedef struct {
		int bib_type;
		char *type_name;
	} typenames;

	typenames types[] = {
		{ TYPE_ARTICLE, "Article" },
		{ TYPE_INBOOK, "Inbook" },
		{ TYPE_PROCEEDINGS, "Proceedings" },
		{ TYPE_INPROCEEDINGS, "InProceedings" },
		{ TYPE_BOOK, "Book" },
		{ TYPE_PHDTHESIS, "PhdThesis" },
		{ TYPE_MASTERSTHESIS, "MastersThesis" },
		{ TYPE_REPORT, "TechReport" },
		{ TYPE_MANUAL, "Manual" },
		{ TYPE_COLLECTION, "Collection" },
		{ TYPE_INCOLLECTION, "InCollection" },
		{ TYPE_UNPUBLISHED, "Unpublished" },
		{ TYPE_ELECTRONIC, "Electronic" },
		{ TYPE_MISC, "Misc" } };
	int i, len, ntypes = sizeof( types ) / sizeof( types[0] );
	char *s = NULL;
	for ( i=0; i<ntypes; ++i ) {
		if ( types[i].bib_type == type ) {
			s = types[i].type_name;
			break;
		}
	}
	if ( !s ) s = types[ntypes-1].type_name; /* default to TYPE_MISC */
	if ( !(format_opts & BIBL_FORMAT_BIBOUT_UPPERCASE ) ) fprintf( fp, "@%s{", s );
	else {
		len = strlen( s );
		fprintf( fp, "@" );
		for ( i=0; i<len; ++i )
			fprintf( fp, "%c", toupper((unsigned char)s[i]) );
		fprintf( fp, "{" );
	}
}

static void
output_element( FILE *fp, char *tag, char *data, int format_opts )
{
	int i, len, nquotes = 0;
	char ch;
	fprintf( fp, ",\n" );
	if ( format_opts & BIBL_FORMAT_BIBOUT_WHITESPACE ) fprintf( fp, "  " );
	if ( !(format_opts & BIBL_FORMAT_BIBOUT_UPPERCASE ) ) fprintf( fp, "%s", tag );
	else {
		len = strlen( tag );
		for ( i=0; i<len; ++i )
			fprintf( fp, "%c", toupper((unsigned char)tag[i]) );
	}
	if ( format_opts & BIBL_FORMAT_BIBOUT_WHITESPACE ) fprintf( fp, " = \t" );
	else fprintf( fp, "=" );

	if ( format_opts & BIBL_FORMAT_BIBOUT_BRACKETS ) fprintf( fp, "{" );
	else fprintf( fp, "\"" );

	len = strlen( data );
	for ( i=0; i<len; ++i ) {
		ch = data[i];
		if ( ch!='\"' ) fprintf( fp, "%c", ch );
		else {
			if ( format_opts & BIBL_FORMAT_BIBOUT_BRACKETS ||
			    ( i>0 && data[i-1]=='\\' ) )
				fprintf( fp, "\"" );
			else {
				if ( nquotes % 2 == 0 )
					fprintf( fp, "``" );
				else    fprintf( fp, "\'\'" );
				nquotes++;
			}
		}
	}

	if ( format_opts & BIBL_FORMAT_BIBOUT_BRACKETS ) fprintf( fp, "}" );
	else fprintf( fp, "\"" );
}

static void
output_and_use( FILE *fp, fields *info, int n, char *outtag, int format_opts )
{
	output_element( fp, outtag, info->data[n].data, format_opts );
	fields_setused( info, n );
}

static void
output_simple( FILE *fp, fields *info, char *intag, char *outtag, 
		int format_opts )
{
	int n = fields_find( info, intag, -1 );
	if ( n!=-1 ) {
		output_and_use( fp, info, n, outtag, format_opts );
	}
}

static void
output_simpleall( FILE *fp, fields *info, char *intag, char *outtag,
		int format_opts )
{
	int i;
	for ( i=0; i<info->n; ++i ) {
		if ( fields_match_tag( info, i, intag ) )
			output_and_use( fp, info, i, outtag, format_opts );
	}
}

static void
output_keywords( FILE *fp, fields *info, int format_opts )
{
	newstr keywords, *word;
	vplist a;
	int i;
	newstr_init( &keywords );
	vplist_init( &a );
	fields_findv_each( info, LEVEL_ANY, FIELDS_STRP, &a, "KEYWORD" );
	if ( a.n ) {
		for ( i=0; i<a.n; ++i ) {
			word = vplist_get( &a, i );
			if ( i>0 ) newstr_strcat( &keywords, "; " );
			newstr_newstrcat( &keywords, word );
		}
		output_element( fp, "keywords", keywords.data, format_opts );

	}
	newstr_free( &keywords );
	vplist_free( &a );
}

static void
output_fileattach( FILE *fp, fields *info, int format_opts )
{
	newstr data;
	int i;
	newstr_init( &data );
	for ( i=0; i<info->n; ++i ) {
		if ( strcasecmp( info->tag[i].data, "FILEATTACH" ) ) continue;
		newstr_strcpy( &data, ":" );
		newstr_newstrcat( &data, &(info->data[i]) );
		if ( strsearch( info->data[i].data, ".pdf" ) )
			newstr_strcat( &data, ":PDF" );
		else if ( strsearch( info->data[i].data, ".html" ) )
			newstr_strcat( &data, ":HTML" );
		else newstr_strcat( &data, ":TYPE" );
		output_element( fp, "file", data.data, format_opts );
		fields_setused( info, i );
		newstr_empty( &data );
	}
	newstr_free( &data );
}

static void
output_people( FILE *fp, fields *info, unsigned long refnum, char *tag, 
		char *ctag, char *atag, char *bibtag, int level, 
		int format_opts )
{
	newstr allpeople, oneperson;
	int i, npeople, person, corp, asis;

	newstrs_init( &allpeople, &oneperson, NULL );

	/* primary citation authors */
	npeople = 0;
	for ( i=0; i<info->n; ++i ) {
		if ( level!=-1 && info->level[i]!=level ) continue;
		person = ( strcasecmp( info->tag[i].data, tag ) == 0 );
		corp   = ( strcasecmp( info->tag[i].data, ctag ) == 0 );
		asis   = ( strcasecmp( info->tag[i].data, atag ) == 0 );
		if ( person || corp || asis ) {
			if ( npeople>0 ) {
				if ( format_opts & BIBL_FORMAT_BIBOUT_WHITESPACE )
					newstr_strcat(&allpeople,"\n\t\tand ");
				else newstr_strcat( &allpeople, "\nand " );
			}
			if ( corp ) {
				newstr_addchar( &allpeople, '{' );
				newstr_strcat( &allpeople, fields_value( info, i, FIELDS_CHRP ) );
				newstr_addchar( &allpeople, '}' );
			} else if ( asis ) {
				newstr_addchar( &allpeople, '{' );
				newstr_strcat( &allpeople, fields_value( info, i, FIELDS_CHRP ) );
				newstr_addchar( &allpeople, '}' );
			} else {
				name_build_withcomma( &oneperson, fields_value( info, i, FIELDS_CHRP ) );
				newstr_newstrcat( &allpeople, &oneperson );
			}
			npeople++;
		}
	}
	if ( npeople )
		output_element( fp, bibtag, allpeople.data, format_opts );

	newstrs_free( &allpeople, &oneperson, NULL );
}

static void
output_title_chosen( FILE *fp, fields *info, char *bibtag, int format_opts, int n1, int n2 )
{
	newstr title, *mainttl, *subttl;

	if ( n1==-1 ) return;

	newstr_init( &title );

	mainttl = fields_value( info, n1, FIELDS_STRP );
	newstr_newstrcpy( &title, mainttl );
	fields_setused( info, n1 );
	if ( n2!=-1 ) {
		subttl = fields_value( info, n2, FIELDS_STRP );
		if ( mainttl->len > 0 &&
		     mainttl->data[mainttl->len-1]!='?' )
			newstr_strcat( &title, ": " );
		else newstr_addchar( &title, ' ' );
		newstr_newstrcat( &title, subttl );
		fields_setused( info, n2 );
	}
	output_element( fp, bibtag, title.data, format_opts );

	newstr_free( &title );
}

static void
output_title( FILE *fp, fields *info, unsigned long refnum, char *bibtag, int level, int format_opts )
{
	int title = -1, short_title = -1;
	int subtitle = -1, short_subtitle = -1;
	int use_title = -1, use_subtitle = -1;

	title          = fields_find( info, "TITLE",         level );
	short_title    = fields_find( info, "SHORTTITLE",    level );
	subtitle       = fields_find( info, "SUBTITLE",      level );
	short_subtitle = fields_find( info, "SHORTSUBTITLE", level );

	if ( title==-1 || ( ( format_opts & BIBL_FORMAT_BIBOUT_SHORTTITLE ) && level==1 ) ) {
		use_title    = short_title;
		use_subtitle = short_subtitle;
	}

	else {
		use_title    = title;
		use_subtitle = subtitle;
	}

	output_title_chosen( fp, info, bibtag, format_opts, use_title, use_subtitle );
}

static void
output_date( FILE *fp, fields *info, unsigned long refnum, int format_opts )
{
	char *months[12] = { "Jan", "Feb", "Mar", "Apr", "May", "Jun", 
		"Jul", "Aug", "Sep", "Oct", "Nov", "Dec" };
	int n, month;
	n = fields_find( info, "DATE:YEAR", -1 );
	if ( n==-1 ) n = fields_find( info, "PARTDATE:YEAR", -1 );
	if ( n!=-1 ) {
		output_element( fp, "year", info->data[n].data, format_opts );
		fields_setused( info, n );
	}
	n = fields_find( info, "DATE:MONTH", -1 );
	if ( n==-1 ) n = fields_find( info, "PARTDATE:MONTH", -1 );
	if ( n!=-1 ) {
		month = atoi( info->data[n].data );
		if ( month>0 && month<13 )
			output_element( fp, "month", months[month-1], format_opts );
		else
			output_element( fp, "month", info->data[n].data, format_opts );
		fields_setused( info, n );
	}
	n = fields_find( info, "DATE:DAY", -1 );
	if ( n==-1 ) n = fields_find( info, "PARTDATE:DAY", -1 );
	if ( n!=-1 ) {
		output_element( fp, "day", info->data[n].data, format_opts );
		fields_setused( info, n );
	}
}


/* output article number as pages if true pages aren't found */
static void
output_articlenumber( FILE *fp, fields *info, unsigned long refnum,
	int format_opts )
{
	int ar = fields_find( info, "ARTICLENUMBER", -1 );
	if ( ar!=-1 ) {
		newstr pages;
		newstr_init( &pages );
		newstr_strcat( &pages, info->data[ar].data );
		output_element( fp, "pages", pages.data, format_opts );
		fields_setused( info, ar );
		newstr_free( &pages );
	}
}

static void
output_arxiv( FILE *fp, fields *info, int format_opts )
{
	int ar = fields_find( info, "ARXIV", -1 );
	newstr arxiv;

	if ( ar==-1 ) return;

	/* ...write:
	 *     archivePrefix = "arXiv",
	 *     eprint = "#####",
	 * ...for people in high energy physics
	 */
	output_element( fp, "archivePrefix", "arXiv", format_opts );
	output_element( fp, "eprint", info->data[ar].data, format_opts );

	/* ...also write:
	 *     url = "http://arxiv.org/abs/####",
	 * ...to maximize compatibility
	 */
	newstr_init( &arxiv );
	arxiv_to_url( info, ar, "URL", &arxiv );
	if ( arxiv.len )
		output_element( fp, "url", arxiv.data, format_opts );
	newstr_free( &arxiv );
}

static void
output_pmc( FILE *fp, fields *info, int format_opts )
{
	int pm = fields_find( info, "PMC", -1 );
	if ( pm!=-1 ) {
		newstr pmc;
		newstr_init( &pmc );
		pmc_to_url( info, pm, "URL", &pmc );
		if ( pmc.len )
			output_element( fp, "url", pmc.data, format_opts );
		newstr_free( &pmc );
	}
}

static void
output_pmid( FILE *fp, fields *info, int format_opts )
{
	int pm = fields_find( info, "PMID", -1 );
	if ( pm!=-1 ) {
		newstr pmid;
		newstr_init( &pmid );
		pmid_to_url( info, pm, "URL", &pmid );
		if ( pmid.len )
			output_element( fp, "url", pmid.data, format_opts );
		newstr_free( &pmid );
	}
}

static void
output_jstor( FILE *fp, fields *info, int format_opts )
{
	int js = fields_find( info, "JSTOR", -1 );
	if ( js!=-1 ) {
		newstr jstor;
		newstr_init( &jstor );
		jstor_to_url( info, js, "URL", &jstor );
		if ( jstor.len )
			output_element( fp, "url", jstor.data, format_opts );
		newstr_free( &jstor );
	}
}

static void
output_isi( FILE *fp, fields *info, int format_opts )
{
	int n = fields_find( info, "ISIREFNUM", -1 );
	if ( n!=-1 ) {
		output_element( fp, "note", fields_value( info, n, FIELDS_CHRP ), format_opts );
	}
}

static void
output_pages( FILE *fp, fields *info, unsigned long refnum, int format_opts )
{
	newstr pages;
	int sn, en;
	sn = fields_find( info, "PAGES:START", -1 );
	en = fields_find( info, "PAGES:STOP", -1 );
	if ( sn==-1 && en==-1 ) {
		output_articlenumber( fp, info, refnum, format_opts );
		return;
	}
	newstr_init( &pages );
	if ( sn!=-1 ) {
		newstr_strcat( &pages, info->data[sn].data );
		fields_setused( info, sn );
	}
	if ( sn!=-1 && en!=-1 ) {
		if ( format_opts & BIBL_FORMAT_BIBOUT_SINGLEDASH )
			newstr_strcat( &pages, "-" );
		else
			newstr_strcat( &pages, "--" );
	}
	if ( en!=-1 ) {
		newstr_strcat( &pages, info->data[en].data );
		fields_setused( info, en );
	}
	output_element( fp, "pages", pages.data, format_opts );
	newstr_free( &pages );
}

/*
 * from Tim Hicks:
 * I'm no expert on bibtex, but those who know more than I on our mailing 
 * list suggest that 'issue' isn't a recognised key for bibtex and 
 * therefore that bibutils should be aliasing IS to number at some point in 
 * the conversion.
 *
 * Therefore prefer outputting issue/number as number and only keep
 * a distinction if both issue and number are present for a particular
 * reference.
 */

static void
output_issue_number( FILE *fp, fields *info, int format_opts )
{
	int nissue  = fields_find( info, "ISSUE", -1 );
	int nnumber = fields_find( info, "NUMBER", -1 );
	if ( nissue!=-1 && nnumber!=-1 ) {
		output_and_use( fp, info, nissue,  "issue",  format_opts );
		output_and_use( fp, info, nnumber, "number", format_opts );
/*		output_element( fp, "issue", info->data[nissue].data, 
				format_opts );
		fields_setused( info, nissue );
		output_element( fp, "number", info->data[nnumber].data, 
				format_opts );
		fields_setused( info, nnumber );*/
	} else if ( nissue!=-1 ) {
		output_and_use( fp, info, nissue, "number", format_opts );
/*
		output_element( fp, "number", info->data[nissue].data, 
				format_opts );
		fields_setused( info, nissue );*/
	} else if ( nnumber!=-1 ) {
		output_and_use( fp, info, nnumber, "number", format_opts );
/*
		output_element( fp, "number", info->data[nnumber].data, 
				format_opts );
		fields_setused( info, nnumber );
*/
	}
}

static void
bibtexout_write( fields *info, FILE *fp, param *p, unsigned long refnum )
{
	int type;
	fields_clearused( info );
	type = bibtexout_type( info, "", refnum, p );
	output_type( fp, type, p->format_opts );
	if ( !( p->format_opts & BIBL_FORMAT_BIBOUT_DROPKEY ) )
		output_citekey( fp, info, refnum, p->format_opts );
	output_people( fp, info, refnum, "AUTHOR", "AUTHOR:CORP", "AUTHOR:ASIS", "author", 0,
		p->format_opts );
	output_people( fp, info, refnum, "EDITOR", "EDITOR:CORP", "EDITOR:ASIS", "editor", -1,
		p->format_opts );
	output_people( fp, info, refnum, "TRANSLATOR", "TRANSLATOR:CORP", "TRANSLATOR:ASIS", "translator", -1, p->format_opts );

	/* item=main level title */
	output_title( fp, info, refnum, "title", 0, p->format_opts );

	/* item=host level title */
	if ( type==TYPE_ARTICLE )
		output_title( fp, info, refnum, "journal", 1, p->format_opts );
	else if ( type==TYPE_INBOOK ) {
		output_title( fp, info, refnum, "bookTitle", 1, p->format_opts );
		output_title( fp, info, refnum, "series", 2, p->format_opts );
	}
	else if ( type==TYPE_INPROCEEDINGS || type==TYPE_INCOLLECTION ) {
		output_title( fp, info, refnum, "booktitle", 1, p->format_opts );
		output_title( fp, info, refnum, "series", 2, p->format_opts );
	}
	else if ( type==TYPE_PHDTHESIS || type==TYPE_MASTERSTHESIS ) {
		output_title( fp, info, refnum, "series", 1, p->format_opts );
	}
	else if ( type==TYPE_BOOK || type==TYPE_COLLECTION || type==TYPE_PROCEEDINGS || type==TYPE_REPORT ) {
		output_title( fp, info, refnum, "series", 1, p->format_opts );
		output_title( fp, info, refnum, "series", 2, p->format_opts );
	}

	output_date( fp, info, refnum, p->format_opts );
	output_simple( fp, info, "EDITION", "edition", p->format_opts );
	output_simple( fp, info, "PUBLISHER", "publisher", p->format_opts );
	output_simple( fp, info, "ADDRESS", "address", p->format_opts );
	output_simple( fp, info, "VOLUME", "volume", p->format_opts );
	output_issue_number( fp, info, p->format_opts );
/*	output_simple( fp, info, "ISSUE", "issue", p->format_opts );
	output_simple( fp, info, "NUMBER", "number", p->format_opts );s*/
	output_pages( fp, info, refnum, p->format_opts );
	output_keywords( fp, info, p->format_opts );
	output_simple( fp, info, "CONTENTS", "contents", p->format_opts );
	output_simple( fp, info, "ABSTRACT", "abstract", p->format_opts );
	output_simple( fp, info, "LOCATION", "location", p->format_opts );
	output_simple( fp, info, "DEGREEGRANTOR", "school", p->format_opts );
	output_simple( fp, info, "DEGREEGRANTOR:ASIS", "school", p->format_opts );
	output_simple( fp, info, "DEGREEGRANTOR:CORP", "school", p->format_opts );
	output_simpleall( fp, info, "NOTES", "note", p->format_opts );
	output_simpleall( fp, info, "ANNOTE", "annote", p->format_opts );
	output_simple( fp, info, "ISBN", "isbn", p->format_opts );
	output_simple( fp, info, "ISSN", "issn", p->format_opts );
	output_simple( fp, info, "DOI", "doi", p->format_opts );
	output_simpleall( fp, info, "URL", "url", p->format_opts );
	output_fileattach( fp, info, p->format_opts );
	output_arxiv( fp, info, p->format_opts );
	output_pmid( fp, info, p->format_opts );
	output_pmc( fp, info, p->format_opts );
	output_jstor( fp, info, p->format_opts );
	output_isi( fp, info, p->format_opts );
	output_simple( fp, info, "LANGUAGE", "language", p->format_opts );
	if ( p->format_opts & BIBL_FORMAT_BIBOUT_FINALCOMMA ) fprintf( fp, "," );
	fprintf( fp, "\n}\n\n" );
	fflush( fp );
}

static void
bibtexout_writeheader( FILE *outptr, param *p )
{
	if ( p->utf8bom ) utf8_writebom( outptr );
}

