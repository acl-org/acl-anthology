/*
 * ebiin.c
 *
 * Copyright (c) Chris Putnam 2004-2013
 *
 * Program and source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include "is_ws.h"
#include "newstr.h"
#include "newstr_conv.h"
#include "fields.h"
#include "xml.h"
#include "xml_encoding.h"
#include "ebiin.h"

void
ebiin_initparams( param *p, const char *progname )
{
	p->readformat       = BIBL_EBIIN;
	p->charsetin        = BIBL_CHARSET_UNICODE;
	p->charsetin_src    = BIBL_SRC_DEFAULT;
	p->latexin          = 0;
	p->xmlin            = 1;
	p->utf8in           = 1;
	p->nosplittitle     = 0;
	p->verbose          = 0;
	p->addcount         = 0;
	p->output_raw       = BIBL_RAW_WITHMAKEREFID |
	                      BIBL_RAW_WITHCHARCONVERT;

	p->readf    = ebiin_readf;
	p->processf = ebiin_processf;
	p->cleanf   = NULL;
	p->typef    = NULL;
	p->convertf = NULL;
	p->all      = NULL;
	p->nall     = 0;

	list_init( &(p->asis) );
	list_init( &(p->corps) );

	if ( !progname ) p->progname = NULL;
	else p->progname = strdup( progname );
}

int
ebiin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset )
{
	newstr tmp;
	char *startptr = NULL, *endptr;
	int haveref = 0, inref = 0, file_charset = CHARSET_UNKNOWN, m;
	newstr_init( &tmp );
	while ( !haveref && newstr_fget( fp, buf, bufsize, bufpos, line ) ) {
		if ( line->data ) {
			m = xml_getencoding( line );
			if ( m!=CHARSET_UNKNOWN ) file_charset = m;
		}
		if ( line->data )
			startptr = xml_findstart( line->data, "Publication" );
		if ( startptr || inref ) {
			if ( inref ) newstr_strcat( &tmp, line->data );
			else {
				newstr_strcat( &tmp, startptr );
				inref = 1;
			}
			endptr = xml_findend( tmp.data, "Publication" );
			if ( endptr ) {
				newstr_segcpy( reference, tmp.data, endptr );
				haveref = 1;
			}
		}
	}
	newstr_free( &tmp );
	*fcharset = file_charset;
	return haveref;
}


static inline int
xml_hasdata( xml *node )
{
	if ( node && node->value && node->value->data ) return 1;
	return 0;
}

static inline char *
xml_data( xml *node )
{
	return node->value->data;
}


static inline int
xml_tagwithdata( xml *node, char *tag )
{
	if ( !xml_hasdata( node ) ) return 0;
	return xml_tagexact( node, tag );
}

typedef struct xml_convert {
	char *in;       /* The input tag */
	char *a, *aval; /* The attribute="attribute_value" pair, if nec. */
	char *out;      /* The output tag */
	int level;
} xml_convert;

static int
ebiin_doconvert( xml *node, fields *info, xml_convert *c, int nc )
{
	int i, found = 0;
	char *d;
	if ( !xml_hasdata( node ) ) return 0;
	d = xml_data( node );
	for ( i=0; i<nc && found==0; ++i ) {
		if ( c[i].a==NULL ) {
			if ( xml_tagexact( node, c[i].in ) ) {
				found = 1;
				fields_add( info, c[i].out, d, c[i].level );
			}
		} else {
			if ( xml_tag_attrib( node, c[i].in, c[i].a, c[i].aval)){
				found = 1;
				fields_add( info, c[i].out, d, c[i].level );
			}
		}
	
	}
	return found;
}

/* <ArticleTitle>Mechanism and.....</ArticleTitle>
 * <Title>Mechanism and....</Title>
 */
static void
ebiin_title( xml *node, fields *info, int title_level )
{
	if ( xml_hasdata( node ) )
		fields_add( info, "TITLE", xml_data( node ), title_level );
}

/*            <MedlineDate>2003 Jan-Feb</MedlineDate> */
static void
ebiin_medlinedate( fields *info, char *string, int level )
{
	newstr tmp;
	char *p, *q;
	newstr_init( &tmp );
	/* extract year */
	p = string;
	q = skip_notws( string );
	newstr_segcpy( &tmp, p, q );
	fields_add( info, "PARTYEAR", tmp.data, level );
	q = skip_ws( q );
	/* extract month */
	if ( q ) {
		p = q;
		newstr_empty( &tmp );
		q = skip_notws( q );
		newstr_segcpy( &tmp, p, q );
		newstr_findreplace( &tmp, "-", "/" );
		fields_add( info, "PARTMONTH", tmp.data, level );
		q = skip_ws( q );
	}
	/* extract day */
	if ( q ) {
		p = q;
		newstr_empty( &tmp );
		q = skip_notws( q );
		newstr_segcpy( &tmp, p, q );
		fields_add( info, "PARTDAY", tmp.data, level );
	}
	newstr_free( &tmp );
}

