/*
 * copacin.c
 *
 * Copyright (c) Chris Putnam 2004-2013
 *
 * Program and source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "is_ws.h"
#include "newstr.h"
#include "newstr_conv.h"
#include "list.h"
#include "name.h"
#include "title.h"
#include "fields.h"
#include "reftypes.h"
#include "serialno.h"
#include "copacin.h"

void
copacin_initparams( param *p, const char *progname )
{
	p->readformat       = BIBL_COPACIN;
	p->charsetin        = BIBL_CHARSET_DEFAULT;
	p->charsetin_src    = BIBL_SRC_DEFAULT;
	p->latexin          = 0;
	p->xmlin            = 0;
	p->utf8in           = 0;
	p->nosplittitle     = 0;
	p->verbose          = 0;
	p->addcount         = 0;
	p->output_raw       = 0;

	p->readf    = copacin_readf;
	p->processf = copacin_processf;
	p->cleanf   = NULL;
	p->typef    = NULL;
	p->convertf = copacin_convertf;
	p->all      = copac_all;
	p->nall     = copac_nall;

	list_init( &(p->asis) );
	list_init( &(p->corps) );

	if ( !progname ) p->progname = NULL;
	else p->progname = strdup( progname );
}

/* Endnote-Refer/Copac tag definition:
    character 1 = alphabetic character
    character 2 = alphabetic character
    character 3 = dash
    character 4 = space
*/
static int
copacin_istag( char *buf )
{
	if (! ((buf[0]>='A' && buf[0]<='Z')) || (buf[0]>='a' && buf[0]<='z') )
		return 0;
	if (! ((buf[1]>='A' && buf[1]<='Z')) || (buf[1]>='a' && buf[1]<='z') )
		return 0;
	if (buf[2]!='-' ) return 0;
	if (buf[3]!=' ' ) return 0;
	return 1; 
}
static int
readmore( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line )
{
	if ( line->len ) return 1;
	else return newstr_fget( fp, buf, bufsize, bufpos, line );
}

int
copacin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset )
{
	int haveref = 0, inref=0;
	char *p;
	*fcharset = CHARSET_UNKNOWN;
	while ( !haveref && readmore( fp, buf, bufsize, bufpos, line ) ) {
		/* blank line separates */
		if ( line->data==NULL ) continue;
		if ( inref && line->len==0 ) haveref=1; 
		p = &(line->data[0]);
		/* Recognize UTF8 BOM */
		if ( line->len > 2 &&
				(unsigned char)(p[0])==0xEF &&
				(unsigned char)(p[1])==0xBB &&
				(unsigned char)(p[2])==0xBF ) {
			*fcharset = CHARSET_UNICODE;
			p += 3;
		}
		if ( copacin_istag( p ) ) {
			if ( inref ) newstr_addchar( reference, '\n' );
			newstr_strcat( reference, p );
			newstr_empty( line );
			inref = 1;
		} else if ( inref ) {
			if ( p ) {
				/* copac puts tag only on 1st line */
				newstr_addchar( reference, ' ' );
				if ( *p ) p++;
				if ( *p ) p++;
				if ( *p ) p++;
			   	newstr_strcat( reference, p );
			}
			newstr_empty( line );
		} else {
			newstr_empty( line );
		}
	}
	return haveref;
}

static char*
copacin_addtag2( char *p, newstr *tag, newstr *data )
{
	int  i;
	i =0;
	while ( i<3 && *p ) {
		newstr_addchar( tag, *p++ );
		i++;
	}
	while ( *p==' ' || *p=='\t' ) p++;
	while ( *p && *p!='\r' && *p!='\n' ) {
		newstr_addchar( data, *p );
		p++;
	}
	newstr_trimendingws( data );
	while ( *p=='\n' || *p=='\r' ) p++;
	return p;
}

static char *
copacin_nextline( char *p )
{
	while ( *p && *p!='\n' && *p!='\r') p++;
	while ( *p=='\n' || *p=='\r' ) p++;
	return p;
}

int
copacin_processf( fields *copacin, char *p, char *filename, long nref )
{
	newstr tag, data;
	newstr_init( &tag );
	newstr_init( &data );
	while ( *p ) {
		p = skip_ws( p );
		if ( copacin_istag( p ) ) {
			p = copacin_addtag2( p, &tag, &data );
			/* don't add empty strings */
			if ( tag.len && data.len )
				fields_add( copacin, tag.data, data.data, 0 );
			newstr_empty( &tag );
			newstr_empty( &data );
		}
		else p = copacin_nextline( p );
	}
	newstr_free( &tag );
	newstr_free( &data );
	return 1;
}

/* copac names appear to always start with last name first, but don't
 * always seem to have a comma after the name
 *
 * editors seem to be stuck in as authors with the tag "[Editor]" in it
 */
static int
copacin_addname( fields *info, char *tag, newstr *name, int level, list *asis,
	list *corps )
{
	char *usetag = tag, editor[]="EDITOR";
	newstr usename, *s;
	list tokens;
	int comma = 0, i;

	if ( list_find( asis, name->data ) !=-1  ||
	     list_find( corps, name->data ) !=-1 ) {
		return name_add( info, tag, name->data, level, asis, corps );
	}

	list_init( &tokens );
	newstr_init( &usename );

	list_tokenize( &tokens, name, " ", 1 );
	for ( i=0; i<tokens.n; ++i ) {
		s = list_get( &tokens, i );
		if ( !strcmp( s->data, "[Editor]" ) ) {
			usetag = editor;
			newstr_strcpy( s, "" );
		} else if ( s->len && s->data[s->len-1]==',' ) {
			comma++;
		}
	}

	if ( comma==0 && tokens.n ) {
		s = list_get( &tokens, 0 );
		newstr_addchar( s, ',' );
	}

	for ( i=0; i<tokens.n; ++i ) {
		if ( i ) newstr_addchar( &usename, ' ' );
		newstr_newstrcat( &usename, list_get( &tokens, i ) );
	}

	return name_add( info, usetag, usename.data, level, asis, corps );
}

