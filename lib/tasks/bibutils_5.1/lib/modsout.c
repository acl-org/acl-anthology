/*
 * modsout.c
 *
 * Copyright (c) Chris Putnam 2003-2013
 *
 * Source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "is_ws.h"
#include "newstr.h"
#include "charsets.h"
#include "newstr_conv.h"
#include "fields.h"
#include "iso639_2.h"
#include "utf8.h"
#include "modsout.h"
#include "modstypes.h"
#include "marc.h"

void
modsout_initparams( param *p, const char *progname )
{
	p->writeformat      = BIBL_MODSOUT;
	p->format_opts      = 0;
	p->charsetout       = BIBL_CHARSET_UNICODE;
	p->charsetout_src   = BIBL_SRC_DEFAULT;
	p->latexout         = 0;
	p->utf8out          = 1;
	p->utf8bom          = 1;
	p->xmlout           = 1;
	p->nosplittitle     = 0;
	p->verbose          = 0;
	p->addcount         = 0;
	p->singlerefperfile = 0;

	p->headerf = modsout_writeheader;
	p->footerf = modsout_writefooter;
	p->writef  = modsout_write;
}

static int
increment_level( int level, int amt )
{
	if ( level > -1 ) return level+amt;
	else return level-amt;
}

static void
output_tab0( FILE *outptr, int level )
{
	int i;
	level = abs( level );
	for ( i=0; i<=level; ++i ) fprintf( outptr, "    " );
}

static void
output_tab1( FILE *outptr, int level, char *tag )
{
	output_tab0( outptr, level );
	fprintf( outptr, "%s", tag );
}

static void
output_tab2_attrib( FILE *outptr, int level, char *tag, char *data, 
	char *attrib, char *type, int cr )
{
	output_tab0( outptr, level );
	fprintf( outptr, "<%s", tag );
	if ( attrib && type ) fprintf( outptr, " %s=\"%s\"", attrib, type );
	fprintf( outptr, ">%s</%s>", data, tag );
	if ( cr ) fprintf( outptr, "\n" );
}

static void
output_tab4( FILE *outptr, int level, char *tag, char *aname, char *avalue,
		char *data, int cr )
{
	output_tab0( outptr, level );
	fprintf( outptr, "<%s %s=\"%s\">%s</%s>", tag,aname,avalue,data,tag);
	if ( cr ) fprintf( outptr, "\n" );
}

static void
output_tab6( FILE *outptr, int level, char *tag, char *aname, char *avalue,
		char *bname, char *bvalue, char *data, int cr )
{
	output_tab0( outptr, level );
	fprintf( outptr, "<%s %s=\"%s\" %s=\"%s\">%s</%s>", tag,aname,avalue,bname,bvalue,data,tag);
	if ( cr ) fprintf( outptr, "\n" );
}

static void
output_fill2( FILE *outptr, int level, char *tag, fields *f, int n, int cr )
{
	char *value;
	if ( n!=-1 ) {
		value = fields_value( f, n, FIELDS_CHRP );
		output_tab2_attrib( outptr, level, tag, value, 
			NULL, NULL, cr );
		fields_setused( f, n );
	}
}

static void
output_fill4( FILE *outptr, int level, char *tag, char *aname, char *avalue,
		fields *f, int n, int cr )
{
	char *value;
	if ( n!=-1 ) {
		value = fields_value( f, n, FIELDS_CHRP );
		output_tab4( outptr, level, tag, aname, avalue,
				value, cr );
		fields_setused( f, n );
	}
}

/*
 * Find the positions of all convert.internal tags and store the
 * locations in convert.code.
 *
 * Return number of the tags found
 */
static int
find_alltags( fields *f, convert *parts, int nparts, int level )
{
	int i, n=0;
	for ( i=0; i<nparts; ++i ) {
		parts[i].code = fields_find( f, parts[i].internal, level );
		n += ( parts[i].code!=-1 );
	}
	return n;
}

static void
output_title( fields *f, FILE *outptr, int level )
{
	int ttl    = fields_find( f, "TITLE", level );
	int subttl = fields_find( f, "SUBTITLE", level );
	int shrttl = fields_find( f, "SHORTTITLE", level );
	int parttl = fields_find( f, "PARTTITLE", level );

	output_tab1( outptr, level, "<titleInfo>\n" );
	output_fill2( outptr, increment_level(level,1), "title", f, ttl, 1 );
	output_fill2( outptr, increment_level(level,1), "subTitle", f, subttl, 1 );
	output_fill2( outptr, increment_level(level,1), "partName", f, parttl, 1 );
	if ( ttl==-1 && subttl==-1 )
		output_tab1( outptr, increment_level(level,1), "<title/>\n" );
	output_tab1( outptr, level, "</titleInfo>\n" );

	/* output shorttitle if it's different from normal title */
	if ( shrttl!=-1 ) {
		if ( ttl==-1 || subttl!=-1 ||
			strcmp(f->data[ttl].data,f->data[shrttl].data) ) {
			output_tab1( outptr, level, 
					"<titleInfo type=\"abbreviated\">\n" );
			output_fill2( outptr, level+1, "title", f, shrttl,1);
			output_tab1( outptr, level, "</titleInfo>\n" );
		}
		fields_setused( f, shrttl );
	}
}

