/*
 * risout.c
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
#include "utf8.h"
#include "newstr.h"
#include "strsearch.h"
#include "fields.h"
#include "doi.h"
#include "name.h"
#include "bibformats.h"

static void risout_write( fields *info, FILE *fp, param *p, unsigned long refnum );
static void risout_writeheader( FILE *outptr, param *p );


void
risout_initparams( param *p, const char *progname )
{
	p->writeformat      = BIBL_RISOUT;
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

	p->headerf = risout_writeheader;
	p->footerf = NULL;
	p->writef  = risout_write;
}

enum { 
	TYPE_UNKNOWN,
	TYPE_STD,                /* standard/generic */
	TYPE_ABSTRACT,           /* abstract */
	TYPE_ARTICLE,            /* article */
	TYPE_BOOK,               /* book */
	TYPE_CASE,               /* case */
	TYPE_INBOOK,             /* chapter */
	TYPE_CONF,               /* conference */
	TYPE_ELEC,               /* electronic */
	TYPE_HEAR,               /* hearing */
	TYPE_MAGARTICLE,         /* magazine article */
	TYPE_NEWS,               /* newspaper */
	TYPE_MPCT,               /* mpct */
	TYPE_PAMP,               /* pamphlet */
	TYPE_PATENT,             /* patent */
	TYPE_PCOMM,              /* personal communication */
	TYPE_PROGRAM,            /* program */
	TYPE_REPORT,             /* report */
	TYPE_STATUTE,            /* statute */
	TYPE_THESIS,             /* thesis */
	TYPE_MASTERSTHESIS,      /* thesis */
	TYPE_PHDTHESIS,          /* thesis */
	TYPE_DIPLOMATHESIS,      /* thesis */
	TYPE_DOCTORALTHESIS,     /* thesis */
	TYPE_HABILITATIONTHESIS, /* thesis */
	TYPE_MAP,                /* map, cartographic data */
	TYPE_UNPUBLISHED,        /* unpublished */
};

static void
write_type( FILE *fp, int type )
{
	switch( type ) {
	case TYPE_UNKNOWN:            fprintf( fp, "TYPE_UNKNOWN" );            break;
	case TYPE_STD:                fprintf( fp, "TYPE_STD" );                break;
	case TYPE_ABSTRACT:           fprintf( fp, "TYPE_ABSTRACT" );           break;
	case TYPE_ARTICLE:            fprintf( fp, "TYPE_ARTICLE" );            break;
	case TYPE_BOOK:               fprintf( fp, "TYPE_BOOK" );               break;
	case TYPE_CASE:               fprintf( fp, "TYPE_CASE" );               break;
	case TYPE_INBOOK:             fprintf( fp, "TYPE_INBOOK" );             break;
	case TYPE_CONF:               fprintf( fp, "TYPE_CONF" );               break;
	case TYPE_ELEC:               fprintf( fp, "TYPE_ELEC" );               break;
	case TYPE_HEAR:               fprintf( fp, "TYPE_HEAR" );               break;
	case TYPE_MAGARTICLE:         fprintf( fp, "TYPE_MAGARTICLE" );         break;
	case TYPE_NEWS:               fprintf( fp, "TYPE_NEWS" );               break;
	case TYPE_MPCT:               fprintf( fp, "TYPE_MCPT" );               break;
	case TYPE_PAMP:               fprintf( fp, "TYPE_PAMP" );               break;
	case TYPE_PATENT:             fprintf( fp, "TYPE_PATENT" );             break;
	case TYPE_PCOMM:              fprintf( fp, "TYPE_PCOMM" );              break;
	case TYPE_PROGRAM:            fprintf( fp, "TYPE_PROGRAM" );            break;
	case TYPE_REPORT:             fprintf( fp, "TYPE_REPORT" );             break;
	case TYPE_STATUTE:            fprintf( fp, "TYPE_STATUTE" );            break;
	case TYPE_THESIS:             fprintf( fp, "TYPE_THESIS" );             break;
	case TYPE_MASTERSTHESIS:      fprintf( fp, "TYPE_MASTERSTHESIS" );      break;
	case TYPE_PHDTHESIS:          fprintf( fp, "TYPE_PHDTHESIS" );          break;
	case TYPE_DIPLOMATHESIS:      fprintf( fp, "TYPE_DIPLOMATHESIS" );      break;
	case TYPE_DOCTORALTHESIS:     fprintf( fp, "TYPE_DOCTORALTHESIS" );     break;
	case TYPE_HABILITATIONTHESIS: fprintf( fp, "TYPE_HABILITATIONTHESIS" ); break;
	case TYPE_MAP:                fprintf( fp, "TYPE_MAP" );                break;
	case TYPE_UNPUBLISHED:        fprintf( fp, "TYPE_UNPUBLISHED" );        break;
	default:                      fprintf( fp, "Error - type not in enum" );break;
	}
}

