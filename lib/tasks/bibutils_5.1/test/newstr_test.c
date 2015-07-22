/*
 * newstr_test.c
 *
 * test newstr functions
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "newstr.h"

char progname[] = "newstr_test";
char version[] = "0.2";

int
test_consistency( newstr *s, int numchars, const char *fn )
{
	if ( s->data ) {
		if ( s->len != strlen( s->data ) ) {
			fprintf(stdout,"%s: failed consistency check found %d, s->len=%ld\n",fn,(int)strlen(s->data),s->len);
			return 1;
		}
	} else {
		if ( s->len != 0 ) {
			fprintf(stdout,"%s: failed consistency check found for unallocated string, s->len=%ld\n",fn,s->len);
			return 1;
		}
	}
	if ( s->len != numchars ) {
		fprintf(stdout,"%s: failed consistency check found %d, expected %d\n",fn,(int)strlen(s->data),numchars);
		return 1;
	}
	return 0;
}

int
test_identity( newstr *s, const char *compstr )
{
	/* Unallocated newstrings are considered identical to empty strings */
	if ( compstr[0]=='\0' ) {
		if ( s->data==NULL || s->data[0]=='\0' ) return 0;
		else return 1;
	}
	/* compstr!="", so s->data must exist */
	if ( !s->data ) return 1;
	if ( strcmp( s->data, compstr ) == 0 ) return 0;
	return 1;
}

int
test_empty( newstr *s )
{
	int failed = 0;
	int numchars = 1000, i, j;
	newstr_empty( s );
	for ( i=0; i<numchars; ++i ) {
		for ( j=0; j<i; ++j )
			newstr_addchar( s, 'x' );
		newstr_empty( s );
		if ( test_consistency( s, 0, __FUNCTION__ ) || test_identity( s, "" ) )
			failed++;
	}
	return failed;
}

int
test_addchar( newstr *s )
{
	int failed = 0;
	int numshort = 5, numchars = 1000, i;

	/* ...appending '\0' characters won't increase length */
	newstr_empty( s );
	for ( i=0; i<numshort; ++i )
		newstr_addchar( s, '\0' );
	if ( test_consistency( s, 0, __FUNCTION__ ) || test_identity( s, "" ) )
		failed++;

	/* ...build "11111" with newstr_addchar */
	newstr_empty( s );
	for ( i=0; i<numshort; ++i )
		newstr_addchar( s, '1' );
	if ( test_consistency( s, 5, __FUNCTION__ ) || test_identity( s, "11111" ) )
		failed++;

	newstr_empty( s );
	for ( i=0; i<numchars; ++i ) {
		newstr_addchar( s, ( i % 64 ) + 64);
	}
	if ( test_consistency( s, numchars, __FUNCTION__ ) )
		failed++;

	return failed;
}

int
test_strcat( newstr *s )
{
	int failed = 0;
	int numshort = 5, numstrings = 1000, i;

	/* ...adding empty strings to an empty string shouldn't change length */
	newstr_empty( s );
	for ( i=0; i<numstrings; ++i )
		newstr_strcat( s, "" );
	if ( test_consistency( s, 0, __FUNCTION__ ) || test_identity( s, "" ) )
		failed++;

	/* ...adding empty strings to a defined string shouldn't change string */
	newstr_strcpy( s, "1" );
	for ( i=0; i<numstrings; ++i )
		newstr_strcat( s, "" );
	if ( test_consistency( s, 1, __FUNCTION__ ) || test_identity( s, "1" ) )
		failed++;

	/* ...build "1111" with newstr_strcat */
	newstr_empty( s );
	for ( i=0; i<numshort; ++i )
		newstr_strcat( s, "1" );
	if ( test_consistency( s, numshort, __FUNCTION__ ) || test_identity( s, "11111" ) )
		failed++;

	/* ...build "xoxoxoxoxo" with newstr_strcat */
	newstr_empty( s );
	for ( i=0; i<numshort; ++i )
		newstr_strcat( s, "xo" );
	if ( test_consistency( s, numshort*2, __FUNCTION__ ) || test_identity( s, "xoxoxoxoxo" ) )
		failed++;

	newstr_empty( s );
	for ( i=0; i<numstrings; ++i )
		newstr_strcat( s, "1" );
	if ( test_consistency( s, numstrings, __FUNCTION__ ) )
		failed++;

	newstr_empty( s );
	for ( i=0; i<numstrings; ++i ) {
		newstr_strcat( s, "XXOO" );
	}
	failed += test_consistency( s, numstrings*4, __FUNCTION__ );
	return failed;
}