static void
output_personalstart( FILE *outptr, int level )
{
	int j;
	for ( j=0; j<=level; ++j ) fprintf( outptr, "    " );
		fprintf( outptr, "<name type=\"personal\">\n" );
}

static void
output_name( FILE *outptr, char *p, int level )
{
	newstr family, part, suffix;
	int n=0;

	newstrs_init( &family, &part, &suffix, NULL );

	while ( *p && *p!='|' ) newstr_addchar( &family, *p++ );
	if ( *p=='|' ) p++;

	while ( *p ) {
		while ( *p && *p!='|' ) newstr_addchar( &part, *p++ );
		/* truncate periods from "A. B. Jones" names */
		if ( part.len ) {
			if ( part.len==2 && part.data[1]=='.' ) {
				part.len=1;
				part.data[1]='\0';
			}
			if ( n==0 ) output_personalstart( outptr, level );
			output_tab4( outptr, increment_level(level,1), "namePart", "type", 
					"given", part.data, 1 );
			n++;
		}
		if ( *p=='|' ) {
			p++;
			if ( *p=='|' ) {
				p++;
				while ( *p && *p!='|' ) newstr_addchar( &suffix, *p++ );
			}
			newstr_empty( &part );
		}
	}

	if ( family.len ) {
		if ( n==0 ) output_personalstart( outptr, level );
		output_tab4( outptr, increment_level(level,1), "namePart", "type", "family",
				family.data, 1 );
	}

	if ( suffix.len ) {
		if ( n==0 ) output_personalstart( outptr, level );
		output_tab4( outptr, increment_level(level,1), "namePart", "type", "suffix",
				suffix.data, 1 );
	}

	newstrs_free( &part, &family, &suffix, NULL );
}


/* MODS v 3.4
 *
 * <name [type="corporation"/type="conference"]>
 *    <namePart></namePart>
 *    <displayForm></displayForm>
 *    <affiliation></affiliation>
 *    <role>
 *        <roleTerm [authority="marcrealtor"] type="text"></roleTerm>
 *    </role>
 *    <description></description>
 * </name>
 */

#define NO_AUTHORITY (0)
#define MARC_AUTHORITY (1)