typedef struct match_type {
	char *name;
	int type;
} match_type;

/* Try to determine type of reference from
 * <genre></genre>
 */
static int
get_type_genre( fields *f, param *p )
{
	match_type match_genres[] = {
		{ "academic journal",          TYPE_ARTICLE },
		{ "article",                   TYPE_ARTICLE },
		{ "journal article",           TYPE_ARTICLE },
		{ "magazine",                  TYPE_MAGARTICLE },
		{ "conference publication",    TYPE_CONF },
		{ "newspaper",                 TYPE_NEWS },
		{ "legislation",               TYPE_STATUTE },
		{ "communication",             TYPE_PCOMM },
		{ "hearing",                   TYPE_HEAR },
		{ "electronic",                TYPE_ELEC },
		{ "legal case and case notes", TYPE_CASE },
		{ "book chapter",              TYPE_INBOOK },
		{ "Ph.D. thesis",              TYPE_PHDTHESIS },
		{ "Masters thesis",            TYPE_MASTERSTHESIS },
		{ "Diploma thesis",            TYPE_DIPLOMATHESIS },
		{ "Doctoral thesis",           TYPE_DOCTORALTHESIS },
		{ "Habilitation thesis",       TYPE_HABILITATIONTHESIS },
		{ "report",                    TYPE_REPORT },
		{ "abstract or summary",       TYPE_ABSTRACT },
		{ "patent",                    TYPE_PATENT },
		{ "unpublished",               TYPE_UNPUBLISHED },
		{ "map",                       TYPE_MAP },
	};
	int nmatch_genres = sizeof( match_genres ) / sizeof( match_genres[0] );
	int type, i, j;
	char *tag, *value;

	type = TYPE_UNKNOWN;

	for ( i=0; i<fields_num( f ); ++i ) {
		if ( !fields_match_tag( f, i, "GENRE" ) &&
		     !fields_match_tag( f, i, "NGENRE" ) )
			continue;
		value = ( char * ) fields_value( f, i, FIELDS_CHRP );
		for ( j=0; j<nmatch_genres; ++j )
			if ( !strcasecmp( match_genres[j].name, value ) )
				type = match_genres[j].type;
		if ( p->verbose ) {
			tag = ( char * ) fields_tag( f, i, FIELDS_CHRP );
			if ( p->progname ) fprintf( stderr, "%s: ", p->progname );
			fprintf( stderr, "Type from tag '%s' data '%s': ", tag, value );
			write_type( stderr, type );
			fprintf( stderr, "\n" );
		}
		if ( type==TYPE_UNKNOWN ) {
			if ( !strcasecmp( value, "periodical" ) )
				type = TYPE_ARTICLE;
			else if ( !strcasecmp( value, "thesis" ) )
				type = TYPE_THESIS;
			else if ( !strcasecmp( value, "book" ) ) {
				if ( fields_level( f, i )==0 ) type=TYPE_BOOK;
				else type=TYPE_INBOOK;
			}
			else if ( !strcasecmp( value, "collection" ) ) {
				if ( fields_level( f, i )==0 ) type=TYPE_BOOK;
				else type=TYPE_INBOOK;
			}
		}

	}

	if ( p->verbose ) {
		if ( p->progname ) fprintf( stderr, "%s: ", p->progname );
		fprintf( stderr, "Type from genre element: " );
		write_type( stderr, type );
		fprintf( stderr, "\n" );
	}

	return type;
}

