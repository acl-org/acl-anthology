/*
 * newstr_conv.c
 *
 * Copyright (c) Chris Putnam 1999-2016
 *
 * Source code released under the GPL version 2
 *
 * newstring routines for converting newstrings between character sets
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <limits.h>
#include "newstr.h"
#include "latex.h"
#include "entities.h"
#include "utf8.h"
#include "gb18030.h"
#include "charsets.h"
#include "newstr_conv.h"

static void
addentity( newstr *s, unsigned int ch )
{
	char buf[512];
	sprintf( buf, "&#%d;", ch );
	newstr_strcat( s, buf );
}

/* These are the five minimal predefined entites in XML */
static int
minimalxmlchars( newstr *s, unsigned int ch )
{
	if ( ch==34 ) { newstr_strcat( s, "&quot;" ); return 1; }
	else if ( ch==38 ) { newstr_strcat( s, "&amp;" ); return 1; }
	else if ( ch==39 ) { newstr_strcat( s, "&apos;" ); return 1; }
	else if ( ch==60 ) { newstr_strcat( s, "&lt;" ); return 1; }
	else if ( ch==62 ) { newstr_strcat( s, "&gt;" ); return 1; }
	return 0;
}

static void
addxmlchar( newstr *s, unsigned int ch )
{
	if ( minimalxmlchars( s, ch ) ) return;
	if ( ch > 127 ) addentity( s, ch );
	else newstr_addchar( s, ch );
}

static void
addutf8char( newstr *s, unsigned int ch, int xmlout )
{
	unsigned char code[6];
	int nc, i;
	if ( xmlout ) {
		if ( minimalxmlchars( s, ch ) ) return;
		if ( ch > 127 && xmlout == NEWSTR_CONV_XMLOUT_ENTITIES )
			{ addentity( s, ch ); return; }
	}
	nc = utf8_encode( ch, code );
	for ( i=0; i<nc; ++i )
		newstr_addchar( s, code[i] );
}

static void
addgb18030char( newstr *s, unsigned int ch, int xmlout )
{
	unsigned char code[4];
	int nc, i;
	if ( xmlout ) {
		if ( minimalxmlchars( s, ch ) ) return;
		if ( ch > 127 && xmlout == NEWSTR_CONV_XMLOUT_ENTITIES )
			{ addentity( s, ch ); return; }
	}
	nc = gb18030_encode( ch, code );
	for ( i=0; i<nc; ++i )
		newstr_addchar( s, code[i] );
}

static void
addlatexchar( newstr *s, unsigned int ch, int xmlout, int utf8out )
{
	char buf[512];
	uni2latex( ch, buf, sizeof( buf ) );
	/* If the unicode character isn't recognized as latex output
	 * a '?' unless the user has requested unicode output.  If so,
	 * output the unicode.
	 */
	if ( utf8out && !strcmp( buf, "?" ) ) {
		addutf8char( s, ch, xmlout );
	} else {
		newstr_strcat( s, buf );
	}
}

/*
 * get_unicode()
 * 
 *   This can be a little tricky.  If the character is simply encoded
 *   such as UTF8 for > 128 or by numeric xml entities such as "&#534;"
 *   then the output of decode_entity() and utf8_decode will necessarily
 *   be in the charsetin character set.  On the other hand, if it's a
 *   fancy latex expression, such as "\alpha", or a non-numeric xml entity
 *   like "&amp;", then we'll get the Unicode value (because our lists only
 *   keep the Unicode equivalent).
 *
 *   The unicode variable indicates whether or not a Unicode-based listing
 *   was used to convert the character (remember that charsetin could be
 *   Unicode independently).
 *
 *   The charset variable is used to keep track of what character set
 *   the character is in prior to conversion.
 *
 */

static unsigned int
get_unicode( newstr *s, unsigned int *pi, int charsetin, int latexin, int utf8in, int xmlin )
{
	unsigned int ch;
	int unicode = 0, err = 0;
	if ( xmlin && s->data[*pi]=='&' ) {
		ch = decode_entity( s->data, pi, &unicode, &err );
	} else if ( charsetin==CHARSET_GB18030 ) {
		ch = gb18030_decode( s->data, pi );
		unicode = 1;
	} else if ( latexin ) {
		/* Must handle bibtex files in UTF8/Unicode */
		if ( utf8in && ( s->data[*pi] & 128 ) ) {
			ch = utf8_decode( s->data, pi );
			unicode = 1;
		} else ch = latex2char( s->data, pi, &unicode );
	}
	else if ( utf8in )
		ch = utf8_decode( s->data, pi );
	else {
		ch = (unsigned int) s->data[*pi];
		*pi = *pi + 1;
	}
	if ( !unicode && charsetin!=CHARSET_UNICODE )
		ch = charset_lookupchar( charsetin, ch );
	return ch;
}

static int
write_unicode( newstr *s, unsigned int ch, int charsetout, int latexout,
		int utf8out, int xmlout )
{
	unsigned int c;
	if ( latexout ) {
		addlatexchar( s, ch, xmlout, utf8out );
	} else if ( utf8out ) {
		addutf8char( s, ch, xmlout );
	} else if ( charsetout==CHARSET_GB18030 ) {
		addgb18030char( s, ch, xmlout );
	} else {
		c = charset_lookupuni( charsetout, ch );
		if ( xmlout ) addxmlchar( s, c );
		else newstr_addchar( s, c );
	}
	return 1;
}

/*
 * Returns 1 on memory error condition
 */
int
newstr_convert( newstr *s,
	int charsetin,  int latexin,  int utf8in,  int xmlin,
	int charsetout, int latexout, int utf8out, int xmlout )
{
	unsigned int pos = 0;
	unsigned int ch;
	newstr ns;
	int ok = 1;

	if ( !s || s->len==0 ) return ok;

	newstr_init( &ns );

	if ( charsetin==CHARSET_UNKNOWN ) charsetin = CHARSET_DEFAULT;
	if ( charsetout==CHARSET_UNKNOWN ) charsetout = CHARSET_DEFAULT;

	while ( s->data[pos] ) {
		ch = get_unicode( s, &pos, charsetin, latexin, utf8in, xmlin );
		ok = write_unicode( &ns, ch, charsetout, latexout, utf8out, xmlout );
		if ( !ok ) goto out;
	}

	newstr_swapstrings( s, &ns );
out:
	newstr_free( &ns );

	return ok;
}

