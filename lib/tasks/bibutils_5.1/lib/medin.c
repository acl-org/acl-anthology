/*
 * medin.c
 *
 * Copyright (c) Chris Putnam 2004-2013
 *
 * Source code released under the GPL version 2
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
#include "medin.h"
#include "iso639_2.h"
#include "bibutils.h"

void
medin_initparams( param *p, const char *progname )
{
	p->readformat       = BIBL_MEDLINEIN;
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

	p->readf    = medin_readf;
	p->processf = medin_processf;
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

/*
 * The only difference between MEDLINE and PUBMED in format is
 * that the entire library is wrapped in <MedlineCitationSet>
 * or <PubmedArticle> tags...
 */
static char *wrapper[] = { "PubmedArticle", "MedlineCitation" };
static int nwrapper = sizeof( wrapper ) / sizeof( wrapper[0] );

static char *
medin_findstartwrapper( char *buf, int *ntype )
{
	char *startptr=NULL;
	int i;
	for ( i=0; i<nwrapper && startptr==NULL; ++i ) {
		startptr = xml_findstart( buf, wrapper[ i ] );
		if ( startptr && *ntype==-1 ) *ntype = i;
	}
	return startptr;
}

static char *
medin_findendwrapper( char *buf, int ntype )
{
	char *endptr = xml_findend( buf, wrapper[ ntype ] );
	return endptr;
}