/* Try to determine type of reference from
 * <TypeOfResource></TypeOfResource>
 */
static int
get_type_resource( fields *f, param *p )
{
	match_type match_res[] = {
		{ "software, multimedia",      TYPE_PROGRAM },
		{ "cartographic",              TYPE_MAP     },
	};
	int nmatch_res = sizeof( match_res ) / sizeof( match_res[0] );
	int type, i, j;
	char *value;
	vplist a;

	type = TYPE_UNKNOWN;

	vplist_init( &a );
	fields_findv_each( f, LEVEL_ANY, FIELDS_CHRP, &a, "RESOURCE" );

	for ( i=0; i<a.n; ++i ) {
		value = ( char * ) vplist_get( &a, i );
		for ( j=0; j<nmatch_res; ++j ) {
			if ( !strcasecmp( value, match_res[j].name ) )
				type = match_res[j].type;
		}
		if ( p->verbose ) {
			if ( p->progname ) fprintf( stderr, "%s: ", p->progname );
			fprintf( stderr, "Type from tag 'RESOURCE' data '%s': ", value );
			write_type( stderr, type );
			fprintf( stderr, "\n" );
		}
	}

	if ( p->verbose ) {
		if ( p->progname ) fprintf( stderr, "%s: ", p->progname );
		fprintf( stderr, "Type from resource element: " );
		write_type( stderr, type );
		fprintf( stderr, "\n" );
	}

	vplist_free( &a );
	return type;
}

/* Try to determine type of reference from <issuance></issuance> and */
/* <typeOfReference></typeOfReference> */
static int
get_type_issuance( fields *f, param *p )
{
	int type = TYPE_UNKNOWN;
	int i, monographic = 0, monographic_level = 0;
//	int text = 0;
	for ( i=0; i<f->n; ++i ) {
		if ( !strcasecmp( f->tag[i].data, "issuance" ) &&
		     !strcasecmp( f->data[i].data, "MONOGRAPHIC" ) ){
			monographic = 1;
			monographic_level = f->level[i];
		}
//		if ( !strcasecmp( f->tag[i].data, "typeOfResource" ) &&
//		     !strcasecmp( f->data[i].data,"text") ) {
//			text = 1;
//		}
	}
//	if ( monographic && text ) {
	if ( monographic ) {
		if ( monographic_level==0 ) type=TYPE_BOOK;
		else if ( monographic_level>0 ) type=TYPE_INBOOK;
	}

	if ( p->verbose ) {
		if ( p->progname ) fprintf( stderr, "%s: ", p->progname );
		fprintf( stderr, "Type from issuance/typeOfReference elements: " );
		write_type( stderr, type );
		fprintf( stderr, "\n" );
	}

	return type;
}

static int
get_type( fields *f, param *p )
{
	int type;
	type = get_type_genre( f, p );
	if ( type==TYPE_UNKNOWN ) type = get_type_resource( f, p );
	if ( type==TYPE_UNKNOWN ) type = get_type_issuance( f, p );
	if ( type==TYPE_UNKNOWN ) {
		if ( fields_maxlevel( f ) > 0 ) type = TYPE_INBOOK;
		else type = TYPE_STD;
	}

	if ( p->verbose ) {
		if ( p->progname ) fprintf( stderr, "%s: ", p->progname );
		fprintf( stderr, "Final type: " );
		write_type( stderr, type );
		fprintf( stderr, "\n" );
	}


	return type;
}

