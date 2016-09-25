/*
 * title.c
 *
 * process titles into title/subtitle pairs for MODS
 *
 * Copyright (c) Chris Putnam 2004-2016
 *
 * Source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "newstr.h"
#include "fields.h"
#include "title.h"
#include "is_ws.h"

int
title_process( fields *info, char *tag, char *data, int level, 
	unsigned char nosplittitle )
{
	newstr title, subtitle;
	char *p, *q;
	int status;

	newstr_init( &title );
	newstr_init( &subtitle );

	if ( nosplittitle ) q = NULL;
	else {
		q = strstr( data, ": " );
		if ( !q ) q = strstr( data, "? " );
	}

	if ( !q ) newstr_strcpy( &title, data );
	else {
		p = data;
		while ( p!=q ) newstr_addchar( &title, *p++ );
		if ( *q=='?' ) newstr_addchar( &title, '?' );
		q++;
		q = skip_ws( q );
		while ( *q ) newstr_addchar( &subtitle, *q++ );
	}

	if ( strncasecmp( "SHORT", tag, 5 ) ) {
		if ( title.len>0 ) {
			status = fields_add( info, "TITLE", title.data, level );
			if ( status!=FIELDS_OK ) return 0;
		}
		if ( subtitle.len>0 ) {
			status = fields_add( info, "SUBTITLE", subtitle.data, level );
			if ( status!=FIELDS_OK ) return 0;
		}
	} else {
		if ( title.len>0 ) {
			status = fields_add( info, "SHORTTITLE", title.data, level );
			if ( status!=FIELDS_OK ) return 0;
		}
		/* no SHORT-SUBTITLE! */
	}

	newstr_free( &subtitle );
	newstr_free( &title );

	return 1;
}

