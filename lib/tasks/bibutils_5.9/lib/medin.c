/*
 * medin.c
 *
 * Copyright (c) Chris Putnam 2004-2016
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
#include "iso639_2.h"
#include "bibutils.h"
#include "bibformats.h"

static int medin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset );
static int medin_processf( fields *medin, char *data, char *filename, long nref, param *p );


/*****************************************************
 PUBLIC: void medin_initparams()
*****************************************************/
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

/*****************************************************
 PUBLIC: int medin_readf()
*****************************************************/

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

static int
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

/*****************************************************
 PUBLIC: int medin_processf()
*****************************************************/

typedef struct xml_convert {
	char *in;       /* The input tag */
	char *a, *aval; /* The attribute="attribute_value" pair, if nec. */
	char *out;      /* The output tag */
	int level;
} xml_convert;

static int
medin_doconvert( xml *node, fields *info, xml_convert *c, int nc, int *found )
{
	int i, fstatus;
	char *d;
	*found = 0;
	if ( !xml_hasdata( node ) ) return BIBL_OK;
	d = xml_data( node );
	for ( i=0; i<nc && *found==0; ++i ) {
		if ( c[i].a==NULL ) {
			if ( xml_tagexact( node, c[i].in ) ) {
				*found = 1;
				fstatus = fields_add( info, c[i].out, d, c[i].level );
				if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
			}
		} else {
			if ( xml_tag_attrib( node, c[i].in, c[i].a, c[i].aval)){
				*found = 1;
				fstatus = fields_add( info, c[i].out, d, c[i].level );
				if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
			}
		}
	
	}
	return BIBL_OK;
}

/* <ArticleTitle>Mechanism and.....</ArticleTitle>
 */
static int
medin_articletitle( xml *node, fields *info )
{
	int fstatus, status = BIBL_OK;
	if ( xml_hasdata( node ) ) {
		fstatus = fields_add( info, "TITLE", xml_data( node ), 0 );
		if ( fstatus!=FIELDS_OK ) status = BIBL_ERR_MEMERR;
	}
	return status;
}

/*            <MedlineDate>2003 Jan-Feb</MedlineDate> */
static int
medin_medlinedate( fields *info, char *p, int level )
{
	int fstatus;
	newstr tmp;

	newstr_init( &tmp );

	p = newstr_cpytodelim( &tmp, skip_ws( p ), " \t\n\r", 0 );
	if ( newstr_memerr( &tmp ) ) return BIBL_ERR_MEMERR;
	if ( tmp.len > 0 ) {
		fstatus = fields_add( info, "PARTDATE:YEAR", tmp.data, level );
		if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}

	p = newstr_cpytodelim( &tmp, skip_ws( p ), " \t\n\r", 0 );
	if ( newstr_memerr( &tmp ) ) return BIBL_ERR_MEMERR;
	if ( tmp.len > 0 ) {
		newstr_findreplace( &tmp, "-", "/" );
		fstatus = fields_add( info, "PARTDATE:MONTH", tmp.data, level );
		if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}

	p = newstr_cpytodelim( &tmp, skip_ws( p ), " \t\n\r", 0 );
	if ( newstr_memerr( &tmp ) ) return BIBL_ERR_MEMERR;
	if ( tmp.len > 0 ) {
		fstatus = fields_add( info, "PARTDATE:DAY", tmp.data, level );
		if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}

	newstr_free( &tmp );

	return BIBL_OK;
}

/* <Langauge>eng</Language>
 */
