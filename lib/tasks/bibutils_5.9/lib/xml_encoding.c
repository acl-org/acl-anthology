/*
 * xml_getencoding.c
 *
 * Copyright (c) Chris Putnam 2007-2016
 *
 * Source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "charsets.h"
#include "newstr.h"
#include "newstr_conv.h"
#include "xml.h"
#include "xml_encoding.h"

static int
xml_getencodingr( xml *node )
{
	newstr *s;
	int n = CHARSET_UNKNOWN, m;
	if ( xml_tagexact( node, "xml" ) ) {
		s = xml_getattrib( node, "encoding" );
		if ( s && s->data ) {
			if ( !strcasecmp( s->data, "UTF-8" ) )
				n = CHARSET_UNICODE;
			else if ( !strcasecmp( s->data, "UTF8" ) )
				n = CHARSET_UNICODE;
			else if ( !strcasecmp( s->data, "GB18030" ) )
				n = CHARSET_GB18030;
			else n = charset_find( s->data );
			if ( n==CHARSET_UNKNOWN ) {
				fprintf( stderr, "Warning: did not recognize "
					"encoding '%s'\n", s->data );
			}
		}
	}
        if ( node->down ) {
		m = xml_getencodingr( node->down );
		if ( m!=CHARSET_UNKNOWN ) n = m;
	}
        if ( node->next ) {
		m = xml_getencodingr( node->next );
		if ( m!=CHARSET_UNKNOWN ) n = m;
	}
	return n;
}

int
xml_getencoding( newstr *s )
{
	newstr descriptor;
	xml descriptxml;
	int file_charset = CHARSET_UNKNOWN;
	char *p, *q;
	p = strstr( s->data, "<?xml" );
	if ( !p ) p = strstr( s->data, "<?XML" );
	if ( p ) {
		q = strstr( p, "?>" );
		if ( q ) {
			newstr_init( &descriptor );
			newstr_segcpy( &descriptor, p, q+2 );
			xml_init( &descriptxml );
			xml_tree( descriptor.data, &descriptxml );
			file_charset = xml_getencodingr( &descriptxml );
			xml_free( &descriptxml );
			newstr_free( &descriptor );
			newstr_segdel( s, p, q+2 );
		}
	}
	return file_charset;
}