/* <Journal>
 *    <ISSN>0027-8424</ISSN>
 *    <JournalIssue PrintYN="Y">
 *       <Volume>100</Volume>
 *       <Issue>21</Issue>
 *       <PubDate>
 *          <Year>2003</Year>
 *          <Month>Oct</Month>
 *          <Day>14</Day>
 *       </PubDate>
 *    </Journal Issue>
 * </Journal>
 *
 * or....
 *
 * <Journal>
 *    <ISSN IssnType="Print">0735-0414</ISSN>
 *    <JournalIssue CitedMedium="Print">
 *        <Volume>38</Volume>
 *        <Issue>1</Issue>
 *        <PubDate>
 *            <MedlineDate>2003 Jan-Feb</MedlineDate>
 *        </PubDate>
 *    </JournalIssue>
 *    <Title>Alcohol and alcoholism (Oxford, Oxfordshire)  </Title>
 *    <ISOAbbreviation>Alcohol Alcohol.</ISOAbbreviation>
 * </Journal>
 */
static void
ebiin_journal1( xml *node, fields *info )
{
	xml_convert c[] = {
		{ "ISSN",     NULL, NULL, "ISSN",      1 },
		{ "Volume",   NULL, NULL, "VOLUME",    1 },
		{ "Issue",    NULL, NULL, "ISSUE",     1 },
		{ "Year",     NULL, NULL, "PARTYEAR",  1 },
		{ "Month",    NULL, NULL, "PARTMONTH", 1 },
		{ "Day",      NULL, NULL, "PARTDAY",   1 },
		{ "Language", NULL, NULL, "LANGUAGE",  1 },
	};
	int nc = sizeof( c ) / sizeof( c[0] );;
	if ( xml_hasdata( node ) && !ebiin_doconvert( node, info, c, nc ) ) {
		if ( xml_tagexact( node, "MedlineDate" ) )
			ebiin_medlinedate( info, xml_data( node ), 1 );
	}
	if ( node->down ) ebiin_journal1( node->down, info );
	if ( node->next ) ebiin_journal1( node->next, info );
}


/* <Pagination>
 *    <MedlinePgn>12111-6</MedlinePgn>
 * </Pagination>
 */
static void
ebiin_pagination( xml *node, fields *info )
{
	newstr sp, ep;
	char *p;
	int i;
	if ( xml_tagexact( node, "Pages" ) && node->value ) {
		newstrs_init( &sp, &ep, NULL );
		p = xml_data( node );
		while ( *p && *p!='-' )
			newstr_addchar( &sp, *p++ );
		if ( *p=='-' ) p++;
		while ( *p )
			newstr_addchar( &ep, *p++ );
		if ( sp.len ) fields_add( info, "PAGESTART", sp.data, 1 );
		if ( ep.len ) {
			if ( sp.len > ep.len ) {
				for ( i=sp.len-ep.len; i<sp.len; ++i )
					sp.data[i] = ep.data[i-sp.len+ep.len];
				fields_add( info, "PAGEEND", sp.data, 1 );
			} else
				fields_add( info, "PAGEEND", ep.data, 1 );
		}
		newstrs_free( &sp, &ep, NULL );
	}
	if ( node->down ) ebiin_pagination( node->down, info );
	if ( node->next ) ebiin_pagination( node->next, info );
}

/* <Abstract>
 *    <AbstractText>ljwejrelr</AbstractText>
 * </Abstract>
 */
static void
ebiin_abstract( xml *node, fields *info )
{
	if ( xml_hasdata( node ) && xml_tagexact( node, "AbstractText" ) )
		fields_add( info, "ABSTRACT", xml_data( node ), 0 );
	else if ( node->next ) ebiin_abstract( node->next, info );
}

/* <AuthorList CompleteYN="Y">
 *    <Author>
 *        <LastName>Barondeau</LastName>
 *        <ForeName>David P</ForeName>
 *        ( or <FirstName>David P</FirstName> )
 *        <Initials>DP</Initials>
 *    </Author>
 * </AuthorList>
 */
