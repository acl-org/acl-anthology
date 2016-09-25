/*
 * pages.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "is_ws.h"
#include "utf8.h"
#include "pages.h"

/* extract_range()
 *
 * Handle input strings like:
 *
 * "1-15"
 * " 1 - 15 "
 * " 1000--- 1500"
 * " 1 <<em-dash>> 10"
 * " 107 111"
 */
static void
extract_range( newstr *input, newstr *begin, newstr *end )
{
	/* -30 is the first character of a UTF8 em-dash and en-dash */
	const char terminators[] = { ' ', '-', '\t', '\r', '\n', -30, '\0' };
	char *p;

	newstr_empty( begin );
	newstr_empty( end );

	if ( input->len==0 ) return;

	p = skip_ws( input->data );
	while ( *p && !strchr( terminators, *p ) )
		newstr_addchar( begin, *p++ );

	p = skip_ws( p );

	while ( *p=='-' ) p++;
	while ( utf8_is_emdash( p ) ) p+=3;
	while ( utf8_is_endash( p ) ) p+=3;

	p = skip_ws( p );

	while ( *p && !strchr( terminators, *p ) )
		newstr_addchar( end, *p++ );
}

int
pages_add( fields *bibout, char *outtag, newstr *invalue, int level )
{
	int fstatus, status = 1;
	newstr start, stop;

	newstr_init( &start );
	newstr_init( &stop );

	extract_range( invalue, &start, &stop );

	if ( newstr_memerr( &start ) || newstr_memerr( &stop ) ) {
		status = 0;
		goto out;
	}

	if ( start.len>0 ) {
		fstatus = fields_add( bibout, "PAGES:START", start.data, level );
		if ( fstatus!=FIELDS_OK ) {
			status = 0;
			goto out;
		}
	}

	if ( stop.len>0 ) {
		fstatus = fields_add( bibout, "PAGES:STOP", stop.data, level );
		if ( fstatus!=FIELDS_OK ) status = 0;
	}

out:
	newstr_free( &start );
	newstr_free( &stop );
	return status;
}