static void
output_names( fields *f, FILE *outptr, int level )
{
	convert   names[] = {
	  { "author",                              "AUTHOR",          MARC_AUTHORITY },
	  { "editor",                              "EDITOR",          MARC_AUTHORITY },
	  { "annotator",                           "ANNOTATOR",       MARC_AUTHORITY },
	  { "artist",                              "ARTIST",          MARC_AUTHORITY },
	  { "author",                              "2ND_AUTHOR",      MARC_AUTHORITY },
	  { "author",                              "3RD_AUTHOR",      MARC_AUTHORITY },
	  { "author",                              "SUB_AUTHOR",      MARC_AUTHORITY },
	  { "author",                              "COMMITTEE",       MARC_AUTHORITY },
	  { "author",                              "COURT",           MARC_AUTHORITY },
	  { "author",                              "LEGISLATIVEBODY", MARC_AUTHORITY },
	  { "author of afterword, colophon, etc.", "AFTERAUTHOR",     MARC_AUTHORITY },
	  { "author of introduction, etc.",        "INTROAUTHOR",     MARC_AUTHORITY },
	  { "cartographer",                        "CARTOGRAPHER",    MARC_AUTHORITY },
	  { "collaborator",                        "COLLABORATOR",    MARC_AUTHORITY },
	  { "commentator",                         "COMMENTATOR",     MARC_AUTHORITY },
	  { "compiler",                            "COMPILER",        MARC_AUTHORITY },
	  { "degree grantor",                      "DEGREEGRANTOR",   MARC_AUTHORITY },
	  { "director",                            "DIRECTOR",        MARC_AUTHORITY },
	  { "event",                               "EVENT",           NO_AUTHORITY   },
	  { "inventor",                            "INVENTOR",        MARC_AUTHORITY },
	  { "organizer of meeting",                "ORGANIZER",       MARC_AUTHORITY },
	  { "patent holder",                       "ASSIGNEE",        MARC_AUTHORITY },
	  { "performer",                           "PERFORMER",       MARC_AUTHORITY },
	  { "producer",                            "PRODUCER",        MARC_AUTHORITY },
	  { "recipient",                           "RECIPIENT",       MARC_AUTHORITY },
	  { "redactor",                            "REDACTOR",        MARC_AUTHORITY },
	  { "reporter",                            "REPORTER",        MARC_AUTHORITY },
	  { "sponsor",                             "SPONSOR",         MARC_AUTHORITY },
	  { "translator",                          "TRANSLATOR",      MARC_AUTHORITY },
	  { "writer",                              "WRITER",          MARC_AUTHORITY },
	};
	int i, n, nfields, ntypes = sizeof( names ) / sizeof( convert );
	int f_asis, f_corp, f_conf;
	newstr role;

	newstr_init( &role );
	nfields = fields_num( f );
	for ( n=0; n<ntypes; ++n ) {
		for ( i=0; i<nfields; ++i ) {
			if ( fields_level( f, i )!=level ) continue;
			if ( f->data[i].len==0 ) continue;
			f_asis = f_corp = f_conf = 0;
			newstr_strcpy( &role, f->tag[i].data );
			if ( newstr_findreplace( &role, ":ASIS", "" )) f_asis=1;
			if ( newstr_findreplace( &role, ":CORP", "" )) f_corp=1;
			if ( newstr_findreplace( &role, ":CONF", "" )) f_conf=1;
			if ( strcasecmp( role.data, names[n].internal ) )
				continue;
			if ( f_asis ) {
				output_tab0( outptr, level );
				fprintf( outptr, "<name>\n" );
				output_fill2( outptr, increment_level(level,1), "namePart", f, i, 1 );
			} else if ( f_corp ) {
				output_tab0( outptr, level );
				fprintf( outptr, "<name type=\"corporate\">\n" );
				output_fill2( outptr, increment_level(level,1), "namePart", f, i, 1 );
			} else if ( f_conf ) {
				output_tab0( outptr, level );
				fprintf( outptr, "<name type=\"conference\">\n" );
				output_fill2( outptr, increment_level(level,1), "namePart", f, i, 1 );
			} else {
				output_name(outptr, f->data[i].data, level);
			}
			output_tab1( outptr, increment_level(level,1), "<role>\n" );
			output_tab1( outptr, increment_level(level,2), "<roleTerm" );
			if ( names[n].code & MARC_AUTHORITY )
				fprintf( outptr, " authority=\"marcrelator\"");
			fprintf( outptr, " type=\"text\">");
			fprintf( outptr, "%s", names[n].mods );
			fprintf( outptr, "</roleTerm>\n");
			output_tab1( outptr, increment_level(level,1), "</role>\n" );
			output_tab1( outptr, level, "</name>\n" );
			fields_setused( f, i );
		}
	}
	newstr_free( &role );
}

static int
output_finddateissued( fields *f, int level, int pos[] )
{
	char      *src_names[] = { "YEAR", "MONTH", "DAY", "DATE" };
	char      *alt_names[] = { "PARTYEAR", "PARTMONTH", "PARTDAY", "PARTDATE" };
	int       i, found = -1, ntypes = 4;

	for ( i=0; i<ntypes; ++i ) {
		pos[i] = fields_find( f, src_names[i], level );
		if ( pos[i]!=-1 ) found = pos[i];
	}
	/* for LEVEL_MAIN, do what it takes to find a date */
	if ( found==-1 && level==0 ) {
		for ( i=0; i<ntypes; ++i ) {
			pos[i] = fields_find( f, src_names[i], -1 );
			if ( pos[i]!=-1 ) found = pos[i];
		}
	}
	if ( found==-1 && level==0 ) {
		for ( i=0; i<ntypes; ++i ) {
			pos[i] = fields_find( f, alt_names[i], -1 );
			if ( pos[i]!=-1 ) found = pos[i];
		}
	}
	return found;
}

static void
output_datepieces( fields *f, FILE *outptr, int pos[4] )
{
	int nprinted = 0, i;
	for ( i=0; i<3 && pos[i]!=-1; ++i ) {
		if ( nprinted>0 ) fprintf( outptr, "-" );
		if ( i>0 && f->data[pos[i]].len==1 )
			fprintf( outptr, "0" ); /*zero pad Jan,Feb,etc*/
		fprintf( outptr,"%s",f->data[pos[i]].data );
		nprinted++;
		fields_setused( f, pos[i] );
	}
}

static void
output_dateall( fields *f, FILE *outptr, int pos )
{
	fprintf( outptr, "%s", f->data[pos].data );
	fields_setused( f, pos );
}

static void
output_dateissued( fields *f, FILE *outptr, int level, int pos[4] )
{
	output_tab1( outptr, increment_level(level,1), "<dateIssued>" );
	if ( pos[0]!=-1 || pos[1]!=-1 || pos[2]!=-1 ) {
		output_datepieces( f, outptr, pos );
	} else {
		output_dateall( f, outptr, pos[3] );
	}
	fprintf( outptr, "</dateIssued>\n" );
}

