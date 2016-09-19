/*
 * xml.c
 *
 * Copyright (c) Chris Putnam 2004-2016
 *
 * Source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "is_ws.h"
#include "strsearch.h"
#include "newstr.h"
#include "xml.h"

char *xml_pns = NULL;

static xml_attrib *
xmlattrib_new( void )
{
	xml_attrib *a = (xml_attrib *) malloc( sizeof( xml_attrib ) );
	if ( a ) {
		list_init( &(a->attrib) );
		list_init( &(a->value) );
	}
	return a;
}

static void
xmlattrib_add( xml_attrib *a, char *attrib, char *value  )
{
	if ( attrib ) list_addc( &(a->attrib), attrib );
	else list_addc( &(a->attrib), "" );
	if ( value ) list_addc( &(a->value), value );
	else list_addc( &(a->value), "" );
}

static void
xmlattrib_free( xml_attrib *a )
{
	list_free( &(a->attrib) );
	list_free( &(a->value ) );
}

static xml *
xml_new( void )
{
	xml *x = ( xml * ) malloc( sizeof( xml ) );
	if ( x ) xml_init( x );
	return x;
}

void
xml_free( xml *x )
{
	if ( x->tag ) {
		newstr_free( x->tag );
		free( x->tag );
	}
	if ( x->value ) {
		newstr_free( x->value );
		free( x->value );
	}
	if ( x->a ) {
		xmlattrib_free( x->a );
		free( x->a );
	}
	if ( x->down ) xml_free( x->down );
	if ( x->next ) xml_free( x->next );
}

void
xml_init( xml *x )
{
	x->tag = newstr_new();
	x->value = newstr_new();
	x->a = NULL;
	x->down = NULL;
	x->next = NULL;
	if ( !(x->tag) || !(x->value) ) {
		fprintf(stderr,"xml_init: memory error.\n");
		exit( EXIT_FAILURE );
	}
}

enum {
	XML_DESCRIPTOR,
	XML_COMMENT,
	XML_OPEN,
	XML_CLOSE,
	XML_OPENCLOSE
};

static int
xml_terminator( char *p, int *type )
{
	if ( *p=='>' ) {
		return 1;
	} else if ( *p=='/' && *(p+1)=='>' ) {
		if ( *type==XML_OPENCLOSE ) return 1;
		else if ( *type==XML_OPEN ) {
			*type = XML_OPENCLOSE;
			return 1;
		}
	} else if ( *p=='?' && *(p+1)=='>' && *type==XML_DESCRIPTOR ) {
		return 1;
	} else if ( *p=='!' && *(p+1)=='>' && *type==XML_COMMENT ) {
		return 1;
	}
	return 0;
}

static char *
xml_processattrib( char *p, xml_attrib **ap, int *type )
{
	xml_attrib *a = NULL;
	char quote_character = '\"';
	int inquotes = 0;
	newstr aname, aval;
	newstr_init( &aname );
	newstr_init( &aval );
	while ( *p && !xml_terminator(p,type) ) {
		/* get attribute name */
		while ( *p==' ' || *p=='\t' ) p++;
		while ( *p && !strchr( "= \t", *p ) && !xml_terminator(p,type)){
			newstr_addchar( &aname, *p );
			p++;
		}
		while ( *p==' ' || *p=='\t' ) p++;
		if ( *p=='=' ) p++;
		/* get attribute value */
		while ( *p==' ' || *p=='\t' ) p++;
		if ( *p=='\"' || *p=='\'' ) {
			if ( *p=='\'' ) quote_character = *p;
			inquotes=1;
			p++;
		}
		while ( *p && ((!xml_terminator(p,type) && !strchr("= \t", *p ))||inquotes)){
			if ( *p==quote_character ) inquotes=0;
			else newstr_addchar( &aval, *p );
			p++;
		}
		if ( aname.len ) {
			if ( !a ) a = xmlattrib_new();
			xmlattrib_add( a, aname.data, aval.data );
		}
		newstr_empty( &aname );
		newstr_empty( &aval );
	}
	newstr_free( &aname );
	newstr_free( &aval );
	*ap = a;
	return p;
}

/*
 * xml_processtag
 *
 *      XML_COMMENT   <!-- ....  -->
 * 	XML_DESCRIPTOR   <?.....>
 * 	XML_OPEN      <A>
 * 	XML_CLOSE     </A>
 * 	XML_OPENCLOSE <A/>
 */
static char *
xml_processtag( char *p, newstr *tag, xml_attrib **attrib, int *type )
{
	*attrib = NULL;
	if ( *p=='<' ) p++;
	if ( *p=='!' ) {
		while ( *p && *p!='>' ) newstr_addchar( tag, *p++ );
		*type = XML_COMMENT;
	} else if ( *p=='?' ) {
		*type = XML_DESCRIPTOR;
		p++; /* skip '?' */
		while ( *p && !strchr( " \t", *p ) && !xml_terminator(p,type) )
			newstr_addchar( tag, *p++ );
		if ( *p==' ' || *p=='\t' )
			p = xml_processattrib( p, attrib, type );
	} else if ( *p=='/' ) {
		while ( *p && !strchr( " \t", *p ) && !xml_terminator(p,type) )
			newstr_addchar( tag, *p++ );
		*type = XML_CLOSE;
		if ( *p==' ' || *p=='\t' ) 
			p = xml_processattrib( p, attrib, type );
	} else {
		*type = XML_OPEN;
		while ( *p && !strchr( " \t", *p ) && !xml_terminator(p,type) )
			newstr_addchar( tag, *p++ );
		if ( *p==' ' || *p=='\t' ) 
			p = xml_processattrib( p, attrib, type );
	}
	while ( *p && *p!='>' ) p++;
	if ( *p=='>' ) p++;
	return p;
}