static void
output_type( FILE *fp, int type, param *p )
{
	match_type tyout[] = {
		{ "STD",  TYPE_STD },
		{ "ABST", TYPE_ABSTRACT },
		{ "JOUR", TYPE_ARTICLE },
		{ "BOOK", TYPE_BOOK },
		{ "CASE", TYPE_CASE },
		{ "CHAP", TYPE_INBOOK },
		{ "CONF", TYPE_CONF },
		{ "ELEC", TYPE_ELEC },
		{ "HEAR", TYPE_HEAR },
		{ "MGZN", TYPE_MAGARTICLE },
		{ "NEWS", TYPE_NEWS },
		{ "MPCT", TYPE_MPCT },
		{ "PAMP", TYPE_PAMP },
		{ "PAT",  TYPE_PATENT },
		{ "PCOMM",TYPE_PCOMM },
		{ "COMP", TYPE_PROGRAM },
		{ "RPRT", TYPE_REPORT },
		{ "STAT", TYPE_STATUTE },
		{ "THES", TYPE_THESIS },
		{ "THES", TYPE_MASTERSTHESIS },
		{ "THES", TYPE_PHDTHESIS },
		{ "THES", TYPE_DIPLOMATHESIS },
		{ "THES", TYPE_DOCTORALTHESIS },
		{ "THES", TYPE_HABILITATIONTHESIS },
		{ "MAP",  TYPE_MAP },
		{ "UNPB", TYPE_UNPUBLISHED }
	};
	int ntyout = sizeof( tyout ) / sizeof( tyout[0] );
	int i, found;

	fprintf( fp, "TY  - " );
	found = 0;
	for ( i=0; i<ntyout && !found ; ++i ) {
		if ( tyout[i].type == type ) {
			fprintf( fp, "%s", tyout[i].name );
			found = 1;
		}
	}
	/* Report internal error, default to TYPE_STD */
	if ( !found ) {
		if ( p->progname ) fprintf( stderr, "%s: ", p->progname );
		fprintf( stderr, "Internal Error: Cannot identify type %d\n",
			type );
		fprintf( fp, "STD" );
	}
	fprintf( fp, "\n" );
}

static void
output_people( FILE *fp, fields *f, char *tag, char *ristag, int level )
{
	newstr oneperson;
	vplist people;
	int i;
	newstr_init( &oneperson );
	vplist_init( &people );
	fields_findv_each( f, level, FIELDS_CHRP, &people, tag );
	for ( i=0; i<people.n; ++i ) {
		name_build_withcomma( &oneperson, ( char * ) vplist_get( &people, i ) );
		fprintf( fp, "%s  - %s\n", ristag, oneperson.data );
	}
	vplist_free( &people );
	newstr_free( &oneperson );
}

static void
output_date( FILE *fp, fields *f )
{
	char *year  = fields_findv_firstof( f, LEVEL_ANY, FIELDS_CHRP,
			"DATE:YEAR", "PARTDATE:YEAR", NULL );
	char *month = fields_findv_firstof( f, LEVEL_ANY, FIELDS_CHRP,
			"DATE:MONTH", "PARTDATE:MONTH", NULL );
	char *day   = fields_findv_firstof( f, LEVEL_ANY, FIELDS_CHRP,
			"DATE:DAY", "PARTDATE:DAY", NULL );
	if ( year )
		fprintf( fp, "PY  - %s\n", year );
	if ( year || month || day ) {
		fprintf( fp, "DA  - " );
		if ( year ) fprintf( fp, "%s", year );
		fprintf( fp, "/" );
		if ( month ) fprintf( fp, "%s", month );
		fprintf( fp, "/" );
		if ( day ) fprintf( fp, "%s", day );
		fprintf( fp, "\n" );
	}
}

static void
output_titlecore( FILE *fp, fields *f, char *ristag, int level,
	char *maintag, char *subtag )
{
	newstr *mainttl = fields_findv( f, level, FIELDS_STRP, maintag );
	newstr *subttl  = fields_findv( f, level, FIELDS_STRP, subtag );

	if ( !mainttl ) return;

	fprintf( fp, "%s  - %s", ristag, mainttl->data );
	if ( subttl ) {
		if ( mainttl->len > 0 &&
		     mainttl->data[ mainttl->len - 1 ]!='?' )
			fprintf( fp, ":" );
		fprintf( fp, " %s", subttl->data );
	}
	fprintf( fp, "\n" );
}