static void
output_origin( fields *f, FILE *outptr, int level )
{
	convert origin[] = {
		{ "issuance",	  "ISSUANCE",	0 },
		{ "publisher",	  "PUBLISHER",	0 },
		{ "place",	  "ADDRESS",	1 },
		{ "edition",	  "EDITION",	0 },
		{ "dateCaptured", "URLDATE",    0 }
	};
	int n, ntypes = sizeof( origin ) / sizeof ( convert );
	int found, datefound, pos[5], date[4];

	/* find all information to be outputted */
	found = -1;
	for ( n=0; n<ntypes; ++n ) {
		pos[n] = fields_find( f, origin[n].internal, level );
		if ( pos[n]!=-1 ) found = pos[n];
	}
	datefound = output_finddateissued( f, level, date );
	if ( found==-1 && datefound==-1 ) return;

	output_tab1( outptr, level, "<originInfo>\n" );
	output_fill2( outptr, increment_level(level,1), "issuance", f, pos[0], 1 );
	if ( datefound!=-1 ) output_dateissued( f, outptr, level, date );

	for ( n=1; n<ntypes; n++ ) {
		if ( pos[n]==-1 ) continue;
		output_tab0( outptr, increment_level(level,1) );
		fprintf( outptr, "<%s", origin[n].mods );
		fprintf( outptr, ">" );
		if ( origin[n].code ) {
			fprintf( outptr, "\n" );
			output_fill4( outptr, increment_level(level,2), 
				"placeTerm", "type", "text", f, pos[n], 1 );
			output_tab0( outptr, increment_level(level,1) );
		} else {
			fprintf( outptr, "%s", f->data[pos[n]].data );
			fields_setused( f, pos[n] );
		}
		fprintf( outptr, "</%s>\n", origin[n].mods );
	}
	output_tab1( outptr, level, "</originInfo>\n" );
}

static void
output_language_core( fields *f, int n, FILE *outptr, char *tag, int level )
{
	newstr usetag;
	char *lang, *code;
	lang = fields_value( f, n, FIELDS_CHRP );
	code = iso639_2_from_language( lang );
	newstr_init( &usetag );
	newstr_addchar( &usetag, '<' );
	newstr_strcat( &usetag, tag );
	newstr_strcat( &usetag, ">\n" );
	output_tab1( outptr, level, usetag.data );
	output_fill4( outptr, increment_level(level,1),
		"languageTerm", "type", "text", f, n, 1 );
	if ( code ) {
		output_tab6( outptr, increment_level(level,1),
			"languageTerm", "type", "code", "authority", "iso639-2b",
			code, 1 );
	}
	newstr_strcpy( &usetag, "</" );
	newstr_strcat( &usetag, tag );
	newstr_strcat( &usetag, ">\n" );
	output_tab1( outptr, level, usetag.data );
	newstr_free( &usetag );
}

static void
output_language( fields *f, FILE *outptr, int level )
{
	int n;
	n = fields_find( f, "LANGUAGE", level );
	if ( n!=-1 )
		output_language_core( f, n, outptr, "language", level );
}

static void
output_description( fields *f, FILE *outptr, int level )
{
	int n = fields_find( f, "DESCRIPTION", level );
	if ( n!=-1 ) {
		output_tab1( outptr, level, "<physicalDescription>\n" );
		output_fill2( outptr, increment_level(level,1), "note", f, n, 1 );
		output_tab1( outptr, level, "</physicalDescription>\n" );
	}
}

static void
output_toc( fields *f, FILE *outptr, int level )
{
	int n = fields_find( f, "CONTENTS", level );
	output_fill2( outptr, level, "tableOfContents", f, n, 1 );
}

/* detail output
 *
 * for example:
 *
 * <detail type="volume"><number>xxx</number></detail
 */
static void
mods_output_detail( fields *f, FILE *outptr, int item, char *item_name,
		int level )
{
	if ( item==-1 ) return;
	output_tab0( outptr, increment_level( level, 1 ) );
	fprintf( outptr, "<detail type=\"%s\"><number>%s</number></detail>\n", 
			item_name, f->data[item].data );
	fields_setused( f, item );
}


/* extents output
 *
 * <extent unit="page">
 * 	<start>xxx</start>
 * 	<end>xxx</end>
 * </extent>
 */
static void
mods_output_extents( fields *f, FILE *outptr, int start, int end,
		int total, char *extype, int level )
{
	output_tab0( outptr, increment_level(level,1) );
	fprintf( outptr, "<extent unit=\"%s\">\n", extype);
	output_fill2( outptr, increment_level(level,2), "start", f, start, 1 );
	output_fill2( outptr, increment_level(level,2), "end", f, end, 1 );
	output_fill2( outptr, increment_level(level,2), "total", f, total, 1 );
	output_tab1 ( outptr, increment_level(level,1), "</extent>\n" );
}

