/*
 * is_ws.c
 *
 * Copyright (c) Chris Putnam 2003-2016
 *
 * Source code released under the GPL version 2
 *
 */
#include "is_ws.h"

/* is_ws(), is whitespace */
int 
is_ws( char ch )
{
	if (ch==' ' || ch=='\n' || ch=='\t' || ch=='\r' ) return 1;
	else return 0;
}

char *
skip_ws( char *p )
{
	if ( p ) {
		while ( is_ws( *p ) ) p++;
	}
	return p;
}

char *
skip_notws( char *p )
{
	if ( p ) {
		while ( *p && !is_ws( *p ) ) p++;
	}
	return p;
}