static void
xml_appendnode( xml *onode, xml *nnode )
{
	if ( !onode->down ) onode->down = nnode;
	else {
		xml *p = onode->down;
		while ( p->next ) p = p->next;
		p->next = nnode;
	}
}

char *
xml_tree( char *p, xml *onode )
{
	newstr tag;
	xml_attrib *attrib;
	int type, is_style = 0;

	newstr_init( &tag );

	while ( *p ) {
		/* retain white space for <style> tags in endnote xml */
		if ( onode->tag && onode->tag->data && 
			!strcasecmp(onode->tag->data,"style") ) is_style=1;
		while ( *p && *p!='<' ) {
			if ( onode->value->len>0 || is_style || !is_ws( *p ) )
				newstr_addchar( onode->value, *p );
			p++;
		}
		if ( *p=='<' ) {
			newstr_empty( &tag );
			p = xml_processtag( p, &tag, &attrib, &type );
			if ( type==XML_OPEN || type==XML_OPENCLOSE ||
			     type==XML_DESCRIPTOR ) {
				xml *nnode = xml_new();
				newstr_newstrcpy( nnode->tag, &tag );
				nnode->a = attrib;
				xml_appendnode( onode, nnode );
				if ( type==XML_OPEN )
					p = xml_tree( p, nnode );
			} else if ( type==XML_CLOSE ) {
				/*check to see if it's closing for this one*/
				goto out; /* assume it's right for now */
			}
		}
	}
out:
	newstr_free( &tag );
	return p;
}

void
xml_draw( xml *x, int n )
{
	int i,j;
	if ( !x ) return;
	for ( i=0; i<n; ++i ) printf( "    " );
	printf("n=%d tag='%s' value='%s'\n", n, x->tag->data, x->value->data );
	if ( x->a ) {
		for ( j=0; j<x->a->value.n; ++j ) {
			for ( i=0; i<n; ++i ) printf( "    " );
			printf("    attrib='%s' value='%s'\n",
				(x->a)->attrib.str[j].data,
				(x->a)->value.str[j].data );
		}
	}
	if ( x->down ) xml_draw( x->down, n+1 );
	if ( x->next ) xml_draw( x->next, n );
}

char *
xml_findstart( char *buffer, char *tag )
{
	newstr starttag;
	char *p;

	newstr_init( &starttag );
	newstr_addchar( &starttag, '<' );
	newstr_strcat( &starttag, tag );
	newstr_addchar( &starttag, ' ' );
	p = strsearch( buffer, starttag.data );

	if ( !p ) {
		starttag.data[ starttag.len-1 ] = '>';
		p = strsearch( buffer, starttag.data );
	}

	newstr_free( &starttag );
	return p;
}

char *
xml_findend( char *buffer, char *tag )
{
	newstr endtag;
	char *p;

	newstr_init( &endtag );
	newstr_strcpy( &endtag, "</" );
	if ( xml_pns ) {
		newstr_strcat( &endtag, xml_pns );
		newstr_addchar( &endtag, ':' );
	}
	newstr_strcat( &endtag, tag );
	newstr_addchar( &endtag, '>' );

	p = strsearch( buffer, endtag.data );

	if ( p && *p ) {
		if ( *p ) p++;  /* skip <random_tag></end> combo */
		while ( *p && *(p-1)!='>' ) p++;
	}

	newstr_free( &endtag );
	return p;
}

int
xml_tagexact( xml *node, char *s )
{
	newstr tag;
	int found = 0;
	if ( xml_pns ) {
		newstr_init( &tag );
		newstr_strcpy( &tag, xml_pns );
		newstr_addchar( &tag, ':' );
		newstr_strcat( &tag, s );
		if ( node->tag->len==tag.len &&
				!strcasecmp( node->tag->data, tag.data ) )
			found = 1;
		newstr_free( &tag );
	} else {
		if ( node->tag->len==strlen( s ) && 
				!strcasecmp( node->tag->data, s ) )
			found = 1;
	}
	return found;
}

int
xml_hasattrib( xml *node, char *attrib, char *value )
{
	xml_attrib *na = node->a;
	int i;

	if ( na ) {

		for ( i=0; i<na->attrib.n; ++i ) {
			if ( !na->attrib.str[i].data || !na->value.str[i].data )
				continue;
			if ( !strcasecmp( na->attrib.str[i].data, attrib ) &&
			     !strcasecmp( na->value.str[i].data, value ) )
				return 1;
		}

	}

	return 0;
}

int
xml_tag_attrib( xml *node, char *s, char *attrib, char *value )
{
	if ( !xml_tagexact( node, s ) ) return 0;
	return xml_hasattrib( node, attrib, value );
}

newstr *
xml_getattrib( xml *node, char *attrib )
{
	newstr *ns = NULL;
	xml_attrib *na = node->a;
	int i, nattrib;
	if ( na ) {
		nattrib = na->attrib.n;
		for ( i=0; i<nattrib; ++i )
			if ( !strcasecmp( na->attrib.str[i].data, attrib ) )
				ns = &(na->value.str[i]);
	}
	return ns;
}

int
xml_hasdata( xml *node )
{
	if ( node && node->value && node->value->data ) return 1;
	return 0;
}

char *
xml_data( xml *node )
{
	return node->value->data;
}

int
xml_tagwithdata( xml *node, char *tag )
{
	if ( !xml_hasdata( node ) ) return 0;
	return xml_tagexact( node, tag );
}