static int
type_is_element( int type )
{
	if ( type==TYPE_ARTICLE )    return 1;
	if ( type==TYPE_INBOOK )     return 1;
	if ( type==TYPE_MAGARTICLE ) return 1;
	if ( type==TYPE_NEWS )       return 1;
	if ( type==TYPE_ABSTRACT )   return 1;
	if ( type==TYPE_CONF )       return 1;
	return 0;
}

static int
type_uses_journal( int type )
{
	if ( type==TYPE_ARTICLE )    return 1;
	if ( type==TYPE_MAGARTICLE ) return 1;
	return 0;
}

static void
output_alltitles( FILE *fp, fields *f, int type )
{
	output_titlecore( fp, f, "TI", 0, "TITLE", "SUBTITLE" );
	output_titlecore( fp, f, "T2", -1, "SHORTTITLE", "SHORTSUBTITLE" );
	if ( type_is_element( type ) ) {
		if ( type_uses_journal( type ) )
			output_titlecore( fp, f, "JO", 1, "TITLE", "SUBTITLE" );
		else output_titlecore( fp, f, "BT", 1, "TITLE", "SUBTITLE" );
		output_titlecore( fp, f, "T3", 2, "TITLE", "SUBTITLE" );
	} else {
		output_titlecore( fp, f, "T3", 1, "TITLE", "SUBTITLE" );
	}
}

static void
output_pages( FILE *fp, fields *f )
{
	char *sn = fields_findv( f, LEVEL_ANY, FIELDS_CHRP, "PAGES:START" );
	char *en = fields_findv( f, LEVEL_ANY, FIELDS_CHRP, "PAGES:STOP" );
	char *ar;

	if ( sn || en ) {
		if ( sn ) fprintf( fp, "SP  - %s\n", sn );
		if ( en ) fprintf( fp, "EP  - %s\n", en );
	} else {
		ar = fields_findv( f, LEVEL_ANY, FIELDS_CHRP, "ARTICLENUMBER" );
		if ( ar ) fprintf( fp, "SP  - %s\n", ar );
	}
}

static void
output_keywords( FILE *fp, fields *f )
{
	vplist vpl;
	int i;
	vplist_init( &vpl );
	fields_findv_each( f, LEVEL_ANY, FIELDS_CHRP, &vpl, "KEYWORD" );
	for ( i=0; i<vpl.n; ++i )
		fprintf( fp, "KW  - %s\n", ( char * ) vplist_get( &vpl, i ) );
	vplist_free( &vpl );
}

static void
output_pmc( FILE *fp, fields *f )
{
	newstr s;
	int i;
	newstr_init( &s );
	for ( i=0; i<fields_num( f ); ++i ) {
		if ( !fields_match_tag( f, i, "PMC" ) ) continue;
		pmc_to_url( f, i, "URL", &s );
		if ( s.len )
			fprintf( fp, "UR  - %s\n", s.data );
	}
	newstr_free( &s );
}

static void
output_pmid( FILE *fp, fields *f )
{
	newstr s;
	int i;
	newstr_init( &s );
	for ( i=0; i<fields_num( f ); ++i ) {
		if ( !fields_match_tag( f, i, "PMID" ) ) continue;
		pmid_to_url( f, i, "URL", &s );
		if ( s.len )
			fprintf( fp, "UR  - %s\n", s.data );
	}
	newstr_free( &s );
}

static void
output_arxiv( FILE *fp, fields *f )
{
	newstr s;
	int i;
	newstr_init( &s );
	for ( i=0; i<fields_num( f ); ++i ) {
		if ( !fields_match_tag( f, i, "ARXIV" ) ) continue;
		arxiv_to_url( f, i, "URL", &s );
		if ( s.len )
			fprintf( fp, "UR  - %s\n", s.data );
	}
	newstr_free( &s );
}

