/*
 * ebiin.c
 *
 * Copyright (c) Chris Putnam 2004-2016
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
#include "bibformats.h"

static int ebiin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset );
static int ebiin_processf( fields *ebiin, char *data, char *filename, long nref, param *p );


/*****************************************************
 PUBLIC: void ebiin_initparams()
*****************************************************/
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

/*****************************************************
 PUBLIC: int ebiin_readf()
*****************************************************/
static int
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

/*****************************************************
 PUBLIC: int ebiin_processf()
*****************************************************/

typedef struct xml_convert {
	char *in;       /* The input tag */
	char *a, *aval; /* The attribute="attribute_value" pair, if nec. */
	char *out;      /* The output tag */
	int level;
} xml_convert;

static int
ebiin_doconvert( xml *node, fields *info, xml_convert *c, int nc, int *found )
{
	int i, status;
	char *d;

	if ( !xml_hasdata( node ) ) goto out;

	d = xml_data( node );
	for ( i=0; i<nc; ++i ) {
		if ( c[i].a==NULL ) {
			if ( xml_tagexact( node, c[i].in ) ) {
				*found = 1;
				status = fields_add( info, c[i].out, d, c[i].level );
				if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
				else return BIBL_OK;
			}
		} else {
			if ( xml_tag_attrib( node, c[i].in, c[i].a, c[i].aval)){
				*found = 1;
				status = fields_add( info, c[i].out, d, c[i].level );
				if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
				else return BIBL_OK;
			}
		}
	
	}
out:
	*found = 0;
	return BIBL_OK;
}

/* <ArticleTitle>Mechanism and.....</ArticleTitle>
 * and
 * <Title>Mechanism and....</Title>
 */