static int
copacin_addpage( fields *info, char *p, int level )
{
	newstr page;
	int ok;
	newstr_init( &page );
	p = skip_ws( p );
	while ( *p && !is_ws(*p) && *p!='-' && *p!='\r' && *p!='\n' ) 
		newstr_addchar( &page, *p++ );
	if ( page.len>0 ) {
		ok = fields_add( info, "PAGESTART", page.data, level );
		if ( !ok ) return 0;
	}
	newstr_empty( &page );
	while ( *p && (is_ws(*p) || *p=='-' ) ) p++;
	while ( *p && !is_ws(*p) && *p!='-' && *p!='\r' && *p!='\n' ) 
		newstr_addchar( &page, *p++ );
	if ( page.len>0 ) {
		ok = fields_add( info, "PAGEEND", page.data, level );
		if ( !ok ) return 0;
	}
	newstr_free( &page );
	return 1;
}

static int
copacin_adddate( fields *info, char *tag, char *newtag, char *p, int level )
{
	char *months[12]={ "January", "February", "March", "April",
		"May", "June", "July", "August", "September",
		"October", "November", "December" };
	char month[10];
	int found,i,part,ok;
	newstr date;
	newstr_init( &date );
	part = (!strncasecmp(newtag,"PART",4));
	if ( !strcasecmp( tag, "%D" ) ) {
		while ( *p ) newstr_addchar( &date, *p++ );
		if ( date.len>0 ) {
			if ( part ) 
				ok = fields_add(info, "PARTYEAR", date.data, level);
			else
				ok = fields_add( info, "YEAR", date.data, level );
			if ( !ok ) return 0;
		}
	} else if ( !strcasecmp( tag, "%8" ) ) {
		while ( *p && *p!=' ' && *p!=',' ) newstr_addchar( &date, *p++ );
		if ( date.len>0 ) {
			found = -1;
			for ( i=0; i<12 && found==-1; ++i )
				if ( !strncasecmp( date.data, months[i], 3 ) )
					found = i;
			if ( found!=-1 ) {
				if (found>8) sprintf( month, "%d", found+1 );
				else sprintf( month, "0%d", found+1 );
				if ( part ) 
					ok = fields_add( info, "PARTMONTH", month, level );
				else    ok = fields_add( info, "MONTH", month, level );
				if ( !ok ) return 0;
			} else {
				if ( part )
					ok = fields_add( info, "PARTMONTH", date.data, level );
				else
					ok = fields_add( info, "MONTH", date.data, level );
				if ( !ok ) return 0;
			}
		}
		newstr_empty( &date );
		p = skip_ws( p );
		while ( *p && *p!='\n' && *p!=',' )
			newstr_addchar( &date, *p++ );
		if ( date.len>0 && date.len<3 ) {
			if ( part )
				ok = fields_add( info, "PARTDAY", date.data, level );
			else
				ok = fields_add( info, "DAY", date.data, level );
			if ( !ok ) return 0;
		}
	}
	newstr_free( &date );
	return 1;
}

static void
copacin_report_notag( param *p, char *tag )
{
	if ( p->verbose ) {
		if ( p->progname ) fprintf( stderr, "%s: ", p->progname );
		fprintf( stderr, "Cannot find tag '%s'\n", tag );
	}
}

int
copacin_convertf( fields *copacin, fields *out, int reftype, param *p, variants *all, int nall )
{
	int  process, level, i, n, nfields, ok;
	newstr *tag, *data;
	char *newtag;

	nfields = fields_num( copacin );
	for ( i=0; i<nfields; ++i ) {

		tag = fields_tag( copacin, i, FIELDS_STRP );

		n = translate_oldtag( tag->data, reftype, all, nall, &process, &level, &newtag );
		if ( n==-1 ) {
			copacin_report_notag( p, tag->data );
			continue;
		}
		if ( process == ALWAYS ) continue; /*add these later*/

		data = fields_value( copacin, i, FIELDS_STRP );

		switch ( process ) {

		case SIMPLE:
			ok = fields_add( out, newtag, data->data, level );
			break;

		case TITLE:
			ok = title_process( out, newtag, data->data, level, p->nosplittitle );
			break;

		case PERSON:
			ok = copacin_addname( out, newtag, data, level, &(p->asis), &(p->corps) );
			break;

		case DATE:
			ok = copacin_adddate(out,all[reftype].  tags[i].oldstr,newtag,data->data,level);
			break;

		case PAGES:
			ok = copacin_addpage( out, data->data, level );
			break;

		case SERIALNO:
			ok = addsn( out, data->data, level );
			break;

		default:
			fprintf(stderr,"%s: internal error -- " "illegal process value %d\n", p->progname, process );
			ok = 1;
			break;
		}

		if ( !ok ) return BIBL_ERR_MEMERR;

	}

	return BIBL_OK;
}