static void
try_output_partheader( FILE *outptr, int wrote_header, int level )
{
	if ( !wrote_header ) output_tab1( outptr, level, "<part>\n" );
}

static void
try_output_partfooter( FILE *outptr, int wrote_header, int level )
{
	if ( wrote_header ) output_tab1( outptr, level, "</part>\n" );
}

/* part date output
 *
 * <date>xxxx-xx-xx</date>
 *
 */
static int
output_partdate( fields *f, FILE *outptr, int level, int wrote_header )
{
	convert parts[3] = {
		{ "",	"PARTYEAR",                -1 },
		{ "",	"PARTMONTH",               -1 },
		{ "",	"PARTDAY",                 -1 },
	};
	int nparts = sizeof(parts)/sizeof(parts[0]);

	if ( !find_alltags( f, parts, nparts, level ) ) return 0;

	try_output_partheader( outptr, wrote_header, level );
	output_tab1( outptr, increment_level(level,1), "<date>" );

	if ( parts[0].code!=-1 ) {
		fprintf( outptr, "%s", f->data[ parts[0].code ].data);
		fields_setused( f, parts[0].code );
	} else fprintf( outptr, "XXXX" );

	if ( parts[1].code!=-1 ) {
		fprintf( outptr, "-%s", f->data[parts[1].code].data );
		fields_setused( f, parts[1].code );
	}

	if ( parts[2].code!=-1 ) {
		if ( parts[1].code!=-1 ) fprintf( outptr, "-" );
		else fprintf( outptr, "-XX-" );
		fprintf( outptr, "%s", f->data[parts[2].code].data );
		fields_setused( f, parts[2].code );
	}

	fprintf( outptr,"</date>\n");

	return 1;
}

static int
output_partpages( fields *f, FILE *outptr, int level, int wrote_header )
{
	convert parts[4] = {
		{ "",  "PAGESTART",                -1 },
		{ "",  "PAGEEND",                  -1 },
		{ "",  "PAGES",                    -1 },
		{ "",  "TOTALPAGES",               -1 }
	};
	int nparts = sizeof(parts)/sizeof(parts[0]);

	if ( !find_alltags( f, parts, nparts, level ) ) return 0;

	try_output_partheader( outptr, wrote_header, level );

	/* If PAGESTART or PAGEEND are  undefined */
	if ( parts[0].code==-1 || parts[1].code==-1 ) {
		if ( parts[0].code!=-1 )
			mods_output_detail( f, outptr, parts[0].code,
				"page", level );
		if ( parts[1].code!=-1 )
			mods_output_detail( f, outptr, parts[1].code,
				"page", level );
		if ( parts[2].code!=-1 )
			mods_output_detail( f, outptr, parts[2].code,
				"page", level );
		if ( parts[3].code!=-1 )
			mods_output_extents( f, outptr, -1, -1,
					parts[3].code, "page", level );
	}
	/* If both PAGESTART and PAGEEND are defined */
	else {
		mods_output_extents( f, outptr, parts[0].code, 
			parts[1].code, parts[3].code, "page", level );
	}

	return 1;
}

static int
output_partelement( fields *f, FILE *outptr, int level, int wrote_header )
{
	convert parts[] = {
		{ "volume",          "VOLUME",          -1 },
		{ "section",         "SECTION",         -1 },
		{ "issue",           "ISSUE",           -1 },
		{ "number",          "NUMBER",          -1 },
		{ "publiclawnumber", "PUBLICLAWNUMBER", -1 },
		{ "session",         "SESSION",         -1 },
		{ "articlenumber",   "ARTICLENUMBER",   -1 },
		{ "part",            "PART",            -1 },
		{ "chapter",         "CHAPTER",         -1 },
		{ "report number",   "REPORTNUMBER",    -1 },
	};
	int i, nparts = sizeof( parts ) / sizeof( convert ), n;

	n = fields_find( f, "NUMVOLUMES", level );
	if ( !find_alltags( f, parts, nparts, level ) && n==-1 ) return 0;
	try_output_partheader( outptr, wrote_header, level );

	for ( i=0; i<nparts; ++i ) {
		if ( parts[i].code==-1 ) continue;
		mods_output_detail( f, outptr, parts[i].code, parts[i].mods,
				level );
	}

	if ( n!=-1 ) {
		output_tab1( outptr, level, "<extent unit=\"volumes\">\n" );
		output_fill2( outptr, increment_level(level,1), "total", f, n, 1 );
		output_tab1( outptr, level, "</extent>\n" );
	}

	return 1;
}

static void
output_part( fields *f, FILE *outptr, int level )
{
	int wrote_hdr;
	wrote_hdr  = output_partdate( f, outptr, level, 0 );
	wrote_hdr += output_partelement( f, outptr, level, wrote_hdr );
	wrote_hdr += output_partpages( f, outptr, level, wrote_hdr );
	try_output_partfooter( outptr, wrote_hdr, level );
}