static int
medin_language( xml *node, fields *info, int level )
{
	char *code, *language;
	int fstatus;
	code = xml_data( node );
	if ( !code ) return BIBL_OK;
	language = iso639_2_from_code( code );
	if ( language )
		fstatus = fields_add( info, "LANGUAGE", language, level );
	else
		fstatus = fields_add( info, "LANGUAGE", code, level );
	if ( fstatus==FIELDS_OK ) return BIBL_OK;
	else return BIBL_ERR_MEMERR;
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
static int
medin_journal1( xml *node, fields *info )
{
	xml_convert c[] = {
		{ "Title",           NULL, NULL, "TITLE",          1 },
		{ "ISOAbbreviation", NULL, NULL, "SHORTTITLE",     1 },
		{ "ISSN",            NULL, NULL, "ISSN",           1 },
		{ "Volume",          NULL, NULL, "VOLUME",         1 },
		{ "Issue",           NULL, NULL, "ISSUE",          1 },
		{ "Year",            NULL, NULL, "PARTDATE:YEAR",  1 },
		{ "Month",           NULL, NULL, "PARTDATE:MONTH", 1 },
		{ "Day",             NULL, NULL, "PARTDATE:DAY",   1 },
	};
	int nc = sizeof( c ) / sizeof( c[0] ), status, found;
	if ( xml_hasdata( node ) ) {
		status = medin_doconvert( node, info, c, nc, &found );
		if ( status!=BIBL_OK ) return status;
		if ( !found ) {
			if ( xml_tagexact( node, "MedlineDate" ) ) {
				status = medin_medlinedate( info, xml_data( node ), 1 );
				if ( status!=BIBL_OK ) return status;
			}
			if ( xml_tagexact( node, "Language" ) ) {
				status = medin_language( node, info, 1 );
				if ( status!=BIBL_OK ) return status;
			}
		}
	}
	if ( node->down ) {
		status = medin_journal1( node->down, info );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) {
		status = medin_journal1( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

/* <Pagination>
 *    <MedlinePgn>12111-6</MedlinePgn>
 * </Pagination>
 */
static int
medin_pagination( xml *node, fields *info )
{
	int i, fstatus, status;
	newstr sp, ep;
	char *p, *pp;
	if ( xml_tagexact( node, "MedlinePgn" ) && node->value ) {
		newstrs_init( &sp, &ep, NULL );
		p = newstr_cpytodelim( &sp, xml_data( node ), "-", 1 );
		if ( newstr_memerr( &sp ) ) return BIBL_ERR_MEMERR;
		if ( sp.len ) {
			fstatus = fields_add( info, "PAGES:START", sp.data, 1 );
			if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		}
		p = newstr_cpytodelim( &ep, p, "", 0 );
		if ( newstr_memerr( &ep ) ) return BIBL_ERR_MEMERR;
		if ( ep.len ) {
			if ( sp.len > ep.len ) {
				for ( i=sp.len-ep.len; i<sp.len; ++i )
					sp.data[i] = ep.data[i-sp.len+ep.len];
				pp = sp.data;
			} else  pp = ep.data;
			fstatus = fields_add( info, "PAGES:STOP", pp, 1 );
			if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		}
		newstrs_free( &sp, &ep, NULL );
	}
	if ( node->down ) {
		status = medin_pagination( node->down, info );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) {
		status = medin_pagination( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

/* <Abstract>
 *    <AbstractText>ljwejrelr</AbstractText>
 * </Abstract>
 */
static int
medin_abstract( xml *node, fields *info )
{
	int fstatus;
	if ( xml_tagwithdata( node, "AbstractText" ) ) {
		fstatus = fields_add( info, "ABSTRACT", xml_data( node ), 0 );
		if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	} else if ( node->next ) return medin_abstract( node->next, info );
	return BIBL_OK;
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
static int
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
	return BIBL_OK;
}

static int
medin_corpauthor( xml *node, newstr *name )
{
	if ( xml_tagexact( node, "CollectiveName" ) ) {
		newstr_strcpy( name, xml_data( node ) );
	} else if ( node->next ) medin_corpauthor( node->next, name );
	return BIBL_OK;
}

static int
medin_authorlist( xml *node, fields *info )
{
	int fstatus, status;
	newstr name;
	char *tag;
	newstr_init( &name );
	node = node->down;
	while ( node ) {
		if ( xml_tagexact( node, "Author" ) && node->down ) {
			status = medin_author( node->down, &name );
			tag = "AUTHOR";
			if ( !name.len ) {
				status = medin_corpauthor( node->down, &name );
				tag = "AUTHOR:CORP";
			}
			if ( newstr_memerr( &name ) || status!=BIBL_OK ) return BIBL_ERR_MEMERR;
			if ( name.len ) {
				fstatus = fields_add(info,tag,name.data,0);
				if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
			}
			newstr_empty( &name );
		}
		node = node->next;
	}
	newstr_free( &name );
	return BIBL_OK;
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

static int
medin_journal2( xml *node, fields *info )
{
	int fstatus, status = BIBL_OK;
	if ( xml_tagwithdata( node, "MedlineTA" ) && fields_find( info, "TITLE", 1 )==-1 ) {
		fstatus = fields_add( info, "TITLE", xml_data( node ), 1 );
		if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	if ( node->down ) {
		status = medin_journal2( node->down, info );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) status = medin_journal2( node->next, info );
	return status;
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
static int
medin_meshheading( xml *node, fields *info )
{
	int fstatus, status = BIBL_OK;
	if ( xml_tagwithdata( node, "DescriptorName" ) ) {
		fstatus = fields_add( info, "KEYWORD", xml_data( node ), 0 );
		if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	if ( node->next ) status = medin_meshheading( node->next, info );
	return status;
}

static int
medin_meshheadinglist( xml *node, fields *info )
{
	int status = BIBL_OK;
	if ( xml_tagexact( node, "MeshHeading" ) && node->down ) {
		status = medin_meshheading( node->down, info );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) status = medin_meshheadinglist( node->next, info );
	return status;
}

/* <PubmedData>
 *     ....
 *     <ArticleIdList>
 *         <ArticleId IdType="pubmed">14523232</ArticleId>
 *         <ArticleId IdType="doi">10.1073/pnas.2133463100</ArticleId>
 *         <ArticleId IdType="pii">2133463100</ArticleId>
 *         <ArticleId IdType="pmc">PMC4833866</ArticleId>
 *     </ArticleIdList>
 * </PubmedData>
 *
 * I think "pii" is "Publisher Item Identifier"
 */
static int
medin_pubmeddata( xml *node, fields *info )
{
	xml_convert c[] = {
		{ "ArticleId", "IdType", "doi",     "DOI",     0 },
		{ "ArticleId", "IdType", "pubmed",  "PMID",    0 },
		{ "ArticleId", "IdType", "medline", "MEDLINE", 0 },
		{ "ArticleId", "IdType", "pmc",     "PMC",     0 },
		{ "ArticleId", "IdType", "pii",     "PII",     0 },
	};
	int nc = sizeof( c ) / sizeof( c[0] ), found, status;
	status = medin_doconvert( node, info, c, nc, &found );
	if ( status!=BIBL_OK ) return status;
	if ( node->next ) {
		status = medin_pubmeddata( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->down ) {
		medin_pubmeddata( node->down, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

static int
medin_article( xml *node, fields *info )
{
	int fstatus, status = BIBL_OK;
	if ( xml_tagexact( node, "Journal" ) )
		status = medin_journal1( node, info );
	else if ( xml_tagexact( node, "ArticleTitle" ) )
		status = medin_articletitle( node, info );
	else if ( xml_tagexact( node, "Pagination" ) && node->down )
		status = medin_pagination( node->down, info );
	else if ( xml_tagexact( node, "Abstract" ) && node->down )
		status = medin_abstract( node->down, info );
	else if ( xml_tagexact( node, "AuthorList" ) )
		status = medin_authorlist( node, info );
	else if ( xml_tagexact( node, "Language" ) )
		status = medin_language( node, info, 0 );
	else if ( xml_tagexact( node, "Affiliation" ) ) {
		fstatus = fields_add( info, "ADDRESS", xml_data( node ), 0 );
		if ( fstatus!=FIELDS_OK ) status = BIBL_ERR_MEMERR;
	}
	if ( status!=BIBL_OK ) return status;
	if ( node->next ) status = medin_article( node->next, info );
	return status;
}

static int
medin_medlinecitation( xml *node, fields *info )
{
	int fstatus, status = BIBL_OK;
	if ( xml_tagexact( node, "PMID" ) && node->value->data ) {
		fstatus = fields_add( info, "PMID", node->value->data, 0 );
		if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	if ( node->down ) {
		if ( xml_tagexact( node, "Article" ) ) {
			status = medin_article( node->down, info );
		} else if ( xml_tagexact( node, "MedlineJournalInfo" ) ) {
			status = medin_journal2( node->down, info );
		} else if ( xml_tagexact( node, "MeshHeadingList" ) )
			status = medin_meshheadinglist( node->down, info );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) status = medin_medlinecitation( node->next, info );
	return status;
}

static int
medin_pubmedarticle( xml *node, fields *info )
{
	int status = BIBL_OK;
	if ( node->down ) {
		if ( xml_tagexact( node, "MedlineCitation" ) )
			status = medin_medlinecitation( node->down, info );
		else if ( xml_tagexact( node, "PubmedData" ) )
			status = medin_pubmeddata( node->down, info );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) status = medin_pubmedarticle( node->next, info );
	return status;
}

static int
medin_assembleref( xml *node, fields *info )
{
	int status = BIBL_OK;
	if ( node->down ) {
		if ( xml_tagexact( node, "PubmedArticle" ) )
			status = medin_pubmedarticle( node->down, info );
		else if ( xml_tagexact( node, "MedlineCitation" ) )
			status = medin_medlinecitation( node->down, info );
		else
			status = medin_assembleref( node->down, info );
	}
	if ( status!=BIBL_OK ) return status;

	if ( node->next ) {
		status = medin_assembleref( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}

	/* assume everything is a journal article */
	if ( fields_num( info ) ) {
		status = fields_add( info, "RESOURCE", "text", 0 );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		status = fields_add( info, "ISSUANCE", "continuing", 1 );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		status = fields_add( info, "GENRE", "periodical", 1 );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		status = fields_add( info, "GENRE", "academic journal", 1 );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		status = BIBL_OK;
	}

	return status;
}

static int
medin_processf( fields *medin, char *data, char *filename, long nref, param *p )
{
	int status;
	xml top;

	xml_init( &top );
	xml_tree( data, &top );
	status = medin_assembleref( &top, medin );
	xml_free( &top );

	if ( status==BIBL_OK ) return 1;
	return 0;
}