static void
ebiin_author( xml *node, newstr *name )
{
	char *p;
	if ( xml_tagexact( node, "LastName" ) ) {
		if ( name->len ) {
			newstr_prepend( name, "|" );
			newstr_prepend( name, xml_data( node ) );
		}
		else newstr_strcat( name, xml_data( node ) );
	} else if ( xml_tagexact( node, "ForeName" ) || 
	            xml_tagexact( node, "FirstName" ) ) {
		p = xml_data( node );
		while ( p && *p ) {
			if ( name->len ) newstr_addchar( name, '|' );
			while ( *p && *p==' ' ) p++;
			while ( *p && *p!=' ' ) newstr_addchar( name, *p++ );
		}
	} else if ( xml_tagexact( node, "Initials" ) && !strchr( name->data, '|' ) ) {
		p = xml_data( node );
		while ( p && *p ) {
			if ( name->len ) newstr_addchar( name, '|' );
			if ( !is_ws(*p ) ) newstr_addchar( name, *p++ );
		}
	}
		 
	if ( node->down ) ebiin_author( node->down, name );
	if ( node->next ) ebiin_author( node->next, name );
}

static void
ebiin_authorlist( xml *node, fields *info, int level )
{
	newstr name;
	newstr_init( &name );
	node = node->down;
	while ( node ) {
		if ( xml_tagexact( node, "Author" ) && node->down ) {
			ebiin_author( node->down, &name );
			if ( name.len ) {
				fields_add(info,"AUTHOR",name.data,level);
				newstr_empty( &name );
			}
		}
		node = node->next;
	}
	newstr_free( &name );
}

/* <PublicationTypeList>
 *    <PublicationType>Journal Article</PublicationType>
 * </PublicationTypeList>
 */

/* <MedlineJournalInfo>
 *    <Country>United States</Country>
 *    <MedlineTA>Proc Natl Acad Sci U S A</MedlineTA>
 *    <NlmUniqueID>7507876</NlmUniqueID>
 * </MedlineJournalInfo>
 */

static void
ebiin_journal2( xml *node, fields *info )
{
	if ( xml_tagwithdata( node, "TitleAbbreviation" ) )
		fields_add( info, "TITLE", xml_data( node ), 1 );
	if ( node->down ) ebiin_journal2( node->down, info );
	if ( node->next ) ebiin_journal2( node->next, info );
}

/*
 * <MeshHeadingList>
 *   <MeshHeading>
 *     <DescriptorName MajorTopicYN="N">Biophysics</DescriptorName>
 *   </MeshHeading>
 *   <MeshHeading>
 *     <DescriptorName MajorTopicYN="N">Crystallography, X-Ray</DescriptorName>
 *   </MeshHeading>
 * </MeshHeadingList>
*/
static void
ebiin_meshheading( xml *node, fields *info )
{
	if ( xml_tagwithdata( node, "DescriptorName" ) )
		fields_add( info, "KEYWORD", xml_data( node ), 0 );
	if ( node->next ) ebiin_meshheading( node->next, info );
}

static void
ebiin_meshheadinglist( xml *node, fields *info )
{
	if ( xml_tagexact( node, "MeshHeading" ) && node->down )
		ebiin_meshheading( node->down, info );
	if ( node->next ) ebiin_meshheadinglist( node->next, info );
}

static void
ebiin_book( xml *node, fields *info, int book_level )
{
	xml_convert book[] = {
		{ "Publisher",              NULL, NULL, "PUBLISHER",  0 },
		{ "Language",               NULL, NULL, "LANGUAGE",   0 },
		{ "ISBN10",                 NULL, NULL, "ISBN",       0 },
		{ "ISBN13",                 NULL, NULL, "ISBN13",     0 },
		{ "Year",                   NULL, NULL, "YEAR",       0 },
		{ "Month",                  NULL, NULL, "MONTH",      0 },
		{ "Day",                    NULL, NULL, "DAY",        0 },
		{ "PageTotal",              NULL, NULL, "TOTALPAGES", 0 },
		{ "SeriesName",             NULL, NULL, "TITLE",      1 },
		{ "SeriesISSN",             NULL, NULL, "ISSN",       0 },
		{ "OtherReportInformation", NULL, NULL, "NOTES",      0 },
		{ "Edition",                NULL, NULL, "EDITION",    0 },
	};
	int nbook = sizeof( book ) / sizeof( book[0] );
	xml_convert inbook[] = {
		{ "Publisher",              NULL, NULL, "PUBLISHER",  1 },
		{ "Language",               NULL, NULL, "LANGUAGE",   0 },
		{ "ISBN10",                 NULL, NULL, "ISBN",       1 },
		{ "ISBN13",                 NULL, NULL, "ISBN13",     1 },
		{ "Year",                   NULL, NULL, "PARTYEAR",   1 },
		{ "Month",                  NULL, NULL, "PARTMONTH",  1 },
		{ "Day",                    NULL, NULL, "PARTDAY",    1 },
		{ "PageTotal",              NULL, NULL, "TOTALPAGES", 1 },
		{ "SeriesName",             NULL, NULL, "TITLE",      2 },
		{ "SeriesISSN",             NULL, NULL, "ISSN",       1 },
		{ "OtherReportInformation", NULL, NULL, "NOTES",      1 },
		{ "Edition",                NULL, NULL, "EDITION",    1 },
	};
	int ninbook = sizeof( inbook ) / sizeof( inbook[0] );
	xml_convert *c;
	int nc;
	if ( book_level==0 ) { c = book; nc = nbook; }
	else { c = inbook; nc = ninbook; }
	if ( xml_hasdata( node ) && !ebiin_doconvert( node, info, c, nc ) ) {
		if ( xml_tagexact( node, "MedlineDate" ) )
			ebiin_medlinedate( info, xml_data( node ), book_level);
		else if ( xml_tagexact( node, "Title" ) )
			ebiin_title( node, info, book_level );
		else if ( xml_tagexact( node, "Pagination" ) && node->down )
			ebiin_pagination( node->down, info );
		else if ( xml_tagexact( node, "Abstract" ) && node->down )
			ebiin_abstract( node->down, info );
		else if ( xml_tagexact( node, "AuthorList" ) ) 
			ebiin_authorlist( node, info, book_level );
		else if ( xml_tagexact( node, "PubDate" ) && node->down)
			ebiin_book( node->down, info, book_level );
	}
	if ( node->next ) ebiin_book( node->next, info, book_level );
}