static void
output_recordInfo( fields *f, FILE *outptr, int level )
{
	int n;
	n = fields_find( f, "LANGCATALOG", level );
	if ( n!=-1 ) {
		output_tab1( outptr, level, "<recordInfo>\n" );
		output_language_core( f, n, outptr, "languageOfCataloging", increment_level(level,1) );
		output_tab1( outptr, level, "</recordInfo>\n" );
	}
}

static void
output_genre( fields *f, FILE *outptr, int level )
{
	int i, ismarc, n;
	char *value;
	n = fields_num( f );
	for ( i=0; i<n; ++i ) {
		if ( fields_level( f, i ) != level ) continue;
		if ( !fields_match_tag( f, i, "GENRE" ) &&
		     !fields_match_tag( f, i, "NGENRE" ) )
			continue;
		value = fields_value( f, i, FIELDS_CHRP );
		if ( marc_findgenre( value )!=-1 ) ismarc = 1;
		else ismarc = 0;
		output_tab1( outptr, level, "<genre" );
		if ( ismarc ) 
			fprintf( outptr, " authority=\"marcgt\"" );
		fprintf( outptr, ">%s</genre>\n", value );
		fields_setused( f, i );
	}
}

static void
output_typeresource( fields *f, FILE *outptr, int level )
{
	int n, ismarc = 0;
	char *value;
	n = fields_find( f, "RESOURCE", level );
	if ( n!=-1 ) {
		value = fields_value( f, n, FIELDS_CHRP );
		if ( marc_findresource( value )!=-1 ) ismarc = 1;
		if ( !ismarc ) {
			fprintf( stderr, "Illegal typeofResource = '%s'\n", value );
		} else {
			output_fill2( outptr, level, "typeOfResource", f, n, 1 );
		}
		fields_setused( f, n );
	}
}

static void
output_type( fields *f, FILE *outptr, int level )
{
	int n = fields_find( f, "INTERNAL_TYPE", 0 );
	if ( n!=-1 ) fields_setused( f, n );
	output_typeresource( f, outptr, level );
	output_genre( f, outptr, level );
}

static void
output_abs( fields *f, FILE *outptr, int level )
{
	int nabs = fields_find( f, "ABSTRACT", level );
	output_fill2( outptr, level, "abstract", f, nabs, 1 );
}

static void
output_notes( fields *f, FILE *outptr, int level )
{
	int i, n;
	char *t;
	n = fields_num( f );
	for ( i=0; i<n; ++i ) {
		if ( fields_level( f, i ) != level ) continue;
		t = fields_tag( f, i, FIELDS_CHRP_NOUSE );
		if ( !strcasecmp( t, "NOTES" ) )
			output_fill2( outptr, level, "note", f, i, 1 );
		else if ( !strcasecmp( t, "PUBSTATE" ) )
			output_fill4( outptr, level, "note", "type", "publication status", f, i, 1 );
		else if ( !strcasecmp( t, "ANNOTE" ) )
			output_fill2( outptr, level, "bibtex-annote", f, i, 1 );
		else if ( !strcasecmp( t, "TIMESCITED" ) )
			output_fill4( outptr, level, "note", "type", "times cited", f, i, 1 );
		else if ( !strcasecmp( t, "ANNOTATION" ) )
			output_fill4( outptr, level, "note", "type", "annotation", f, i, 1 );
		else if ( !strcasecmp( t, "ADDENDUM" ) )
			output_fill4( outptr, level, "note", "type", "addendum", f, i, 1 );
		else if ( !strcasecmp( t, "BIBKEY" ) )
			output_fill4( outptr, level, "note", "type", "bibliography key", f, i, 1 );
	}
}

static void
output_key( fields *f, FILE *outptr, int level )
{
	int i, n;
	n = fields_num( f );
	for ( i=0; i<n; ++i ) {
		if ( fields_level( f, i ) != level ) continue;
		if ( !strcasecmp( f->tag[i].data, "KEYWORD" ) ) {
			output_tab1( outptr, level, "<subject>\n" );
			output_fill2( outptr, increment_level(level,1), "topic", f, i, 1 );
			output_tab1( outptr, level, "</subject>\n" );
		}
	}
}

