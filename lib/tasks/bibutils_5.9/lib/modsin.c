/*
 * modsin.c
 *
 * Copyright (c) Chris Putnam 2004-2016
 *
 * Source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "is_ws.h"
#include "newstr.h"
#include "newstr_conv.h"
#include "xml.h"
#include "xml_encoding.h"
#include "fields.h"
#include "name.h"
#include "reftypes.h"
#include "modstypes.h"
#include "marc.h"
#include "iso639_1.h"
#include "iso639_2.h"
#include "iso639_3.h"
#include "bibutils.h"
#include "bibformats.h"

static int modsin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset );
static int modsin_processf( fields *medin, char *data, char *filename, long nref, param *p );

/*****************************************************
 PUBLIC: void modsin_initparams()
*****************************************************/
void
modsin_initparams( param *p, const char *progname )
{

	p->readformat       = BIBL_MODSIN;
	p->format_opts      = 0;
	p->charsetin        = BIBL_CHARSET_UNICODE;
	p->charsetin_src    = BIBL_SRC_DEFAULT;
	p->latexin          = 0;
	p->utf8in           = 1;
	p->xmlin            = 1;
	p->nosplittitle     = 0;
	p->verbose          = 0;
	p->addcount         = 0;
	p->singlerefperfile = 0;
	p->output_raw       = BIBL_RAW_WITHMAKEREFID |
	                      BIBL_RAW_WITHCHARCONVERT;

	p->readf    = modsin_readf;
	p->processf = modsin_processf;
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
 PUBLIC: int modsin_processf()
*****************************************************/

static char modsns[]="mods";

static int
modsin_detailr( xml *node, newstr *value )
{
	int status = BIBL_OK;
	if ( node->value && node->value->len ) {
		if ( value->len ) newstr_addchar( value, ' ' );
		newstr_newstrcat( value, node->value );
		if ( newstr_memerr( value ) ) return BIBL_ERR_MEMERR;
	}
	if ( node->down ) {
		status = modsin_detailr( node->down, value );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next )
		status = modsin_detailr( node->next, value );
	return status;
}

static int
modsin_detail( xml *node, fields *info, int level )
{
	newstr type, value, *tp;
	int fstatus, status = BIBL_OK;
	if ( node->down ) {
		newstrs_init( &type, &value, NULL );
		tp = xml_getattrib( node, "type" );
		if ( tp ) {
			newstr_newstrcpy( &type, tp );
			newstr_toupper( &type );
			if ( newstr_memerr( &type ) ) goto out;
		}
		status = modsin_detailr( node->down, &value );
		if ( status!=BIBL_OK ) goto out;
		if ( type.data && !strcasecmp( type.data, "PAGE" ) ) {
			fstatus = fields_add( info, "PAGES:START", value.data, level );
		} else {
			fstatus = fields_add( info, type.data, value.data, level );
		}
		if ( fstatus!=FIELDS_OK ) status = BIBL_ERR_MEMERR;
out:
		newstrs_free( &type, &value, NULL );
	}
	return status;
}

static int
modsin_date( xml *node, fields *info, int level, int part )
{
	int fstatus, status = BIBL_OK;
	char *tag, *p = NULL;
	newstr s;
	if ( node->value ) p = node->value->data;
	if ( p ) {
		newstr_init( &s );

		p = newstr_cpytodelim( &s, skip_ws( p ), "-", 1 );
		if ( newstr_memerr( &s ) ) { status = BIBL_ERR_MEMERR; goto out; }
		if ( s.len ) {
			tag = ( part ) ? "PARTDATE:YEAR" : "DATE:YEAR";
			fstatus =  fields_add( info, tag, s.data, level );
			if ( fstatus!=FIELDS_OK ) { status = BIBL_ERR_MEMERR; goto out; }
		}

		p = newstr_cpytodelim( &s, skip_ws( p ), "-", 1 );
		if ( newstr_memerr( &s ) ) { status = BIBL_ERR_MEMERR; goto out; }
		if ( s.len ) {
			tag = ( part ) ? "PARTDATE:MONTH" : "DATE:MONTH";
			fstatus =  fields_add( info, tag, s.data, level );
			if ( fstatus!=FIELDS_OK ) { status = BIBL_ERR_MEMERR; goto out; }
		}

		p = newstr_cpytodelim( &s, skip_ws( p ), "", 0 );
		if ( newstr_memerr( &s ) ) { status = BIBL_ERR_MEMERR; goto out; }
		if ( s.len ) {
			tag = ( part ) ? "PARTDATE:DAY" : "DATE:DAY";
			fstatus =  fields_add( info, tag, s.data, level );
			if ( fstatus!=FIELDS_OK ) { status = BIBL_ERR_MEMERR; goto out; }
		}
out:
		newstr_free( &s );
	}
	return status;
}

static int
modsin_pager( xml *node, newstr *sp, newstr *ep, newstr *tp, newstr *lp )
{
	int status = BIBL_OK;
	if ( xml_tagexact( node, "start" ) ) {
		newstr_newstrcpy( sp, node->value );
		if ( newstr_memerr( sp ) ) return BIBL_ERR_MEMERR;
	} else if ( xml_tagexact( node, "end" ) ) {
		newstr_newstrcpy( ep, node->value );
		if ( newstr_memerr( ep ) ) return BIBL_ERR_MEMERR;
	} else if ( xml_tagexact( node, "total" ) ) {
		newstr_newstrcpy( tp, node->value );
		if ( newstr_memerr( tp ) ) return BIBL_ERR_MEMERR;
	} else if ( xml_tagexact( node, "list" ) ) {
		newstr_newstrcpy( lp, node->value );
		if ( newstr_memerr( lp ) ) return BIBL_ERR_MEMERR;
	}
	if ( node->down ) {
		status = modsin_pager( node->down, sp, ep, tp, lp );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next )
		status = modsin_pager( node->next, sp, ep, tp, lp );
	return status;
}

static int
modsin_page( xml *node, fields *info, int level )
{
	int fstatus, status = BIBL_OK;
	newstr sp, ep, tp, lp;
	xml *dnode = node->down;

	if ( !dnode ) return BIBL_OK;

	newstrs_init( &sp, &ep, &tp, &lp, NULL );

	status = modsin_pager( dnode, &sp, &ep, &tp, &lp );
	if ( status!=BIBL_OK ) goto out;

	if ( sp.len || ep.len ) {
		if ( sp.len ) {
			fstatus = fields_add( info, "PAGES:START", sp.data, level );
			if ( fstatus!=FIELDS_OK ) { status = BIBL_ERR_MEMERR; goto out; }
		}
		if ( ep.len ) {
			fstatus = fields_add( info, "PAGES:STOP", ep.data, level );
			if ( fstatus!=FIELDS_OK ) { status = BIBL_ERR_MEMERR; goto out; }
		}
	} else if ( lp.len ) {
		fstatus = fields_add( info, "PAGES:START", lp.data, level );
		if ( fstatus!=FIELDS_OK ) { status = BIBL_ERR_MEMERR; goto out; }
	}
	if ( tp.len ) {
		fstatus = fields_add( info, "PAGES:TOTAL", tp.data, level );
		if ( fstatus!=FIELDS_OK ) { status = BIBL_ERR_MEMERR; goto out; }
	}
out:
	newstrs_free( &sp, &ep, &tp, &lp, NULL );
	return status;
}

static int
modsin_titler( xml *node, newstr *title, newstr *subtitle )
{
	int status = BIBL_OK;
	if ( xml_tagexact( node, "title" ) ) {
		if ( title->len ) {
			newstr_strcat( title, " : " );
			newstr_newstrcat( title, node->value );
		} else {
			newstr_newstrcat( title, node->value );
		}
		if ( newstr_memerr( title ) ) return BIBL_ERR_MEMERR;
	} else if ( xml_tagexact( node, "subTitle" ) ) {
		newstr_newstrcat( subtitle, node->value );
		if ( newstr_memerr( subtitle ) ) return BIBL_ERR_MEMERR;
	}
	if ( node->down ) {
		status = modsin_titler( node->down, title, subtitle );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next )
		status = modsin_titler( node->next, title, subtitle );
	return status;
}

static int
modsin_title( xml *node, fields *info, int level )
{
	char *titletag[2][2] = {
		{ "TITLE",    "SHORTTITLE" },
		{ "SUBTITLE", "SHORTSUBTITLE" },
	};
	int fstatus, status = BIBL_OK;
	newstr title, subtitle;
	xml *dnode;
	int abbr;

	dnode = node->down;
	if ( !dnode ) return status;

	newstrs_init( &title, &subtitle, NULL );
	abbr = xml_tag_attrib( node, "titleInfo", "type", "abbreviated" );

	status = modsin_titler( dnode, &title, &subtitle );
	if ( status!=BIBL_OK ) goto out;

	if ( title.len ) {
		fstatus = fields_add( info, titletag[0][abbr], title.data, level );
		if ( fstatus!=FIELDS_OK ) { status = BIBL_ERR_MEMERR; goto out; }
	}

	if ( subtitle.len ) {
		fstatus = fields_add( info, titletag[1][abbr], subtitle.data, level );
		if ( fstatus!=FIELDS_OK ) { status = BIBL_ERR_MEMERR; goto out; }
	}

out:
	newstrs_free( &title, &subtitle, NULL );
	return status;
}

/* modsin_marcrole_convert()
 *
 * Map MARC-authority roles for people or organizations associated
 * with a reference to internal roles.
 *
 * Take input strings with roles separated by '|' characters, e.g.
 * "author" or "author|creator" or "edt" or "editor|edt".
 */
static int
modsin_marcrole_convert( newstr *s, char *suffix, newstr *out )
{
	convert roles[] = {
		{ "author",              "AUTHOR",        0, 0 },
		{ "aut",                 "AUTHOR",        0, 0 },
		{ "aud",                 "AUTHOR",        0, 0 },
		{ "aui",                 "AUTHOR",        0, 0 },
		{ "aus",                 "AUTHOR",        0, 0 },
		{ "creator",             "AUTHOR",        0, 0 },
		{ "cre",                 "AUTHOR",        0, 0 },
		{ "editor",              "EDITOR",        0, 0 },
		{ "edt",                 "EDITOR",        0, 0 },
		{ "degree grantor",      "DEGREEGRANTOR", 0, 0 },
		{ "dgg",                 "DEGREEGRANTOR", 0, 0 },
		{ "organizer of meeting","ORGANIZER",     0, 0 },
		{ "orm",                 "ORGANIZER",     0, 0 },
		{ "patent holder",       "ASSIGNEE",      0, 0 },
		{ "pth",                 "ASSIGNEE",      0, 0 }
	};
	int nroles = sizeof( roles ) / sizeof( roles[0] );
	int i, nmismatch, n = -1, status = BIBL_OK;
	char *p, *q;

	if ( s->len == 0 ) {
		/* ...default to author on an empty string */
		n = 0;
	} else {
		/* ...find first match in '|'-separated list */
		for ( i=0; i<nroles && n==-1; ++i ) {
			p = s->data;
			while ( *p ) {
				q = roles[i].mods;
				nmismatch = 0;
				while ( *p && *p!='|' && nmismatch == 0) {
					if ( toupper( (unsigned char)*p ) != toupper( (unsigned char)*q ) )
						nmismatch++;
					p++;
					q++;
				}
				if ( !nmismatch && !(*(q++))) n = i;
				if ( *p=='|' ) p++;
			}
		}
	}

	if ( n!=-1 ) {
		newstr_strcpy( out, roles[n].internal );
		if ( suffix ) newstr_strcat( out, suffix );
	} else {
		newstr_strcpy( out, s->data );
	}
	if ( newstr_memerr( out ) ) status = BIBL_ERR_MEMERR;
	return status;
}

static int
modsin_asis_corp_r( xml *node, newstr *name, newstr *role )
{
	int status = BIBL_OK;
	if ( xml_tagexact( node, "namePart" ) ) {
		newstr_newstrcpy( name, node->value );
		if ( newstr_memerr( name ) ) return BIBL_ERR_MEMERR;
	} else if ( xml_tagexact( node, "roleTerm" ) ) {
		if ( role->len ) newstr_addchar( role, '|' );
		newstr_newstrcat( role, node->value );
		if ( newstr_memerr( role ) ) return BIBL_ERR_MEMERR;
	}
	if ( node->down ) {
		status = modsin_asis_corp_r( node->down, name, role );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next )
		status = modsin_asis_corp_r( node->next, name, role );
	return status;
}

static int
modsin_asis_corp( xml *node, fields *info, int level, char *suffix )
{
	int fstatus, status = BIBL_OK;
	newstr name, roles, role_out;
	xml *dnode = node->down;
	if ( dnode ) {
		newstrs_init( &name, &roles, &role_out, NULL );
		status = modsin_asis_corp_r( dnode, &name, &roles );
		if ( status!=BIBL_OK ) goto out;
		status = modsin_marcrole_convert( &roles, suffix, &role_out );
		if ( status!=BIBL_OK ) goto out;
		fstatus = fields_add( info, role_out.data, name.data, level );
		if ( fstatus!=FIELDS_OK ) status = BIBL_ERR_MEMERR;
out:
		newstrs_free( &name, &roles, &role_out, NULL );
	}
	return status;
}

static int
modsin_roler( xml *node, newstr *roles )
{
	int status = BIBL_OK;

	if ( roles->len ) newstr_addchar( roles, '|' );
	newstr_newstrcat( roles, node->value );
	if ( newstr_memerr( roles ) ) status = BIBL_ERR_MEMERR;

	return status;
}

static int
modsin_personr( xml *node, newstr *familyname, newstr *givenname, newstr *suffix )
{
	int status = BIBL_OK;

	if ( xml_tag_attrib( node, "namePart", "type", "family" ) ) {
		if ( familyname->len ) newstr_addchar( familyname, ' ' );
		newstr_newstrcat( familyname, node->value );
		if ( newstr_memerr( familyname ) ) status = BIBL_ERR_MEMERR;
	}

	else if ( xml_tag_attrib( node, "namePart", "type", "suffix") ||
	          xml_tag_attrib( node, "namePart", "type", "termsOfAddress" )) {
		if ( suffix->len ) newstr_addchar( suffix, ' ' );
		newstr_newstrcat( suffix, node->value );
		if ( newstr_memerr( suffix ) ) status = BIBL_ERR_MEMERR;
	}

	else if (xml_tag_attrib( node, "namePart", "type", "date") ){
		/* no nothing */
	}

	else {
		if ( givenname->len ) newstr_addchar( givenname, '|' );
		newstr_newstrcat( givenname, node->value );
		if ( newstr_memerr( givenname ) ) status = BIBL_ERR_MEMERR;
	}

	return status;
}

static int
modsin_person( xml *node, fields *info, int level )
{
	newstr familyname, givenname, name, suffix, roles, role_out;
	int fstatus, status = BIBL_OK;
	xml *dnode, *rnode;

	dnode = node->down;
	if ( !dnode ) return status;

	newstrs_init( &name, &familyname, &givenname, &suffix, &roles, &role_out, NULL );

	while ( dnode ) {

		if ( xml_tagexact( dnode, "namePart" ) ) {
			status = modsin_personr( dnode, &familyname, &givenname, &suffix );
			if ( status!=BIBL_OK ) goto out;
		}

		else if ( xml_tagexact( dnode, "role" ) ) {
			rnode = dnode->down;
			while ( rnode ) {
				if ( xml_tagexact( rnode, "roleTerm" ) ) {
					status = modsin_roler( rnode, &roles );
					if ( status!=BIBL_OK ) goto out;
				}
				rnode = rnode->next;
			}
		}

		dnode = dnode->next;

	}

	/*
	 * Handle:
	 *          <namePart type='given'>Noah A.</namePart>
	 *          <namePart type='family'>Smith</namePart>
	 * without mangling the order of "Noah A."
	 */
	if ( familyname.len ) {
		newstr_newstrcpy( &name, &familyname );
		if ( givenname.len ) {
			newstr_addchar( &name, '|' );
			newstr_newstrcat( &name, &givenname );
		}
	}

	/*
	 * Handle:
	 *          <namePart>Noah A. Smith</namePart>
	 * with name order mangling.
	 */
	else {
		if ( givenname.len )
			name_parse( &name, &givenname, NULL, NULL );
	}

	if ( suffix.len ) {
		newstr_strcat( &name, "||" );
		newstr_newstrcat( &name, &suffix );
	}

	if ( newstr_memerr( &name ) ) {
		status=BIBL_ERR_MEMERR;
		goto out;
	}

	status = modsin_marcrole_convert( &roles, NULL, &role_out );
	if ( status!=BIBL_OK ) goto out;

	fstatus = fields_add_can_dup( info, role_out.data, name.data, level );
	if ( fstatus!=FIELDS_OK ) status = BIBL_ERR_MEMERR;

out:
	newstrs_free( &name, &familyname, &givenname, &suffix, &roles, &role_out, NULL );
	return status;
}

static int
modsin_placeterm_text( xml *node, fields *info, int level, int school )
{
	char address_tag[] = "ADDRESS";
	char school_tag[]  = "SCHOOL";
	char *tag;
	int fstatus;

	tag = ( school ) ? school_tag : address_tag;

	fstatus = fields_add( info, tag, xml_data( node ), level );
	if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;

	return BIBL_OK;
}

static int
modsin_placeterm_code( xml *node, fields *info, int level )
{
	int fstatus, status = BIBL_OK;
	newstr s, *auth;

	newstr_init( &s );

	auth = xml_getattrib( node, "authority" );
	if ( auth && auth->len ) {
		newstr_newstrcpy( &s, auth );
		newstr_addchar( &s, '|' );
	}
	newstr_newstrcat( &s, node->value );

	if ( newstr_memerr( &s ) ) {
		status = BIBL_ERR_MEMERR;
		goto out;
	}

	fstatus = fields_add( info, "CODEDADDRESS", s.data, level );
	if ( fstatus!=FIELDS_OK ) status = BIBL_ERR_MEMERR;
out:
	newstr_free( &s );
	return status;
}

static int
modsin_placeterm( xml *node, fields *info, int level, int school )
{
	int status = BIBL_OK;
	newstr *type;

	type = xml_getattrib( node, "type" );
	if ( type && type->len ) {
		if ( !strcmp( type->data, "text" ) )
			status = modsin_placeterm_text( node, info, level, school );
		else if ( !strcmp( type->data, "code" ) )
			status = modsin_placeterm_code( node, info, level );
	}

	return status;
}

static int
modsin_placer( xml *node, fields *info, int level, int school )
{
	int status = BIBL_OK;
	if ( xml_tag_attrib( node, "place", "type", "school" ) ) {
		school = 1;
	} else if ( xml_tagexact( node, "placeTerm" ) ) {
		status = modsin_placeterm( node, info, level, school );
	}
	if ( node->down ) {
		status = modsin_placer( node->down, info, level, school );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) status = modsin_placer( node->next, info, level, school );
	return status;
}

static int
modsin_origininfor( xml *node, fields *info, int level, newstr *pub, newstr *add, newstr *addc, newstr *ed, newstr *iss )
{
	int status = BIBL_OK;
	if ( xml_tagexact( node, "dateIssued" ) )
		status = modsin_date( node, info, level, 0 );
	else if ( xml_tagexact( node, "publisher" ) && xml_hasdata( node ) ) {
		newstr_newstrcat( pub, node->value );
		if ( newstr_memerr( pub ) ) return BIBL_ERR_MEMERR;
	} else if ( xml_tagexact( node, "edition" ) && xml_hasdata( node ) ) {
		newstr_newstrcat( ed, node->value );
		if( newstr_memerr( ed ) ) return BIBL_ERR_MEMERR;
	} else if ( xml_tagexact( node, "issuance" ) && xml_hasdata( node ) ) {
		newstr_newstrcat( iss, node->value );
		if ( newstr_memerr( iss ) ) return BIBL_ERR_MEMERR;
	} else if ( xml_tagexact( node, "place" ) && xml_hasdata( node ) )
		status = modsin_placer( node, info, level, 0 );
	if ( status!=BIBL_OK ) return status;
	if ( node->down ) {
		status = modsin_origininfor( node->down, info, level, pub, add, addc, ed, iss );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next )
		status = modsin_origininfor( node->next, info, level, pub, add, addc, ed, iss );
	return status;
}

static int
modsin_origininfo( xml *node, fields *info, int level )
{
	newstr publisher, address, addcode, edition, issuance;
	int fstatus, status = BIBL_OK;
	if ( node->down ) {
		newstrs_init( &publisher, &address, &addcode, &edition, &issuance, NULL );
		status = modsin_origininfor( node->down, info, level, &publisher, 
				&address, &addcode, &edition, &issuance );
		if ( status!=BIBL_OK ) goto out;
		if ( publisher.len ) {
			fstatus = fields_add( info, "PUBLISHER", publisher.data, level );
			if ( fstatus!=FIELDS_OK ) { status=BIBL_ERR_MEMERR; goto out; }
		}
		if ( address.len ) {
			fstatus = fields_add( info, "ADDRESS", address.data, level );
			if ( fstatus!=FIELDS_OK ) { status=BIBL_ERR_MEMERR; goto out; }
		}
		if ( addcode.len ) {
			fstatus = fields_add( info, "CODEDADDRESS", addcode.data, level );
			if ( fstatus!=FIELDS_OK ) { status=BIBL_ERR_MEMERR; goto out; }
		}
		if ( edition.len ) {
			fstatus = fields_add( info, "EDITION", edition.data, level );
			if ( fstatus!=FIELDS_OK ) { status=BIBL_ERR_MEMERR; goto out; }
		}
		if ( issuance.len ) {
			fstatus = fields_add( info, "ISSUANCE", issuance.data, level );
			if ( fstatus!=FIELDS_OK ) { status=BIBL_ERR_MEMERR; goto out; }
		}
out:
		newstrs_free( &publisher, &address, &addcode, &edition, &issuance, NULL );
	}
	return status;
}

static int
modsin_subjectr( xml *node, fields *info, int level )
{
	int fstatus, status = BIBL_OK;
	if ( xml_tagexact( node, "topic" ) || xml_tagexact( node, "geographic" )) {
		fstatus = fields_add( info, "KEYWORD", node->value->data, level );
		if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	if ( node->down ) {
		status = modsin_subjectr( node->down, info, level );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) status = modsin_subjectr( node->next, info, level );
	return status;
}

static int
modsin_subject( xml *node, fields *info, int level )
{
	int status = BIBL_OK;
	if ( node->down ) status = modsin_subjectr( node->down, info, level );
	return status;
}

static int
modsin_id1( xml *node, fields *info, int level )
{
	int fstatus;
	newstr *ns;
	ns = xml_getattrib( node, "ID" );
	if ( ns && ns->len ) {
		fstatus = fields_add( info, "REFNUM", ns->data, level );
		if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	return BIBL_OK;
}

static int
modsin_genre( xml *node, fields *info, int level )
{
	char *added[] = { "manuscript", "academic journal", "magazine",
		"hearing", "report", "Ph.D. thesis", "Masters thesis",
		"Diploma thesis", "Doctoral thesis", "Habilitation thesis",
		"collection", "handwritten note", "communication",
		"teletype", "airtel", "memo", "e-mail communication",
		"press release", "television broadcast", "electronic"
	};
	int nadded = sizeof( added ) /sizeof( char *);
	int i, ismarc = 0, isadded = 0, fstatus;
	char *d;

	if ( !xml_hasdata( node ) ) return BIBL_OK;
	d = xml_data( node );
	if ( marc_findgenre( d )!=-1 ) ismarc = 1;
	if ( !ismarc ) {
		for ( i=0; i<nadded && ismarc==0 && isadded==0; ++i )
			if ( !strcasecmp( d, added[i] ) ) isadded = 1;
	}

	if ( ismarc || isadded ) 
		fstatus = fields_add( info, "GENRE", d, level );
	else
		fstatus = fields_add( info, "NGENRE", d, level );
	if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;

	return BIBL_OK;
}

/* in MODS version 3.5
 * <languageTerm type="text">....</languageTerm>
 * <languageTerm type="code" authority="xxx">...</languageTerm>
 * xxx = rfc3066
 * xxx = iso639-2b
 * xxx = iso639-3
 * xxx = rfc4646
 * xxx = rfc5646
 */
static int
modsin_languager( xml *node, fields *info, int level )
{
	int fstatus, status = BIBL_OK;
	char *d = NULL;
	if ( xml_tagexact( node, "languageTerm" ) ) {
		if ( xml_hasdata( node ) ) {
			if ( xml_hasattrib( node, "type", "code" ) ) {
				if ( xml_hasattrib( node, "authority", "iso639-1" ) )
					d = iso639_1_from_code( xml_data( node ) );
				else if ( xml_hasattrib( node, "authority", "iso639-2b" ) )
					d = iso639_2_from_code( xml_data( node ) );
				else if ( xml_hasattrib( node, "authority", "iso639-3" ))
					d = iso639_3_from_code( xml_data( node ) );
			}
			if ( !d ) d  = xml_data( node );
			fstatus = fields_add( info, "LANGUAGE", d, level );
			if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		}
	}
	if ( node->next ) status = modsin_languager( node->next, info, level );
	return status;
}

static int
modsin_language( xml *node, fields *info, int level )
{
	int fstatus, status = BIBL_OK;
	/* Old versions of MODS had <language>English</language> */
	if ( xml_hasdata( node ) ) {
		fstatus = fields_add( info, "LANGUAGE", xml_data( node ), level );
		if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}

	/* New versions of MODS have <language><languageTerm>English</languageTerm></language> */
	if ( node->down ) status = modsin_languager( node->down, info, level );
	return status;
}

static int
modsin_simple( xml *node, fields *info, char *tag, int level )
{
	int fstatus;
	if ( xml_hasdata( node ) ) {
		fstatus = fields_add( info, tag, xml_data( node ), level );
		if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	return BIBL_OK;
}

static int
modsin_locationr( xml *node, fields *info, int level )
{
	int fstatus, status = BIBL_OK;
	char *tag=NULL;

	if ( xml_tagexact( node, "url" ) ) {
		if ( xml_hasattrib( node, "access", "raw object" ) )
			tag = "FILEATTACH";
		else
			tag = "URL";
	} else if ( xml_tagexact( node, "physicalLocation" ) ) {
		if ( xml_hasattrib( node, "type", "school" ) )
			tag = "SCHOOL";
		else
			tag = "LOCATION";
	}

	if ( tag ) {
		fstatus = fields_add( info, tag, node->value->data, level );
		if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}

	if ( node->down ) {
		status = modsin_locationr( node->down, info, level );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) status = modsin_locationr( node->next, info, level );
	return status;
}

static int
modsin_location( xml *node, fields *info, int level )
{
	int status = BIBL_OK;
	if ( node->down ) status = modsin_locationr( node->down, info, level );
	return status;
}

static int
modsin_descriptionr( xml *node, newstr *s )
{
	int status = BIBL_OK;
	if ( xml_tagexact( node, "extent" ) ||
	     xml_tagexact( node, "note" ) ) {
		newstr_newstrcpy( s, node->value );
		if ( newstr_memerr( s ) ) return BIBL_ERR_MEMERR;
	}
	if ( node->down ) {
		status = modsin_descriptionr( node->down, s );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) status = modsin_descriptionr( node->next, s );
	return status;
}

static int
modsin_description( xml *node, fields *info, int level )
{
	int fstatus, status = BIBL_OK;
	newstr s;
	newstr_init( &s );
	if ( node->down ) {
		status = modsin_descriptionr( node->down, &s );
		if ( status!=BIBL_OK ) goto out;
	} else {
		if ( node->value && node->value->len > 0 )
			newstr_newstrcpy( &s, node->value );
		if ( newstr_memerr( &s ) ) {
			status = BIBL_ERR_MEMERR;
			goto out;
		}
	}
	if ( s.len ) {
		fstatus = fields_add( info, "DESCRIPTION", s.data, level );
		if ( fstatus!=FIELDS_OK ) {
			status = BIBL_ERR_MEMERR;
			goto out;
		}
	}
out:
	newstr_free( &s );
	return status;
}

static int
modsin_partr( xml *node, fields *info, int level )
{
	int status = BIBL_OK;
	if ( xml_tagexact( node, "detail" ) )
		status = modsin_detail( node, info, level );
	else if ( xml_tag_attrib( node, "extent", "unit", "page" ) )
		status = modsin_page( node, info, level );
	else if ( xml_tag_attrib( node, "extent", "unit", "pages" ) )
		status = modsin_page( node, info, level );
	else if ( xml_tagexact( node, "date" ) )
		status = modsin_date( node, info, level, 1 );
	if ( status!=BIBL_OK ) return status;
	if ( node->next ) status = modsin_partr( node->next, info, level );
	return status;
}

static int
modsin_part( xml *node, fields *info, int level )
{
	if ( node->down ) return modsin_partr( node->down, info, level );
	return BIBL_OK;
}

/* <classification authority="lcc">Q3 .A65</classification> */
static int
modsin_classification( xml *node, fields *info, int level )
{
	int fstatus, status = BIBL_OK;
	char *tag, *d;
	if ( xml_hasdata( node ) ) {
		d = xml_data( node );
		if ( xml_tag_attrib( node, "classification", "authority", "lcc" ) )
			tag = "LCC";
		else
			tag = "CLASSIFICATION";
		fstatus = fields_add( info, tag, d, level );
		if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
	}
	if ( node->down ) status = modsin_classification( node->down, info, level );
	return status;
}

static int
modsin_recordinfo( xml *node, fields *info, int level )
{
	int fstatus;
	xml *curr;
	char *d;

	/* extract recordIdentifier */
	curr = node;
	while ( curr ) {
		if ( xml_tagexact( curr, "recordIdentifier" ) && xml_hasdata( curr ) ) {
			d = xml_data( curr );
			fstatus = fields_add( info, "REFNUM", d, level );
			if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		}
		curr = curr->next;
	}
	return BIBL_OK;
}

static int
modsin_identifier( xml *node, fields *info, int level )
{
	convert ids[] = {
		{ "citekey",       "REFNUM",      0, 0 },
		{ "issn",          "ISSN",        0, 0 },
		{ "isbn",          "ISBN",        0, 0 },
		{ "doi",           "DOI",         0, 0 },
		{ "url",           "URL",         0, 0 },
		{ "uri",           "URL",         0, 0 },
		{ "pmid",          "PMID",        0, 0 },
		{ "pubmed",        "PMID",        0, 0 },
		{ "medline",       "MEDLINE",     0, 0 },
		{ "pmc",           "PMC",         0, 0 },
		{ "arXiv",         "ARXIV",       0, 0 },
		{ "pii",           "PII",         0, 0 },
		{ "isi",           "ISIREFNUM",   0, 0 },
		{ "serial number", "SERIALNUMBER",0, 0 },
		{ "accessnum",     "ACCESSNUM",   0, 0 },
		{ "jstor",         "JSTOR",       0, 0 },
	};
	int i, fstatus, n = sizeof( ids ) / sizeof( ids[0] );
	if ( !node->value || node->value->len==0 ) return BIBL_OK;
	for ( i=0; i<n; ++i ) {
		if ( xml_tag_attrib( node, "identifier", "type", ids[i].mods ) ) {
			fstatus = fields_add( info, ids[i].internal, node->value->data, level );
			if ( fstatus!=FIELDS_OK ) return BIBL_ERR_MEMERR;
		}
	}
	return BIBL_OK;
}

static int
modsin_mods( xml *node, fields *info, int level )
{
	convert simple[] = {
		{ "note",            "NOTES",    0, 0 },
		{ "abstract",        "ABSTRACT", 0, 0 },
		{ "bibtex-annote",   "ANNOTE",   0, 0 },
		{ "typeOfResource",  "RESOURCE", 0, 0 },
		{ "tableOfContents", "CONTENTS", 0, 0 },
	};
	int nsimple = sizeof( simple ) / sizeof( simple[0] );
	int i, found = 0, status = BIBL_OK;

	for ( i=0; i<nsimple && found==0; i++ ) {
		if ( xml_tagexact( node, simple[i].mods ) ) {
			status = modsin_simple( node, info, simple[i].internal, level );
			if ( status!=BIBL_OK ) return status;
			found = 1;
		}
	}

	if ( !found ) {
		if ( xml_tagexact( node, "titleInfo" ) )
			modsin_title( node, info, level );
		else if ( xml_tag_attrib( node, "name", "type", "personal" ) )
			status = modsin_person( node, info, level );
		else if ( xml_tag_attrib( node, "name", "type", "corporate" ) )
			status = modsin_asis_corp( node, info, level, ":CORP" );
		else if ( xml_tagexact( node, "name" ) )
			status = modsin_asis_corp( node, info, level, ":ASIS" );
		else if ( xml_tagexact( node, "recordInfo" ) && node->down )
			status = modsin_recordinfo( node->down, info, level );
		else if  ( xml_tagexact( node, "part" ) )
			modsin_part( node, info, level );
		else if ( xml_tagexact( node, "identifier" ) )
			status = modsin_identifier( node, info, level );
		else if ( xml_tagexact( node, "originInfo" ) )
			status = modsin_origininfo( node, info, level );
		else if ( xml_tagexact( node, "language" ) )
			status = modsin_language( node, info, level );
		else if ( xml_tagexact( node, "genre" ) )
			status = modsin_genre( node, info, level );
		else if ( xml_tagexact( node, "date" ) )
			status = modsin_date( node, info, level, 0 );
		else if ( xml_tagexact( node, "subject" ) )
			status = modsin_subject( node, info, level );
		else if ( xml_tagexact( node, "classification" ) )
			status = modsin_classification( node, info, level );
		else if ( xml_tagexact( node, "location" ) )
			status = modsin_location( node, info, level );
		else if ( xml_tagexact( node, "physicalDescription" ) )
			status = modsin_description( node, info, level );
		else if ( xml_tag_attrib( node, "relatedItem", "type", "host" ) ||
			  xml_tag_attrib( node, "relatedItem", "type", "series" ) ) {
			if ( node->down ) status = modsin_mods( node->down, info, level+1 );
		}
		else if ( xml_tag_attrib( node, "relatedItem", "type", "original" ) ) {
			if ( node->down ) status = modsin_mods( node->down, info, LEVEL_ORIG );
		}

		if ( status!=BIBL_OK ) return status;
	}

	if ( node->next ) status = modsin_mods( node->next, info, level );

	return status;
}

static int
modsin_assembleref( xml *node, fields *info )
{
	int status = BIBL_OK;
	if ( xml_tagexact( node, "mods" ) ) {
		status = modsin_id1( node, info, 0 );
		if ( status!=BIBL_OK ) return status;
		if ( node->down ) {
			status = modsin_mods( node->down, info, 0 );
			if ( status!=BIBL_OK ) return status;
		}
	} else if ( node->down ) {
		status = modsin_assembleref( node->down, info );
		if ( status!=BIBL_OK ) return status;
	}
	if ( node->next ) status = modsin_assembleref( node->next, info );
	return status;
}

static int
modsin_processf( fields *modsin, char *data, char *filename, long nref, param *p )
{
	int status;
	xml top;

	xml_init( &top );
	xml_tree( data, &top );
	status = modsin_assembleref( &top, modsin );
	xml_free( &top );

	if ( status==BIBL_OK ) return 1;
	else return 0;
}

/*****************************************************
 PUBLIC: int modsin_readf()
*****************************************************/

static char *
modsin_startptr( char *p )
{
	char *startptr;
	startptr = xml_findstart( p, "mods:mods" );
	if ( startptr ) {
		/* set namespace if found */
		xml_pns = modsns;
	} else {
		startptr = xml_findstart( p, "mods" );
		if ( startptr ) xml_pns = NULL;
	}
	return startptr;
}

static char *
modsin_endptr( char *p )
{
	return xml_findend( p, "mods" );
}

static int
modsin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line,
		newstr *reference, int *fcharset )
{
	newstr tmp;
	int m, file_charset = CHARSET_UNKNOWN;
	char *startptr = NULL, *endptr = NULL;

	newstr_init( &tmp );

	do {
		if ( line->data ) newstr_newstrcat( &tmp, line );
		if ( tmp.data ) {
			m = xml_getencoding( &tmp );
			if ( m!=CHARSET_UNKNOWN ) file_charset = m;
			startptr = modsin_startptr( tmp.data );
			endptr = modsin_endptr( tmp.data );
		} else startptr = endptr = NULL;
		newstr_empty( line );
		if ( startptr && endptr ) {
			newstr_segcpy( reference, startptr, endptr );
			newstr_strcpy( line, endptr );
		}
	} while ( !endptr && newstr_fget( fp, buf, bufsize, bufpos, line ) );

	newstr_free( &tmp );
	*fcharset = file_charset;
	return ( reference->len > 0 );
}