int
medin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset )
{
	newstr tmp;
	char *startptr = NULL, *endptr;
	int haveref = 0, inref = 0, file_charset = CHARSET_UNKNOWN, m, type = -1;
	newstr_init( &tmp );
	while ( !haveref && newstr_fget( fp, buf, bufsize, bufpos, line ) ) {
		if ( line->data ) {
			m = xml_getencoding( line );
			if ( m!=CHARSET_UNKNOWN ) file_charset = m;
		}
		if ( line->data ) {
			startptr = medin_findstartwrapper( line->data, &type );
		}
		if ( startptr || inref ) {
			if ( inref ) newstr_strcat( &tmp, line->data );
			else {
				newstr_strcat( &tmp, startptr );
				inref = 1;
			}
			endptr = medin_findendwrapper( tmp.data, type );
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
medin_doconvert( xml *node, fields *info, xml_convert *c, int nc )
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
 */
static void
medin_articletitle( xml *node, fields *info )
{
	if ( xml_hasdata( node ) )
		fields_add( info, "TITLE", xml_data( node ), 0 );
}

/*            <MedlineDate>2003 Jan-Feb</MedlineDate> */
static void
medin_medlinedate( fields *info, char *string, int level )
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

/* <Langauge>eng</Language>
 */
static int
medin_language( xml *node, fields *info, int level )
{
	char *code, *language;
	int ok;
	code = xml_data( node );
	if ( !code ) return 1;
	language = iso639_2_from_code( code );
	if ( language ) ok = fields_add( info, "LANGUAGE", language, level );
	else ok = fields_add( info, "LANGUAGE", code, level );
	return ok;
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
medin_journal1( xml *node, fields *info )
{
	xml_convert c[] = {
		{ "Title",           NULL, NULL, "TITLE",      1 },
		{ "ISOAbbreviation", NULL, NULL, "SHORTTITLE", 1 },
		{ "ISSN",            NULL, NULL, "ISSN",       1 },
		{ "Volume",          NULL, NULL, "VOLUME",     1 },
		{ "Issue",           NULL, NULL, "ISSUE",      1 },
		{ "Year",            NULL, NULL, "PARTYEAR",   1 },
		{ "Month",           NULL, NULL, "PARTMONTH",  1 },
		{ "Day",             NULL, NULL, "PARTDAY",    1 },
	};
	int nc = sizeof( c ) / sizeof( c[0] );;
	if ( xml_hasdata( node ) && !medin_doconvert( node, info, c, nc ) ) {
		if ( xml_tagexact( node, "MedlineDate" ) )
			medin_medlinedate( info, xml_data( node ), 1 );
		if ( xml_tagexact( node, "Language" ) )
			medin_language( node, info, 1 );
	}
	if ( node->down ) medin_journal1( node->down, info );
	if ( node->next ) medin_journal1( node->next, info );
}

/* <Pagination>
 *    <MedlinePgn>12111-6</MedlinePgn>
 * </Pagination>
 */
static void
medin_pagination( xml *node, fields *info )
{
	newstr sp, ep;
	char *p;
	int i;
	if ( xml_tagexact( node, "MedlinePgn" ) && node->value ) {
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
	if ( node->down ) medin_pagination( node->down, info );
	if ( node->next ) medin_pagination( node->next, info );
}

/* <Abstract>
 *    <AbstractText>ljwejrelr</AbstractText>
 * </Abstract>
 */
static void
medin_abstract( xml *node, fields *info )
{
	if ( xml_tagwithdata( node, "AbstractText" ) )
		fields_add( info, "ABSTRACT", xml_data( node ), 0 );
	else if ( node->next ) medin_abstract( node->next, info );
}

/* <AuthorList CompleteYN="Y">
 *    <Author>
 *        <LastName>Barondeau</LastName>
 *        <ForeName>David P</ForeName>
 *        ( or <FirstName>David P</FirstName> )
 *        <Initials>DP</Initials>
 *    </Author>
 *    <Author>
 *        <CollectiveName>Organization</CollectiveName>
 *    </Author>
 * </AuthorList>
 */
static void
medin_author( xml *node, newstr *name )
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
	} else if ( xml_tagexact( node, "Initials" ) && !strchr( name->data, '|' )) {
		p = xml_data( node );
		while ( p && *p ) {
			if ( name->len ) newstr_addchar( name, '|' );
			if ( !is_ws(*p) ) newstr_addchar( name, *p++ );
		}
	}
	if ( node->next ) medin_author( node->next, name );
}

static void
medin_corpauthor( xml *node, newstr *name )
{
	if ( xml_tagexact( node, "CollectiveName" ) ) {
		newstr_strcpy( name, xml_data( node ) );
	} else if ( node->next ) medin_corpauthor( node->next, name );
}

static void
medin_authorlist( xml *node, fields *info )
{
	newstr name;
	newstr_init( &name );
	node = node->down;
	while ( node ) {
		if ( xml_tagexact( node, "Author" ) && node->down ) {
			medin_author( node->down, &name );
			if ( name.len ) {
				fields_add(info,"AUTHOR",name.data,0);
			} else {
				medin_corpauthor( node->down, &name );
				if ( name.len )
					fields_add(info,"AUTHOR:CORP",name.data,0);
			}
			newstr_empty( &name );
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
medin_journal2( xml *node, fields *info )
{
	if ( xml_tagwithdata( node, "MedlineTA" ) && fields_find( info, "TITLE", 1 )==-1 )
		fields_add( info, "TITLE", xml_data( node ), 1 );
	if ( node->down ) medin_journal2( node->down, info );
	if ( node->next ) medin_journal2( node->next, info );
}

/*
<MeshHeadingList>
<MeshHeading>
<DescriptorName MajorTopicYN="N">Biophysics</DescriptorName>
</MeshHeading>
<MeshHeading>
<DescriptorName MajorTopicYN="N">Crystallography, X-Ray</DescriptorName>
</MeshHeading>
</MeshHeadingList>
*/
static void
medin_meshheading( xml *node, fields *info )
{
	if ( xml_tagwithdata( node, "DescriptorName" ) )
		fields_add( info, "KEYWORD", xml_data( node ), 0 );
	if ( node->next ) medin_meshheading( node->next, info );
}

static void
medin_meshheadinglist( xml *node, fields *info )
{
	if ( xml_tagexact( node, "MeshHeading" ) && node->down )
		medin_meshheading( node->down, info );
	if ( node->next ) medin_meshheadinglist( node->next, info );
}

/* <PubmedData>
 *     ....
 *     <ArticleIdList>
 *         <ArticleId IdType="pubmed">14523232</ArticleId>
 *         <ArticleId IdType="doi">10.1073/pnas.2133463100</ArticleId>
 *         <ArticleId IdType="pii">2133463100</ArticleId>
 *         <ArticleId IdType="medline">22922082</ArticleId>
 *     </ArticleIdList>
 * </PubmedData>
 *
 * I think "pii" is "Publisher Item Identifier"
 */

static void
medin_pubmeddata( xml *node, fields *info )
{
	xml_convert c[] = {
		{ "ArticleId", "IdType", "doi",     "DOI",     0 },
		{ "ArticleId", "IdType", "pubmed",  "PMID",    0 },
		{ "ArticleId", "IdType", "medline", "MEDLINE", 0 },
		{ "ArticleId", "IdType", "pii",     "PII",     0 },
	};
	int nc = sizeof( c ) / sizeof( c[0] );
	medin_doconvert( node, info, c, nc );
	if ( node->next ) medin_pubmeddata( node->next, info );
	if ( node->down ) medin_pubmeddata( node->down, info );
}

static void
medin_article( xml *node, fields *info )
{
	if ( xml_tagexact( node, "Journal" ) ) 
		medin_journal1( node, info );
	else if ( xml_tagexact( node, "ArticleTitle" ) )
		medin_articletitle( node, info );
	else if ( xml_tagexact( node, "Pagination" ) && node->down )
		medin_pagination( node->down, info );
	else if ( xml_tagexact( node, "Abstract" ) && node->down )
		medin_abstract( node->down, info );
	else if ( xml_tagexact( node, "AuthorList" ) )
		medin_authorlist( node, info );
	else if ( xml_tagexact( node, "Language" ) )
		medin_language( node, info, 0 );
	else if ( xml_tagexact( node, "Affiliation" ) )
		fields_add( info, "ADDRESS", xml_data( node ), 0 );
	if ( node->next ) medin_article( node->next, info );
}

static void
medin_medlinecitation( xml *node, fields *info )
{
	if ( xml_tagexact( node, "PMID" ) && node->value->data )
		fields_add( info, "PMID", node->value->data, 0 );
	if ( node->down ) {
		if ( xml_tagexact( node, "Article" ) )
			medin_article( node->down, info );
		else if ( xml_tagexact( node, "MedlineJournalInfo" ) )
			medin_journal2( node->down, info );
		else if ( xml_tagexact( node, "MeshHeadingList" ) )
			medin_meshheadinglist( node->down, info );
	}
	if ( node->next ) medin_medlinecitation( node->next, info );
}

static void
medin_pubmedarticle( xml *node, fields *info )
{
	if ( node->down ) {
		if ( xml_tagexact( node, "MedlineCitation" ) )
			medin_medlinecitation( node->down, info );
		else if ( xml_tagexact( node, "PubmedData" ) )
			medin_pubmeddata( node->down, info );
	}
	if ( node->next ) medin_pubmedarticle( node->next, info );
}

static void
medin_assembleref( xml *node, fields *info )
{
	if ( node->down ) {
		if ( xml_tagexact( node, "PubmedArticle" ) )
			medin_pubmedarticle( node->down, info );
		else if ( xml_tagexact( node, "MedlineCitation" ) )
			medin_medlinecitation( node->down, info );
		else medin_assembleref( node->down, info );
	}

	if ( node->next ) medin_assembleref( node->next, info );
	/* assume everything is a journal article */
	if ( fields_num( info ) ) {
		fields_add( info, "RESOURCE", "text", 0 );
		fields_add( info, "ISSUANCE", "continuing", 1 );
		fields_add( info, "GENRE", "periodical", 1 );
		fields_add( info, "GENRE", "academic journal", 1 );
	}
}

int
medin_processf( fields *medin, char *data, char *filename, long nref )
{
	xml top;
	xml_init( &top );
	xml_tree( data, &top );
	medin_assembleref( &top, medin );
	xml_free( &top );
	return 1;
}