static void
output_jstor( FILE *fp, fields *f )
{
	newstr s;
	int i;
	newstr_init( &s );
	for ( i=0; i<fields_num( f ); ++i ) {
		if ( !fields_match_tag( f, i, "JSTOR" ) ) continue;
		jstor_to_url( f, i, "URL", &s );
		if ( s.len )
			fprintf( fp, "UR  - %s\n", s.data );
	}
	newstr_free( &s );
}

static void
output_thesishint( FILE *fp, int type )
{
	if ( type==TYPE_MASTERSTHESIS )
		fprintf( fp, "%s  - %s\n", "U1", "Masters thesis" );
	else if ( type==TYPE_PHDTHESIS )
		fprintf( fp, "%s  - %s\n", "U1", "Ph.D. thesis" );
	else if ( type==TYPE_DIPLOMATHESIS )
		fprintf( fp, "%s  - %s\n", "U1", "Diploma thesis" );
	else if ( type==TYPE_DOCTORALTHESIS )
		fprintf( fp, "%s  - %s\n", "U1", "Doctoral thesis" );
	else if ( type==TYPE_HABILITATIONTHESIS )
		fprintf( fp, "%s  - %s\n", "U1", "Habilitation thesis" );
}

static int
is_uri_scheme( char *p )
{
	char *scheme[] = { "http:", "file:", "ftp:", "git:", "gopher:" };
	int i, len, nschemes = sizeof( scheme ) / sizeof( scheme[0] );
	for ( i=0; i<nschemes; ++i ) {
		len = strlen( scheme[i] );
		if ( !strncmp( p, scheme[i], len ) ) return len;
	}
	return 0;
}


static void
output_file( FILE *fp, fields *f, char *tag, char *ristag, int level )
{
	vplist a;
	char *fl;
	int i;
	vplist_init( &a );
	fields_findv_each( f, level, FIELDS_CHRP, &a, tag );
	for ( i=0; i<a.n; ++i ) {
		fprintf( fp, "%s  - ", ristag );
		fl = ( char * ) vplist_get( &a, i );
		if ( !is_uri_scheme( fl ) )
			fprintf( fp, "file:" );
		fprintf( fp, "%s\n", fl );
	}
	vplist_free( &a );
}

static void
output_easy( FILE *fp, fields *f, char *tag, char *ristag, int level )
{
	char *value = fields_findv( f, level, FIELDS_CHRP, tag );
	if ( value ) fprintf( fp, "%s  - %s\n", ristag, value );
}

static void
output_easyall( FILE *fp, fields *f, char *tag, char *ristag, int level )
{
	vplist a;
	int i;
	vplist_init( &a );
	fields_findv_each( f, level, FIELDS_CHRP, &a, tag );
	for ( i=0; i<a.n; ++i )
		fprintf( fp, "%s  - %s\n", ristag, (char *) vplist_get( &a, i ) );
	vplist_free( &a );
}