static void
ebiin_article( xml *node, fields *info )
{
	if ( xml_tagexact( node, "Journal" ) ) 
		ebiin_journal1( node, info );
	else if ( node->down && ( xml_tagexact( node, "Book" ) || 
			xml_tagexact(node, "Report") )) 
		ebiin_book( node->down, info, 1 );
	else if ( xml_tagexact( node, "ArticleTitle" ) )
		ebiin_title( node, info, 0 );
	else if ( xml_tagexact( node, "Pagination" ) && node->down )
		ebiin_pagination( node->down, info );
	else if ( xml_tagexact( node, "Abstract" ) && node->down )
		ebiin_abstract( node->down, info );
	else if ( xml_tagexact( node, "AuthorList" ) )
		ebiin_authorlist( node, info, 0 );
	if ( node->next ) ebiin_article( node->next, info );
}

static void
ebiin_publication( xml *node, fields *info )
{
	if ( node->down ) {
		if ( xml_tagexact( node, "Article" ) )
			ebiin_article( node->down, info );
		else if ( xml_tagexact( node, "Book" ) )
			ebiin_book( node->down, info, 0 );
		else if ( xml_tagexact( node, "Report" ) )
			ebiin_book( node->down, info, 0 );
		else if ( xml_tagexact( node, "JournalInfo" ) )
			ebiin_journal2( node->down, info );
		else if ( xml_tagexact( node, "MeshHeadingList" ) )
			ebiin_meshheadinglist( node->down, info );
	}
	if ( node->next ) ebiin_publication( node->next, info );
}

/* Call with the "Publication" node */
static void
ebiin_fixtype( xml *node, fields *info )
{
	newstr *type;
	fields_add( info, "RESOURCE", "text", 0 );
	type = xml_getattrib( node, "Type" );
	if ( !type || type->len==0 ) return;
	if ( !strcmp( type->data, "JournalArticle" ) ) {
		fields_add( info, "ISSUANCE", "continuing", 1 );
		fields_add( info, "GENRE", "periodical", 1 );
		fields_add( info, "GENRE", "academic journal", 1 );
	} else if ( !strcmp( type->data, "Book" ) ) {
		fields_add( info, "GENRE", "book", 0 );
		fields_add( info, "ISSUANCE", "monographic", 0 );
	} else if ( !strcmp( type->data, "BookArticle" ) ) {
		fields_add( info, "GENRE", "book", 1 );
		fields_add( info, "ISSUANCE", "monographic", 1 );
	}
}

static void
ebiin_assembleref( xml *node, fields *info )
{
	if ( xml_tagexact( node, "Publication" ) && node->down) {
		ebiin_fixtype( node, info );
		ebiin_publication( node->down, info );
	} else if ( node->down ) ebiin_assembleref( node->down, info );
	if ( node->next ) ebiin_assembleref( node->next, info );
}

int
ebiin_processf( fields *ebiin, char *data, char *filename, long nref )
{
	xml top;
	xml_init( &top );
	xml_tree( data, &top );
	ebiin_assembleref( &top, ebiin );
	xml_free( &top );
	return 1;
}