static void
output_sn( fields *f, FILE *outptr, int level )
{
	convert sn_types[] = {
		{ "isbn",      "ISBN",      0 },
		{ "lccn",      "LCCN",      0 },
		{ "issn",      "ISSN",      0 },
		{ "citekey",   "REFNUM",    0 },
		{ "doi",       "DOI",       0 },
		{ "eid",       "EID",       0 },
		{ "eprint",    "EPRINT",    0 },
		{ "eprinttype","EPRINTTYPE",0 },
		{ "pubmed",    "PMID",      0 },
		{ "medline",   "MEDLINE",   0 },
		{ "pii",       "PII",       0 },
		{ "arXiv",     "ARXIV",     0 },
		{ "isi",       "ISIREFNUM", 0 },
		{ "accessnum", "ACCESSNUM", 0 },
		{ "jstor",     "JSTOR",     0 },
		{ "isrn",      "ISRN",      0 },
	};
	int n, ntypes = sizeof( sn_types ) / sizeof( sn_types[0] );
	int found, i, nfields;

	found = fields_find ( f, "CALLNUMBER", level );
	output_fill2( outptr, level, "classification", f, found, 1 );

	for ( n=0; n<ntypes; ++n ) {
		found = fields_find( f, sn_types[n].internal, level );
		if ( found==-1 ) continue;
		output_tab0( outptr, level );
		fprintf( outptr, "<identifier type=\"%s\">%s</identifier>\n",
				sn_types[n].mods,
				f->data[found].data
		       );
		fields_setused( f, found );
	}
	nfields = fields_num( f );
	for ( i=0; i<nfields; ++i ) {
		if ( f->level[i]!=level ) continue;
		if ( !strcasecmp( f->tag[i].data, "SERIALNUMBER" ) ) {
			output_tab0( outptr, level );
			fprintf( outptr, "<identifier type=\"%s\">%s</identifier>\n",
				"serial number", f->data[i].data );
			fields_setused( f, i );
		}
	}
}

static void
output_url( fields *f, FILE *outptr, int level )
{
	int location = fields_find( f, "LOCATION", level );
	int url = fields_find( f, "URL", level );
	int fileattach = fields_find( f, "FILEATTACH", level );
	int pdflink = fields_find( f, "PDFLINK", level );
	int i, n;
	if ( url==-1 && location==-1 && pdflink==-1 && fileattach==-1 ) return;
	output_tab1( outptr, level, "<location>\n" );
	n = fields_num( f );
	for ( i=0; i<n; ++i ) {
		if ( f->level[i]!=level ) continue;
		if ( !strcasecmp( f->tag[i].data, "URL" ) ) {
			output_fill2( outptr, increment_level(level,1), "url", f, i, 1 );
		}
	}
	for ( i=0; i<n; ++i ) {
		if ( f->level[i]!=level ) continue;
		if ( !strcasecmp( f->tag[i].data, "PDFLINK" ) ) {
			output_fill2( outptr, increment_level(level,1), "url",
				/*"urlType", "pdf",*/ f, i, 1 );
		}
	}
	for ( i=0; i<n; ++i ) {
		if ( f->level[i]!=level ) continue;
		if ( !strcasecmp( f->tag[i].data, "FILEATTACH" ) ){
			output_tab0( outptr, increment_level(level,1) );
			fprintf( outptr, "<url displayLabel=\"Electronic full text\" access=\"raw object\">" );
			fprintf( outptr, "%s</url>\n", f->data[i].data );
			fields_setused( f, i );
		}
	}
	if ( location!=-1 )
		output_fill2( outptr, increment_level(level,1), "physicalLocation", f, 
				location, 1 );
	output_tab1( outptr, level, "</location>\n" );
}

/* refnum should start with a non-number and not include spaces -- ignore this */
static void
output_refnum( fields *f, int n, FILE *outptr )
{
	char *p = fields_value( f, n, FIELDS_CHRP_NOUSE );
/*	if ( p && ((*p>='0' && *p<='9') || *p=='-' || *p=='_' ))
		fprintf( outptr, "ref" );*/
	while ( p && *p ) {
		if ( !is_ws(*p) ) fprintf( outptr, "%c", *p );
/*		if ( (*p>='A' && *p<='Z') ||
		     (*p>='a' && *p<='z') ||
		     (*p>='0' && *p<='9') ||
		     (*p=='-') || (*p=='
		     (*p=='_') ) fprintf( outptr, "%c", *p );*/
		p++;
	}
}

static void
output_head( fields *f, FILE *outptr, int dropkey, unsigned long numrefs )
{
	int n;
	fprintf( outptr, "<mods");
	if ( !dropkey ) {
		n = fields_find( f, "REFNUM", 0 );
		if ( n!=-1 ) {
			fprintf( outptr, " ID=\"");
			output_refnum( f, n, outptr );
			fprintf( outptr, "\"");
		}
	}
	fprintf( outptr, ">\n" );
}

static int
original_items( fields *f, int level )
{
	int i, targetlevel, n;
	if ( level < 0 ) return 0;
	targetlevel = -( level + 2 );
	n = fields_num( f );
	for ( i=0; i<n; ++i ) {
		if ( fields_level( f, i ) == targetlevel )
			return targetlevel;
	}
	return 0;
}