static void
output_allpeople( FILE *fp, fields *f, int type )
{
	output_people(  fp, f, "AUTHOR",      "AU", LEVEL_MAIN   );
	output_easyall( fp, f, "AUTHOR:CORP", "AU", LEVEL_MAIN   );
	output_easyall( fp, f, "AUTHOR:ASIS", "AU", LEVEL_MAIN   );
	output_people(  fp, f, "AUTHOR",      "A2", LEVEL_HOST   );
	output_easyall( fp, f, "AUTHOR:CORP", "A2", LEVEL_HOST   );
	output_easyall( fp, f, "AUTHOR:ASIS", "A2", LEVEL_HOST   );
	output_people(  fp, f, "AUTHOR",      "A3", LEVEL_SERIES );
	output_easyall( fp, f, "AUTHOR:CORP", "A3", LEVEL_SERIES );
	output_easyall( fp, f, "AUTHOR:ASIS", "A3", LEVEL_SERIES );
	output_people(  fp, f, "EDITOR",      "ED", LEVEL_MAIN   );
	output_easyall( fp, f, "EDITOR:CORP", "ED", LEVEL_MAIN   );
	output_easyall( fp, f, "EDITOR:ASIS", "ED", LEVEL_MAIN   );
	if ( type_is_element( type ) ) {
		output_people(  fp, f, "EDITOR",      "ED", LEVEL_HOST   );
		output_easyall( fp, f, "EDITOR:CORP", "ED", LEVEL_HOST   );
		output_easyall( fp, f, "EDITOR:ASIS", "ED", LEVEL_HOST   );
	} else {
		output_people(  fp, f, "EDITOR",      "A3", LEVEL_HOST   );
		output_easyall( fp, f, "EDITOR:CORP", "A3", LEVEL_HOST   );
		output_easyall( fp, f, "EDITOR:ASIS", "A3", LEVEL_HOST   );
	}
	output_people(  fp, f, "EDITOR",      "A3", LEVEL_SERIES );
	output_easyall( fp, f, "EDITOR:CORP", "A3", LEVEL_SERIES );
	output_easyall( fp, f, "EDITOR:ASIS", "A3", LEVEL_SERIES );
}

static void
risout_write( fields *f, FILE *fp, param *p, unsigned long refnum )
{
	int type;
	type = get_type( f, p );
	output_type( fp, type, p );

	output_allpeople( fp, f, type );

	output_date( fp, f );

	output_alltitles( fp, f, type );

	output_pages( fp, f );
	output_easy( fp, f, "VOLUME",             "VL", LEVEL_ANY );
	output_easy( fp, f, "ISSUE",              "IS", LEVEL_ANY );
	output_easy( fp, f, "NUMBER",             "IS", LEVEL_ANY );
	output_easy( fp, f, "EDITION",            "ET", LEVEL_ANY );
	output_easy( fp, f, "NUMVOLUMES",         "NV", LEVEL_ANY );
	output_easy( fp, f, "AUTHORADDRESS",      "AD", LEVEL_ANY );
	output_easy( fp, f, "PUBLISHER",          "PB", LEVEL_ANY );
	output_easy( fp, f, "DEGREEGRANTOR",      "PB", LEVEL_ANY );
	output_easy( fp, f, "DEGREEGRANTOR:ASIS", "PB", LEVEL_ANY );
	output_easy( fp, f, "DEGREEGRANTOR:CORP", "PB", LEVEL_ANY );
	output_easy( fp, f, "ADDRESS",            "CY", LEVEL_ANY );
	output_keywords( fp, f );
	output_easy( fp, f, "ABSTRACT",           "AB", LEVEL_ANY );
	output_easy( fp, f, "CALLNUMBER",         "CN", LEVEL_ANY );
	output_easy( fp, f, "ISSN",               "SN", LEVEL_ANY );
	output_easy( fp, f, "ISBN",               "SN", LEVEL_ANY );
	output_easyall( fp, f, "URL",             "UR", LEVEL_ANY );
	output_easyall( fp, f, "DOI",             "DO", LEVEL_ANY );
	output_file(    fp, f, "FILEATTACH",      "L1", LEVEL_ANY );
	output_file(    fp, f, "FIGATTACH",       "L4", LEVEL_ANY );
	output_easy( fp, f, "CAPTION",            "CA", LEVEL_ANY );
	output_pmid( fp, f );
	output_pmc( fp, f );
	output_arxiv( fp, f );
	output_jstor( fp, f );
	output_easy( fp, f, "LANGUAGE",           "LA", LEVEL_ANY );
	output_easy( fp, f, "NOTES",              "N1", LEVEL_ANY );
	output_easy( fp, f, "REFNUM",             "ID", LEVEL_ANY );
	output_thesishint( fp, type );
	fprintf( fp, "ER  - \n" );
	fflush( fp );
}

static void
risout_writeheader( FILE *outptr, param *p )
{
	if ( p->utf8bom ) utf8_writebom( outptr );
}