int
test_strcpy( newstr *s )
{
	int failed = 0;
	int numstrings = 1000, i;

	/* Copying null string should reset string */
	newstr_empty( s );
	for ( i=0; i<numstrings; ++i ) {
		newstr_strcpy( s, "1" );
		newstr_strcpy( s, "" );
		if ( test_consistency( s, 0, __FUNCTION__ ) || test_identity( s, "" ) )
			failed++;
	}

	newstr_empty( s );
	for ( i=0; i<numstrings; ++i ) {
		newstr_strcpy( s, "1" );
		if ( test_consistency( s, 1, __FUNCTION__ ) || test_identity( s, "1" ) )
			failed++;
	}

	newstr_empty( s );
	for ( i=0; i<numstrings; ++i ) {
		newstr_strcpy( s, "XXOO" );
		if ( test_consistency( s, 4, __FUNCTION__ ) || test_identity( s, "XXOO" ) )
			failed++;
	}

	return failed;
}

int
test_segcpy( newstr *s )
{
	int failed = 0;
	int numstrings = 1000, i;
	char segment[]="0123456789";
	char *start=&(segment[2]), *end=&(segment[5]);
	newstr_empty( s );
	for ( i=0; i<numstrings; ++i ) {
		newstr_segcpy( s, start, end );
		if ( test_consistency( s, 3, __FUNCTION__ ) || test_identity( s, "234" ) )
			failed++;
	}
	return failed;
}

int
test_segcat( newstr *s )
{
	int failed = 0;
	int numstrings = 1000, i;
	char segment[]="0123456789";
	char *start=&(segment[2]), *end=&(segment[5]);
	newstr_empty( s );
	for ( i=0; i<numstrings; ++i ) {
		newstr_segcat( s, start, end );
	}
	failed = test_consistency( s, 3*numstrings, __FUNCTION__ );
	return failed;
}

int
test_findreplace( newstr *s )
{
	int failed = 0;
	int numstrings = 1000, i;
	char segment[]="0123456789";
	for ( i=0; i<numstrings; ++i ) {
		newstr_strcpy( s, segment );
		newstr_findreplace( s, "234", "" );
	}
	failed += test_consistency( s, 7, __FUNCTION__ );
	for ( i=0; i<numstrings; ++i ) {
		newstr_strcpy( s, segment );
		newstr_findreplace( s, "234", "223344" );
	}
	failed += test_consistency( s, 13, __FUNCTION__ );
	return failed;
}

int
main ( int argc, char *argv[] )
{
	int failed = 0;
	int ntest = 1000;
	int i;
	newstr s;
	newstr_init( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_empty( &s );
	for ( i=0; i<ntest; ++i)
		failed += test_addchar( &s );
	for ( i=0; i<ntest; ++i)
		failed += test_strcat( &s );
	for ( i=0; i<ntest; ++i)
		failed += test_strcpy( &s );
	for ( i=0; i<ntest; ++i)
		failed += test_segcpy( &s );
	for ( i=0; i<ntest; ++i)
		failed += test_segcat( &s );
	for ( i=0; i<ntest; ++i)
		failed += test_findreplace( &s );
	newstr_free( &s );
	if ( !failed ) {
		printf( "%s: PASSED\n", progname );
		return EXIT_SUCCESS;
	} else {
		printf( "%s: FAILED\n", progname );
		return EXIT_FAILURE;
	}
	return EXIT_SUCCESS;
}