static int
ebiin_title( xml *node, fields *info, int title_level )
{
	int status;
	if ( xml_hasdata( node ) ) {
		status = fields_add( info, "TITLE", xml_data( node ), title_level );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	return BIBL_OK;
}

/* ebiin_medlinedate()
 *
 *   - extract medline information from entries like:
 *             <MedlineDate>2003 Jan-Feb</MedlineDate>
 */
static int
ebiin_medlinedate_year( fields *info, char *p, newstr *s, int level, char **end )
{
	int status;
	*end = newstr_cpytodelim( s, p, " \t\n\r", 0 );
	if ( newstr_memerr( s ) ) return BIBL_ERR_MEMERR;
	if ( s->len ) {
		status = fields_add( info, "PARTDATE:YEAR", s->data, level );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	return BIBL_OK;
}
static int
ebiin_medlinedate_month( fields *info, char *p, newstr *s, int level, char **end )
{
	int status;
	*end = newstr_cpytodelim( s, p, " \t\n\r", 0 );
	newstr_findreplace( s, "-", "/" );
	if ( newstr_memerr( s ) ) return BIBL_ERR_MEMERR;
	if ( s->len ) {
		status = fields_add( info, "PARTDATE:MONTH", s->data, level );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	return BIBL_OK;
}
static int
ebiin_medlinedate_day( fields *info, char *p, newstr *s, int level, char **end )
{
	int status;
	*end = newstr_cpytodelim( s, p, " \t\n\r", 0 );
	if ( newstr_memerr( s ) ) return BIBL_ERR_MEMERR;
	if ( s->len ) {
		status = fields_add( info, "PARTDATE:DAY", s->data, level );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	return BIBL_OK;
}
static int
ebiin_medlinedate( fields *info, char *p, int level )
{
	int status;
	newstr s;
	newstr_init( &s );
	status = ebiin_medlinedate_year( info, skip_ws( p ), &s, level, &p );
	if ( status==BIBL_OK && *p )
		status = ebiin_medlinedate_month( info, skip_ws( p ), &s, level, &p );
	if ( status==BIBL_OK && *p )
		status = ebiin_medlinedate_day( info, skip_ws( p ), &s, level, &p );
	newstr_free( &s );
	return status;
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
ebiin_journal1( xml *node, fields *info )
{
	xml_convert c[] = {
		{ "ISSN",     NULL, NULL, "ISSN",           1 },
		{ "Volume",   NULL, NULL, "VOLUME",         1 },
		{ "Issue",    NULL, NULL, "ISSUE",          1 },
		{ "Year",     NULL, NULL, "PARTDATE:YEAR",  1 },
		{ "Month",    NULL, NULL, "PARTDATE:MONTH", 1 },
		{ "Day",      NULL, NULL, "PARTDATE:DAY",   1 },
		{ "Language", NULL, NULL, "LANGUAGE",       1 },
	};
	int nc = sizeof( c ) / sizeof( c[0] ), status, found;
	if ( xml_hasdata( node ) ) {
		status = ebiin_doconvert( node, info, c, nc, &found );
		if ( status!=BIBL_OK ) return status;
		if ( !found ) {
			if ( xml_tagexact( node, "MedlineDate" ) ) {
				status = ebiin_medlinedate( info, xml_data( node ), 1 );
				if ( status!=BIBL_OK ) return status;
			}
		}
	}
	if ( node->down ) {
		status = ebiin_journal1( node->down, info );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) {
		status = ebiin_journal1( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

/* <Pagination>
 *    <MedlinePgn>12111-6</MedlinePgn>
 * </Pagination>
 */
static int
ebiin_pages( fields *info, char *p )
{
	int i, status, ret = BIBL_OK;
	const int level = 1;
	newstr sp, ep, *up;

	newstrs_init( &sp, &ep, NULL );

	/* ...start page */
	p = newstr_cpytodelim( &sp, skip_ws( p ), "-", 1 );
	if ( newstr_memerr( &sp ) ) {
		ret = BIBL_ERR_MEMERR;
		goto out;
	}

	/* ...end page */
	p = newstr_cpytodelim( &ep, skip_ws( p ), " \t\n\r", 0 );
	if ( newstr_memerr( &ep ) ) {
		ret = BIBL_ERR_MEMERR;
		goto out;
	}

	if ( sp.len ) {
		status = fields_add( info, "PAGES:START", sp.data, level );
		if ( status!=FIELDS_OK ) {
			ret = BIBL_ERR_MEMERR;
			goto out;
		}
	}
	if ( ep.len ) {
		if ( sp.len > ep.len ) {
			for ( i=sp.len-ep.len; i<sp.len; ++i )
				sp.data[i] = ep.data[i-sp.len+ep.len];
				up = &(sp);
		} else up = &(ep);
		status = fields_add( info, "PAGES:STOP", up->data, level );
		if ( status!=FIELDS_OK ) ret = BIBL_ERR_MEMERR;
	}

out:
	newstrs_free( &sp, &ep, NULL );
	return ret;
}
static int
ebiin_pagination( xml *node, fields *info )
{
	int status;
	if ( xml_tagexact( node, "Pages" ) && node->value ) {
		status = ebiin_pages( info, xml_data( node ) );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->down ) {
		status = ebiin_pagination( node->down, info );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) {
		status = ebiin_pagination( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

/* <Abstract>
 *    <AbstractText>ljwejrelr</AbstractText>
 * </Abstract>
 */
static int
ebiin_abstract( xml *node, fields *info )
{
	int status;
	if ( xml_hasdata( node ) && xml_tagexact( node, "AbstractText" ) ) {
		status = fields_add( info, "ABSTRACT", xml_data( node ), 0 );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	else if ( node->next ) {
		status = ebiin_abstract( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
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
static int
ebiin_author( xml *node, newstr *name )
{
	int status;
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
	if ( newstr_memerr( name ) ) return BIBL_ERR_MEMERR;
		 
	if ( node->down ) {
		status = ebiin_author( node->down, name );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) {
		status = ebiin_author( node->next, name );
		if ( status!=BIBL_OK ) return status;
	}

	return BIBL_OK;
}
static int
ebiin_authorlist( xml *node, fields *info, int level )
{
	int fstatus, status = BIBL_OK;
	newstr name;

	newstr_init( &name );
	node = node->down;
	while ( node ) {
		if ( xml_tagexact( node, "Author" ) && node->down ) {
			status = ebiin_author( node->down, &name );
			if ( status!=BIBL_OK ) goto out;
			if ( name.len ) {
				fstatus = fields_add(info,"AUTHOR",name.data,level);
				if ( fstatus!=FIELDS_OK ) { status = BIBL_ERR_MEMERR; goto out; }
				newstr_empty( &name );
			}
		}
		node = node->next;
	}
out:
	newstr_free( &name );
	return status;
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
ebiin_journal2( xml *node, fields *info )
{
	int status;
	if ( xml_tagwithdata( node, "TitleAbbreviation" ) ) {
		status = fields_add( info, "TITLE", xml_data( node ), 1 );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	if ( node->down ) {
		status = ebiin_journal2( node->down, info );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) {
		status = ebiin_journal2( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
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
static int
ebiin_meshheading( xml *node, fields *info )
{
	int status;
	if ( xml_tagwithdata( node, "DescriptorName" ) ) {
		status = fields_add( info, "KEYWORD", xml_data( node ), 0 );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	if ( node->next ) {
		status = ebiin_meshheading( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

static int
ebiin_meshheadinglist( xml *node, fields *info )
{
	int status;
	if ( xml_tagexact( node, "MeshHeading" ) && node->down ) {
		status = ebiin_meshheading( node->down, info );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) {
		status = ebiin_meshheadinglist( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

static int
ebiin_book( xml *node, fields *info, int book_level )
{
	xml_convert book[] = {
		{ "Publisher",              NULL, NULL, "PUBLISHER",      0 },
		{ "Language",               NULL, NULL, "LANGUAGE",       0 },
		{ "ISBN10",                 NULL, NULL, "ISBN",           0 },
		{ "ISBN13",                 NULL, NULL, "ISBN13",         0 },
		{ "Year",                   NULL, NULL, "DATE:YEAR",      0 },
		{ "Month",                  NULL, NULL, "DATE:MONTH",     0 },
		{ "Day",                    NULL, NULL, "DATE:DAY",       0 },
		{ "PageTotal",              NULL, NULL, "PAGES:TOTAL",    0 },
		{ "SeriesName",             NULL, NULL, "TITLE",          1 },
		{ "SeriesISSN",             NULL, NULL, "ISSN",           0 },
		{ "OtherReportInformation", NULL, NULL, "NOTES",          0 },
		{ "Edition",                NULL, NULL, "EDITION",        0 },
	};
	int nbook = sizeof( book ) / sizeof( book[0] );
	xml_convert inbook[] = {
		{ "Publisher",              NULL, NULL, "PUBLISHER",      1 },
		{ "Language",               NULL, NULL, "LANGUAGE",       0 },
		{ "ISBN10",                 NULL, NULL, "ISBN",           1 },
		{ "ISBN13",                 NULL, NULL, "ISBN13",         1 },
		{ "Year",                   NULL, NULL, "PARTDATE:YEAR",  1 },
		{ "Month",                  NULL, NULL, "PARTDATE:MONTH", 1 },
		{ "Day",                    NULL, NULL, "PARTDATE:DAY",   1 },
		{ "PageTotal",              NULL, NULL, "PAGES:TOTAL",    1 },
		{ "SeriesName",             NULL, NULL, "TITLE",          2 },
		{ "SeriesISSN",             NULL, NULL, "ISSN",           1 },
		{ "OtherReportInformation", NULL, NULL, "NOTES",          1 },
		{ "Edition",                NULL, NULL, "EDITION",        1 },
	};
	int ninbook = sizeof( inbook ) / sizeof( inbook[0] );
	xml_convert *c;
	int nc, status, found;
	if ( book_level==0 ) { c = book; nc = nbook; }
	else { c = inbook; nc = ninbook; }
	if ( xml_hasdata( node ) ) {
		status = ebiin_doconvert( node, info, c, nc, &found );
		if ( status!=BIBL_OK ) return status;
		if ( !found ) {
			status = BIBL_OK;
			if ( xml_tagexact( node, "MedlineDate" ) )
				status = ebiin_medlinedate( info, xml_data( node ), book_level);
			else if ( xml_tagexact( node, "Title" ) )
				status = ebiin_title( node, info, book_level );
			else if ( xml_tagexact( node, "Pagination" ) && node->down )
				status = ebiin_pagination( node->down, info );
			else if ( xml_tagexact( node, "Abstract" ) && node->down )
				status = ebiin_abstract( node->down, info );
			else if ( xml_tagexact( node, "AuthorList" ) )
				status = ebiin_authorlist( node, info, book_level );
			else if ( xml_tagexact( node, "PubDate" ) && node->down)
				status = ebiin_book( node->down, info, book_level );
			if ( status!=BIBL_OK ) return status;
		}
	}
	if ( node->next ) {
		status = ebiin_book( node->next, info, book_level );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

static int
ebiin_article( xml *node, fields *info )
{
	int status = BIBL_OK;

	if ( xml_tagexact( node, "Journal" ) ) 
		status = ebiin_journal1( node, info );
	else if ( node->down && ( xml_tagexact( node, "Book" ) || 
			xml_tagexact(node, "Report") )) 
		status = ebiin_book( node->down, info, 1 );
	else if ( xml_tagexact( node, "ArticleTitle" ) )
		status = ebiin_title( node, info, 0 );
	else if ( xml_tagexact( node, "Pagination" ) && node->down )
		status = ebiin_pagination( node->down, info );
	else if ( xml_tagexact( node, "Abstract" ) && node->down )
		status = ebiin_abstract( node->down, info );
	else if ( xml_tagexact( node, "AuthorList" ) )
		status = ebiin_authorlist( node, info, 0 );
	if ( status!=BIBL_OK ) return status;

	if ( node->next ) {
		status = ebiin_article( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}

	return BIBL_OK;
}

static int
ebiin_publication( xml *node, fields *info )
{
	int status = BIBL_OK;
	if ( node->down ) {
		if ( xml_tagexact( node, "Article" ) )
			status = ebiin_article( node->down, info );
		else if ( xml_tagexact( node, "Book" ) )
			status = ebiin_book( node->down, info, 0 );
		else if ( xml_tagexact( node, "Report" ) )
			status = ebiin_book( node->down, info, 0 );
		else if ( xml_tagexact( node, "JournalInfo" ) )
			status = ebiin_journal2( node->down, info );
		else if ( xml_tagexact( node, "MeshHeadingList" ) )
			status = ebiin_meshheadinglist( node->down, info );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) {
		status = ebiin_publication( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

/* Call with the "Publication" node */
static int
ebiin_fixtype( xml *node, fields *info )
{
	char *resource = NULL, *issuance = NULL, *genre1 = NULL, *genre2 = NULL;
	newstr *type;
	int reslvl, isslvl, gen1lvl, gen2lvl;
	int status;

	type = xml_getattrib( node, "Type" );
	if ( !type || type->len==0 ) return BIBL_OK;

	if ( !strcmp( type->data, "JournalArticle" ) ) {
		resource = "text";
		issuance = "continuing";
		genre1   = "periodical";
		genre2   = "academic journal";
		reslvl   = 0;
		isslvl   = 1;
		gen1lvl  = 1;
		gen2lvl  = 1;
	} else if ( !strcmp( type->data, "Book" ) ) {
		resource = "text";
		issuance = "monographic";
		genre1   = "book";
		reslvl   = 0;
		isslvl   = 0;
		gen1lvl  = 0;
	} else if ( !strcmp( type->data, "BookArticle" ) ) {
		resource = "text";
		issuance = "monographic";
		genre1   = "book";
		reslvl   = 0;
		isslvl   = 1;
		gen1lvl  = 1;
	}

	if ( resource ) {
		status = fields_add( info, "RESOURCE", resource, reslvl );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	if ( issuance ) {
		status = fields_add( info, "ISSUANCE", issuance, isslvl );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	if ( genre1 ) {
		status = fields_add( info, "GENRE", genre1, gen1lvl );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	if ( genre2 ) {
		status = fields_add( info, "GENRE", genre2, gen2lvl );
		if ( status!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}

	return BIBL_OK;
}

static int
ebiin_assembleref( xml *node, fields *info )
{
	int status;
	if ( xml_tagexact( node, "Publication" ) && node->down ) {
		status = ebiin_fixtype( node, info );
		if ( status!=BIBL_OK ) return status;
		status = ebiin_publication( node->down, info );
		if ( status!=BIBL_OK ) return status;
	} else if ( node->down ) {
		status = ebiin_assembleref( node->down, info );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) {
		status = ebiin_assembleref( node->next, info );
		if ( status!=BIBL_OK ) return status;
	}
	return BIBL_OK;
}

static int
ebiin_processf( fields *ebiin, char *data, char *filename, long nref, param *p )
{
	int status;
	xml top;

	xml_init( &top );
	xml_tree( data, &top );
	status = ebiin_assembleref( &top, ebiin );
	xml_free( &top );

	return ( status==BIBL_OK ) ? 1 : 0;
}