static void
output_citeparts( fields *f, FILE *outptr, int level, int max )
{
	int orig_level;

	output_title(       f, outptr, level );
	output_names(       f, outptr, level );
	output_origin(      f, outptr, level );
	output_type(        f, outptr, level );
	output_language(    f, outptr, level );
	output_description( f, outptr, level );

	if ( level >= 0 && level < max ) {
		output_tab0( outptr, level );
		fprintf( outptr, "<relatedItem type=\"host\">\n" );
		output_citeparts( f, outptr, increment_level(level,1), max );
		output_tab0( outptr, level );
		fprintf( outptr, "</relatedItem>\n");
	}
	/* Look for original item things */
	orig_level = original_items( f, level );
	if ( orig_level ) {
		output_tab0( outptr, level );
		fprintf( outptr, "<relatedItem type=\"original\">\n" );
		output_citeparts( f, outptr, orig_level, max );
		output_tab0( outptr, level );
		fprintf( outptr, "</relatedItem>\n" );
	}
	output_abs(        f, outptr, level );
	output_notes(      f, outptr, level );
	output_toc(        f, outptr, level );
	output_key(        f, outptr, level );
	output_sn(         f, outptr, level );
	output_url(        f, outptr, level );
	output_part(       f, outptr, level );

	output_recordInfo( f, outptr, level );
}

static void
modsout_report_unused_tags( fields *f, param *p, unsigned long numrefs )
{
	int i, n, nwritten, nunused = 0, level;
	char *tag, *value;
	n = fields_num( f );
	for ( i=0; i<n; ++i ) {
		if ( fields_used( f, i ) ) continue;
		nunused++;
	}
	if ( nunused ) {
		if ( p->progname ) fprintf( stderr, "%s: ", p->progname );
		fprintf( stderr, "Reference %lu has unused tags.\n", numrefs+1 );
		/* Find author from level 0 */
		nwritten = 0;
		for ( i=0; i<n; ++i ) {
			if ( fields_level( f, i ) != 0 ) continue;
			tag = fields_tag( f, i, FIELDS_CHRP_NOUSE );
			if ( strncasecmp( tag, "AUTHOR", 6 ) ) continue;
			value = fields_value( f, i, FIELDS_CHRP_NOUSE );
			if ( nwritten==0 ) fprintf( stderr, "\tAuthor(s) (level=0):\n" );
			fprintf( stderr, "\t\t'%s'\n", value );
			nwritten++;
		}
		nwritten = 0;
		for ( i=0; i<n; ++i ) {
			if ( fields_level( f, i ) != 0 ) continue;
			tag = fields_tag( f, i, FIELDS_CHRP_NOUSE );
			if ( strcasecmp( tag, "YEAR" ) && strcasecmp( tag, "PARTYEAR" ) ) continue;
			value = fields_value( f, i, FIELDS_CHRP_NOUSE );
			if ( nwritten==0 ) fprintf( stderr, "\tYear(s) (level=0):\n" );
			fprintf( stderr, "\t\t'%s'\n", value );
			nwritten++;
		}
		nwritten = 0;
		for ( i=0; i<n; ++i ) {
			if ( fields_level( f, i ) != 0 ) continue;
			tag = fields_tag( f, i, FIELDS_CHRP_NOUSE );
			if ( strncasecmp( tag, "TITLE", 5 ) ) continue;
			value = fields_value( f, i, FIELDS_CHRP_NOUSE );
			if ( nwritten==0 ) fprintf( stderr, "\tTitle(s) (level=0):\n" );
			fprintf( stderr, "\t\t'%s'\n", value );
			nwritten++;
		}
	
		fprintf( stderr, "\tUnused tags:\n" );
		for ( i=0; i<n; ++i ) {
			if ( fields_used( f, i ) ) continue;
			tag   = fields_tag(   f, i, FIELDS_CHRP_NOUSE );
			value = fields_value( f, i, FIELDS_CHRP_NOUSE );
			level = fields_level( f, i );
			fprintf( stderr, "\t\ttag: '%s' value: '%s' level: %d\n",
				tag, value, level );
		}
	}
}

void
modsout_write( fields *f, FILE *outptr, param *p, unsigned long numrefs )
{
	int max, dropkey;
	max = fields_maxlevel( f );
	dropkey = ( p->format_opts & MODSOUT_DROPKEY );

	output_head( f, outptr, dropkey, numrefs );
	output_citeparts( f, outptr, 0, max );
	modsout_report_unused_tags( f, p, numrefs );

	fprintf( outptr, "</mods>\n" );
	fflush( outptr );
}

void
modsout_writeheader( FILE *outptr, param *p )
{
	if ( p->utf8bom ) utf8_writebom( outptr );
	fprintf(outptr,"<?xml version=\"1.0\" encoding=\"%s\"?>\n",
			charset_get_xmlname( p->charsetout ) );
	fprintf(outptr,"<modsCollection xmlns=\"http://www.loc.gov/mods/v3\">\n");
}

void
modsout_writefooter( FILE *outptr )
{
	fprintf(outptr,"</modsCollection>\n");
	fflush( outptr );
}

