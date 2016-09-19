/*
 * newstr_test.c
 *
 * Copyright (c) 2012-2016
 *
 * Source code released under the GPL version 2
 *
 * test newstr functions
 */

/* Need to add tests for...

const char *newstr_addutf8    ( newstr *s, const char *p );
void newstr_fprintf     ( FILE *fp, newstr *s );
int  newstr_fget        ( FILE *fp, char *buf, int bufsize, int *pbufpos,
                          newstr *outs );
int  newstr_fgetline    ( newstr *s, FILE *fp );
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "newstr.h"

char progname[] = "newstr_test";
char version[] = "0.3";

int
_inconsistent_len( newstr *s, unsigned long numchars, const char *fn, unsigned long line )
{
	if ( s->len > s->dim ) {
		fprintf(stdout,"%s line %lu: failed consistency check found s->len=%lu, s->max=%lu\n",fn,line,
			s->len, s->dim );
	}
	if ( s->data ) {
		if ( s->len != strlen( s->data ) ) {
			fprintf(stdout,"%s line %lu: failed consistency check found strlen=%d, s->len=%ld\n",fn,line,(int)strlen(s->data),s->len);
			return 1;
		}
	} else {
		if ( s->len != 0 ) {
			fprintf(stdout,"%s line %lu: failed consistency check found for unallocated string, s->len=%ld\n",fn,line,s->len);
			return 1;
		}
	}
	if ( s->len != numchars ) {
		fprintf(stdout,"%s line %lu: failed consistency check found %d, expected %lu\n",fn,line,(int)strlen(s->data),numchars);
		return 1;
	}
	return 0;
}

#define inconsistent_len( a, b ) _inconsistent_len( (a), (b), __FUNCTION__, __LINE__ )

int
_test_identity( newstr *s, const char *expected, const char *fn, unsigned long line )
{
	/* Unallocated newstrings are considered identical to empty strings */
	if ( expected[0]=='\0' ) {
		if ( s->data==NULL || s->data[0]=='\0' ) return 0;
		fprintf(stdout,"%s line %lu: failed identity check found '%s', expected ''\n",fn,line,s->data);
		return 1;
	}
	/* expected!="", so s->data must exist */
	if ( !s->data ) {
		fprintf(stdout,"%s line %lu: failed identity check, s->data unallocated, expected '%s'\n",fn,line,expected);
		return 1;
	}
	if ( strcmp( s->data, expected ) == 0 ) return 0;
	fprintf(stdout,"%s line %lu: failed identity check, found '%s', expected '%s'\n",fn,line,s->data,expected);
	return 1;
}

#define test_identity( a, b ) _test_identity( (a), (b), __FUNCTION__, __LINE__ )

#define string_mismatch( a, b, c ) ( test_identity( (a), (c) ) || inconsistent_len( (a), (b) ) )

static int
test_empty( newstr *s )
{
	int failed = 0;
	int numchars = 1000, i, j;

	newstr_empty( s );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	for ( i=0; i<numchars; ++i ) {
		for ( j=0; j<i; ++j )
			newstr_addchar( s, 'x' );
		newstr_empty( s );
		if ( string_mismatch( s, 0, "" ) ) failed++;
	}

	return failed;
}

static int
test_addchar( newstr *s )
{
	int failed = 0;
	int numshort = 5, numchars = 1000, i;

	/* ...appending '\0' characters won't increase length */
	newstr_empty( s );
	for ( i=0; i<numshort; ++i )
		newstr_addchar( s, '\0' );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	/* ...build "11111" with newstr_addchar */
	newstr_empty( s );
	for ( i=0; i<numshort; ++i )
		newstr_addchar( s, '1' );
	if ( string_mismatch( s, 5, "11111" ) ) failed++;

	/* ...build a bunch of random characters */
	newstr_empty( s );
	for ( i=0; i<numchars; ++i ) {
		newstr_addchar( s, ( i % 64 ) + 64);
	}
	if ( inconsistent_len( s, numchars ) ) failed++;

	return failed;
}

static int
test_strcat( newstr *s )
{
	int failed = 0;
	int numshort = 5, numstrings = 1000, i;

	/* ...adding empty strings to an empty string shouldn't change length */
	newstr_empty( s );
	for ( i=0; i<numstrings; ++i )
		newstr_strcat( s, "" );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	/* ...adding empty strings to a defined string shouldn't change string */
	newstr_strcpy( s, "1" );
	for ( i=0; i<numstrings; ++i )
		newstr_strcat( s, "" );
	if ( string_mismatch( s, 1, "1" ) ) failed++;

	/* ...build "1111" with newstr_strcat */
	newstr_empty( s );
	for ( i=0; i<numshort; ++i )
		newstr_strcat( s, "1" );
	if ( string_mismatch( s, numshort, "11111" ) ) failed++;

	/* ...build "xoxoxoxoxo" with newstr_strcat */
	newstr_empty( s );
	for ( i=0; i<numshort; ++i )
		newstr_strcat( s, "xo" );
	if ( string_mismatch( s, numshort*2, "xoxoxoxoxo" ) ) failed++;

	newstr_empty( s );
	for ( i=0; i<numstrings; ++i )
		newstr_strcat( s, "1" );
	if ( inconsistent_len( s, numstrings ) ) failed++;

	newstr_empty( s );
	for ( i=0; i<numstrings; ++i )
		newstr_strcat( s, "XXOO" );
	if ( inconsistent_len( s, numstrings*4 ) ) failed++;

	return failed;
}

static int
test_newstrcat( newstr *s )
{
	int numshort = 5, numstrings = 1000, i;
	int failed = 0;
	newstr t;

	newstr_init( &t );

	/* ...adding empty strings to an empty string shouldn't change length */
	newstr_empty( s );
	for ( i=0; i<numstrings; ++i )
		newstr_newstrcat( s, &t );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	/* ...adding empty strings to a defined string shouldn't change string */
	newstr_strcpy( s, "1" );
	for ( i=0; i<numstrings; ++i )
		newstr_newstrcat( s, &t );
	if ( string_mismatch( s, 1, "1" ) ) failed++;

	/* ...build "1111" with newstr_strcat */
	newstr_empty( s );
	newstr_strcpy( &t, "1" );
	for ( i=0; i<numshort; ++i )
		newstr_newstrcat( s, &t );
	if ( string_mismatch( s, numshort, "11111" ) ) failed++;

	/* ...build "xoxoxoxoxo" with newstr_strcat */
	newstr_empty( s );
	newstr_strcpy( &t, "xo" );
	for ( i=0; i<numshort; ++i )
		newstr_newstrcat( s, &t );
	if ( string_mismatch( s, numshort*2, "xoxoxoxoxo" ) ) failed++;

	newstr_empty( s );
	newstr_strcpy( &t, "1" );
	for ( i=0; i<numstrings; ++i )
		newstr_newstrcat( s, &t );
	if ( inconsistent_len( s, numstrings ) ) failed++;

	newstr_empty( s );
	newstr_strcpy( &t, "XXOO" );
	for ( i=0; i<numstrings; ++i )
		newstr_newstrcat( s, &t );
	if ( inconsistent_len( s, numstrings*4 ) ) failed++;

	newstr_free( &t );

	return failed;
}

static int
test_strcpy( newstr *s )
{
	int failed = 0;
	int numstrings = 1000, i;

	/* Copying null string should reset string */
	newstr_empty( s );
	for ( i=0; i<numstrings; ++i ) {
		newstr_strcpy( s, "1" );
		newstr_strcpy( s, "" );
		if ( string_mismatch( s, 0, "" ) ) failed++;
	}

	/* Many rounds of copying just "1" should give "1" */
	newstr_empty( s );
	for ( i=0; i<numstrings; ++i ) {
		newstr_strcpy( s, "1" );
		if ( string_mismatch( s, 1, "1" ) ) failed++;
	}

	/* Many rounds of copying just "XXOO" should give "XXOO" */
	newstr_empty( s );
	for ( i=0; i<numstrings; ++i ) {
		newstr_strcpy( s, "XXOO" );
		if ( string_mismatch( s, 4, "XXOO" ) ) failed++;
	}

	return failed;
}

static int
test_newstrcpy( newstr *s )
{
	int failed = 0;
	int numstrings = 1000, i;
	newstr t;

	newstr_init( &t );

	/* Copying null string should reset string */
	newstr_empty( s );
	for ( i=0; i<numstrings; ++i ) {
		newstr_strcpy( s, "1" );
		newstr_newstrcpy( s, &t );
		if ( string_mismatch( s, 0, "" ) ) failed++;
	}

	/* Many rounds of copying just "1" should give "1" */
	newstr_empty( s );
	newstr_strcpy( &t, "1" );
	for ( i=0; i<numstrings; ++i ) {
		newstr_newstrcpy( s, &t );
		if ( string_mismatch( s, t.len, t.data ) ) failed++;
	}

	/* Many rounds of copying just "XXOO" should give "XXOO" */
	newstr_empty( s );
	newstr_strcpy( &t, "XXOO" );
	for ( i=0; i<numstrings; ++i ) {
		newstr_newstrcpy( s, &t );
		if ( string_mismatch( s, t.len, t.data ) ) failed++;
	}

	newstr_free( &t );

	return failed;
}

static int
test_segcpy( newstr *s )
{
	char segment[]="0123456789";
	char *start=&(segment[2]), *end=&(segment[5]);
	int numstrings = 1000, i;
	newstr t, u;
	int failed = 0;

	newstr_init( &t );
	newstr_init( &u );

	newstr_empty( s );
	newstr_segcpy( s, start, start );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	newstr_segcpy( &t, start, start );
	if ( string_mismatch( &t, 0, "" ) ) failed++;

	newstr_segcpy( &u, start, end );
	if ( string_mismatch( &u, 3, "234" ) ) failed++;

	newstr_empty( s );
	for ( i=0; i<numstrings; ++i ) {
		newstr_segcpy( s, start, end );
		if ( string_mismatch( s, 3, "234" ) ) failed++;
	}

	newstr_free( &t );
	newstr_free( &u );

	return failed;
}

static int
test_indxcpy( newstr *s )
{
	char segment[]="0123456789";
	int numstrings = 10, i;
	newstr t, u;
	int failed = 0;

	newstr_init( &t );
	newstr_init( &u );

	newstr_empty( s );
	newstr_indxcpy( s, segment, 2, 2 );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	newstr_indxcpy( &t, segment, 2, 2 );
	if ( string_mismatch( &t, 0, "" ) ) failed++;

	newstr_indxcpy( &u, segment, 2, 5 );
	if ( string_mismatch( &u, 3, "234" ) ) failed++;

	newstr_empty( s );
	for ( i=0; i<numstrings; ++i ) {
		newstr_indxcpy( s, segment, 2, 5 );
		if ( string_mismatch( s, 3, "234" ) ) failed++;
	}

	newstr_free( &t );
	newstr_free( &u );

	return failed;
}

/* void newstr_copyposlen  ( newstr *s, newstr *in, unsigned long pos, unsigned long len ); */
static int
test_copyposlen( newstr *s )
{
	newstr t;
	int failed = 0;

	newstr_init( &t );

	newstr_copyposlen( s, &t, 1, 5 );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	newstr_strcpy( &t, "0123456789" );

	newstr_copyposlen( s, &t, 1, 5 );
	if ( string_mismatch( s, 5, "12345" ) ) failed++;

	newstr_free( &t );

	return failed;
}

static int
test_indxcat( newstr *s )
{
	char segment[]="0123456789";
	int numstrings = 3, i;
	newstr t, u;
	int failed = 0;

	newstr_init( &t );
	newstr_init( &u );

	newstr_empty( s );
	newstr_indxcat( s, segment, 2, 2 );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	newstr_indxcat( &t, segment, 2, 2 );
	if ( string_mismatch( &t, 0, "" ) ) failed++;

	newstr_indxcat( &u, segment, 2, 5 );
	if ( string_mismatch( &u, 3, "234" ) ) failed++;

	newstr_empty( s );
	for ( i=0; i<numstrings; ++i )
		newstr_indxcat( s, segment, 2, 5 );
	if ( string_mismatch( s, 9, "234234234" ) ) failed++;

	newstr_free( &t );
	newstr_free( &u );

	return failed;
}

static int
test_segcat( newstr *s )
{
	char segment[]="0123456789";
	char *start=&(segment[2]), *end=&(segment[5]);
	int numstrings = 1000, i;
	int failed = 0;
	newstr t, u;

	newstr_init( &t );
	newstr_init( &u );

	newstr_empty( s );
	newstr_segcpy( s, start, start );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	newstr_segcpy( &t, start, start );
	if ( string_mismatch( &t, 0, "" ) ) failed++;

	newstr_segcpy( &u, start, end );
	if ( string_mismatch( &u, 3, "234" ) ) failed++;

	newstr_empty( s );
	for ( i=0; i<numstrings; ++i )
		newstr_segcat( s, start, end );
	if ( inconsistent_len( s, 3*numstrings ) ) failed++;

	newstr_free( &t );
	newstr_free( &u );

	return failed;
}

static int
test_prepend( newstr *s )
{
	int failed = 0;

	newstr_empty( s );
	newstr_prepend( s, "" );
	if ( string_mismatch( s, 0, "" ) ) failed++;
	newstr_prepend( s, "asdf" );
	if ( string_mismatch( s, 4, "asdf" ) ) failed++;

	newstr_strcpy( s, "567890" );
	newstr_prepend( s, "01234" );
	if ( string_mismatch( s, 11, "01234567890" ) ) failed++;

	return failed;
}

static int
test_pad( newstr *s )
{
	int failed = 0;

	newstr_empty( s );
	newstr_pad( s, 10, '-' );
	if ( string_mismatch( s, 10, "----------" ) ) failed++;

	newstr_strcpy( s, "012" );
	newstr_pad( s, 10, '-' );
	if ( string_mismatch( s, 10, "012-------" ) ) failed++;

	newstr_strcpy( s, "0123456789" );
	newstr_pad( s, 10, '-' );
	if ( string_mismatch( s, 10, "0123456789" ) ) failed++;

	newstr_strcpy( s, "01234567890" );
	newstr_pad( s, 10, '-' );
	if ( string_mismatch( s, 11, "01234567890" ) ) failed++;

	return failed;
}

static int
test_makepath( newstr *s )
{
	int failed = 0;

	newstr_empty( s );
	newstr_makepath( s, "", "", '/' );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	newstr_makepath( s, "", "file1.txt", '/' );
	if ( string_mismatch( s, 9, "file1.txt" ) ) failed++;

	newstr_makepath( s, "/home/user", "", '/' );
	if ( string_mismatch( s, 11, "/home/user/" ) ) failed++;

	newstr_makepath( s, "/home/user", "file1.txt", '/' );
	if ( string_mismatch( s, 20, "/home/user/file1.txt" ) ) failed++;

	newstr_makepath( s, "/home/user/", "", '/' );
	if ( string_mismatch( s, 11, "/home/user/" ) ) failed++;

	newstr_makepath( s, "/home/user/", "file1.txt", '/' );
	if ( string_mismatch( s, 20, "/home/user/file1.txt" ) ) failed++;

	return failed;
}

static int
test_findreplace( newstr *s )
{
	char segment[]="0123456789";
	int numstrings = 1000, i;
	int failed = 0;

	for ( i=0; i<numstrings; ++i ) {
		newstr_strcpy( s, segment );
		newstr_findreplace( s, "234", "" );
	}
	if ( string_mismatch( s, 7, "0156789" ) ) failed++;

	for ( i=0; i<numstrings; ++i ) {
		newstr_strcpy( s, segment );
		newstr_findreplace( s, "234", "223344" );
	}
	if ( string_mismatch( s, 13, "0122334456789" ) ) failed++;

	return failed;
}

static int
test_mergestrs( newstr *s )
{
	int failed = 0;

	newstr_empty( s );

	/* don't add any anything */
	newstr_mergestrs( s, NULL );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	/* add just one string */
	newstr_mergestrs( s, "01", NULL );
	if ( string_mismatch( s, 2, "01" ) ) failed++;

	/* add multiple strings */
	newstr_mergestrs( s, "01", "23", "45", "67", "89", NULL );
	if ( string_mismatch( s, 10, "0123456789" ) ) failed++;

	return failed;
}

static int
test_cpytodelim( newstr *s )
{
	char str0[]="\0";
	char str1[]="Col1\tCol2\tCol3\n";
	char str2[]="Col1 Col2 Col3";
	char *q;
	int failed = 0;

	q = newstr_cpytodelim( s, str0, "\t", 0 );
	if ( string_mismatch( s, 0, "" ) ) failed++;
	if ( *q!='\0' ) {
		fprintf( stdout, "%s line %d: newstr_cpytodelim() returned '%c', expected '\\t'\n", __FUNCTION__, __LINE__, *q );
		failed++;
	}

	q = newstr_cpytodelim( s, str1, "\t", 0 );
	if ( string_mismatch( s, 4, "Col1" ) ) failed++;
	if ( *q!='\t' ) {
		fprintf( stdout, "%s line %d: newstr_cpytodelim() returned '%c', expected '\\t'\n", __FUNCTION__, __LINE__, *q );
		failed++;
	}

	q = newstr_cpytodelim( s, str1, " \t", 0 );
	if ( string_mismatch( s, 4, "Col1" ) ) failed++;
	if ( *q!='\t' ) {
		fprintf( stdout, "%s line %d: newstr_cpytodelim() returned '%c', expected '\\t'\n", __FUNCTION__, __LINE__, *q );
		failed++;
	}

	q = newstr_cpytodelim( s, str1, "\t", 1 );
	if ( string_mismatch( s, 4, "Col1" ) ) failed++;
	if ( *q!='C' ) {
		fprintf( stdout, "%s line %d: newstr_cpytodelim() returned '%c', expected 'C'\n", __FUNCTION__, __LINE__, *q );
		failed++;
	}

	q = newstr_cpytodelim( s, str1, "\n", 0 );
	if ( string_mismatch( s, strlen(str1)-1, "Col1\tCol2\tCol3" ) ) failed++;
	if ( *q!='\n' ) {
		fprintf( stdout, "%s line %d: newstr_cpytodelim() returned '%c', expected '\\n'\n", __FUNCTION__, __LINE__, *q );
		failed++;
	}

	q = newstr_cpytodelim( s, str1, "\r", 0 );
	if ( string_mismatch( s, strlen(str1), "Col1\tCol2\tCol3\n" ) ) failed++;
	if ( *q!='\0' ) {
		fprintf( stdout, "%s line %d: newstr_cpytodelim() returned '%c', expected '\\n'\n", __FUNCTION__, __LINE__, *q );
		failed++;
	}

	q = newstr_cpytodelim( s, str2, " ", 0 );
	if ( string_mismatch( s, 4, "Col1" ) ) failed++;
	if ( *q!=' ' ) {
		fprintf( stdout, "%s line %d: newstr_cpytodelim() returned '%c', expected '\\t'\n", __FUNCTION__, __LINE__, *q );
		failed++;
	}

	q = newstr_cpytodelim( s, str2, "\t", 0 );
	if ( string_mismatch( s, strlen(str2), str2 ) ) failed++;
	if ( *q!='\0' ) {
		fprintf( stdout, "%s line %d: newstr_cpytodelim() returned '%c', expected '\\t'\n", __FUNCTION__, __LINE__, *q );
		failed++;
	}

	return failed;
}

/* char *newstr_caytodelim  ( newstr *s, char *p, const char *delim, unsigned char finalstep ); */
static int
test_cattodelim( newstr *s )
{
	char str1[] = "1 1 1 1 1 1 1";
	int failed = 0, i, n = 2;
	char *q;

	newstr_empty( s );
	for ( i=0; i<n; ++i ) {
		q = newstr_cattodelim( s, str1, " ", 0 );
		if ( *q!=' ' ) {
			fprintf( stdout, "%s line %d: newstr_cattodelim() returned '%c', expected ' '\n", __FUNCTION__, __LINE__, *q );
			failed++;
		}
	}
	if ( string_mismatch( s, n, "11" ) ) failed++;

	newstr_empty( s );
	q = str1;
	while ( *q ) {
		q = newstr_cattodelim( s, q, " ", 1 );
		if ( *q!='1' && *q!='\0' ) {
			fprintf( stdout, "%s line %d: newstr_cattodelim() returned '%c', expected '1' or '\\0' \n", __FUNCTION__, __LINE__, *q );
			failed++;
		}
	}
	if ( string_mismatch( s, 7, "1111111" ) ) failed++;

	return failed;
}

static int
test_strdup( void )
{
	char str1[] = "In Isbel's case and mine own. Service is no heritage: and I think I shall never have the blessing of God till I have issue o' my body; for they say barnes are blessings.";
	char str2[] = "Here once again we sit, once again crown'd, And looked upon, I hope, with cheerful eyes.";
	int failed = 0;
	newstr *dup;

	dup = newstr_strdup( "" );
	if ( dup==NULL ) {
		fprintf( stdout, "%s line %d: newstr_strdup() returned NULL\n", __FUNCTION__, __LINE__ );
		failed++;
	} else {
		if ( string_mismatch( dup, 0, "" ) ) failed++;
		newstr_delete( dup );
	}

	dup = newstr_strdup( str1 );
	if ( dup==NULL ) {
		fprintf( stdout, "%s line %d: newstr_strdup() returned NULL\n", __FUNCTION__, __LINE__ );
		failed++;
	} else {
		if ( string_mismatch( dup, strlen(str1), str1 ) ) failed++;
		newstr_delete( dup );
	}

	dup = newstr_strdup( str2 );
	if ( dup==NULL ) {
		fprintf( stdout, "%s line %d: newstr_strdup() returned NULL\n", __FUNCTION__, __LINE__ );
		failed++;
	} else {
		if ( string_mismatch( dup, strlen(str2), str2 ) ) failed++;
		newstr_delete( dup );
	}
	return failed;
}

static int
test_toupper( newstr *s )
{
	char str1[] = "abcde_ABCDE_12345";
	char str2[] = "0123456789";
	int failed = 0;

	newstr_empty( s );
	newstr_toupper( s );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	newstr_strcpy( s, str1 );
	newstr_toupper( s );
	if ( string_mismatch( s, strlen(str1), "ABCDE_ABCDE_12345" ) ) failed++;

	newstr_strcpy( s, str2 );
	newstr_toupper( s );
	if ( string_mismatch( s, strlen(str2), str2 ) ) failed++;

	return failed;
}

static int
test_tolower( newstr *s )
{
	char str1[] = "abcde_ABCDE_12345";
	char str2[] = "0123456789";
	int failed = 0;

	newstr_empty( s );
	newstr_tolower( s );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	newstr_strcpy( s, str1 );
	newstr_tolower( s );
	if ( string_mismatch( s, strlen(str1), "abcde_abcde_12345" ) ) failed++;

	newstr_strcpy( s, str2 );
	newstr_tolower( s );
	if ( string_mismatch( s, strlen(str2), str2 ) ) failed++;

	return failed;
}

static int
test_trimws( newstr *s )
{
	char str1[] = "      ksjadfk    lajskfjds      askdjflkj   ";
	char str2[] = "        ";
	int failed = 0;

	newstr_empty( s );
	newstr_trimstartingws( s );
	if ( string_mismatch( s, 0, "" ) ) failed++;
	newstr_trimendingws( s );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	newstr_strcpy( s, str2 );
	newstr_trimstartingws( s );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	newstr_strcpy( s, str2 );
	newstr_trimendingws( s );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	newstr_strcpy( s, str1 );
	newstr_trimstartingws( s );
	if ( string_mismatch( s, strlen("ksjadfk    lajskfjds      askdjflkj   "), "ksjadfk    lajskfjds      askdjflkj   " ) ) failed++;
	newstr_trimendingws( s );
	if ( string_mismatch( s, strlen("ksjadfk    lajskfjds      askdjflkj"), "ksjadfk    lajskfjds      askdjflkj" ) ) failed++;

	newstr_strcpy( s, str1 );
	newstr_trimendingws( s );
	if ( string_mismatch( s, strlen("      ksjadfk    lajskfjds      askdjflkj"), "      ksjadfk    lajskfjds      askdjflkj" ) ) failed++;
	newstr_trimstartingws( s );
	if ( string_mismatch( s, strlen("ksjadfk    lajskfjds      askdjflkj"), "ksjadfk    lajskfjds      askdjflkj" ) ) failed++;

	newstr_empty( s );
	newstr_stripws( s );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	newstr_strcpy( s, "0123456789" );
	newstr_stripws( s );
	if ( string_mismatch( s, 10, "0123456789" ) ) failed++;

	newstr_strcpy( s, str1 );
	newstr_stripws( s );
	if ( string_mismatch( s, strlen("ksjadfklajskfjdsaskdjflkj"), "ksjadfklajskfjdsaskdjflkj" ) ) failed++;

	return failed;
}

static int
test_reverse( newstr *s )
{
	int failed = 0;

	/* empty string */
	newstr_strcpy( s, "" );
	newstr_reverse( s );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	/* string with even number of elements */
	newstr_strcpy( s, "0123456789" );
	newstr_reverse( s );
	if ( string_mismatch( s, 10, "9876543210" ) ) failed++;
	newstr_reverse( s );
	if ( string_mismatch( s, 10, "0123456789" ) ) failed++;

	/* string with odd number of elements */
	newstr_strcpy( s, "123456789" );
	newstr_reverse( s );
	if ( string_mismatch( s, 9, "987654321" ) ) failed++;
	newstr_reverse( s );
	if ( string_mismatch( s, 9, "123456789" ) ) failed++;

	return failed;
}

static int
test_trim( newstr *s )
{
	char str1[] = "123456789";
	char str2[] = "987654321";
	int failed = 0;

	newstr_strcpy( s, str1 );
	newstr_trimbegin( s, 0 );
	if ( string_mismatch( s, 9, str1 ) ) failed++;
	newstr_trimend( s, 0 );
	if ( string_mismatch( s, 9, str1 ) ) failed++;

	newstr_strcpy( s, str1 );
	newstr_trimbegin( s, 1 );
	if ( string_mismatch( s, 8, "23456789" ) ) failed++;

	newstr_strcpy( s, str1 );
	newstr_trimbegin( s, 4 );
	if ( string_mismatch( s, 5, "56789" ) ) failed++;

	newstr_strcpy( s, str1 );
	newstr_trimbegin( s, 9 );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	newstr_strcpy( s, str2 );
	newstr_trimend( s, 1 );
	if ( string_mismatch( s, 8, "98765432" ) ) failed++;

	newstr_strcpy( s, str2 );
	newstr_trimend( s, 6 );
	if ( string_mismatch( s, 3, "987" ) ) failed++;

	newstr_strcpy( s, str2 );
	newstr_trimend( s, 9 );
	if ( string_mismatch( s, 0, "" ) ) failed++;

	return failed;
}

static int
test_case( newstr *s )
{
	int failed = 0;

	newstr_strcpy( s, "asdfjalskjfljasdfjlsfjd" );
	if ( !newstr_is_lowercase( s ) ) {
		fprintf( stdout, "%s line %d: newstr_is_lowercase('%s') returned false\n", __FUNCTION__, __LINE__, s->data );
		failed++;
	}
	if ( newstr_is_uppercase( s ) ) {
		fprintf( stdout, "%s line %d: newstr_is_uppercase('%s') returned true\n", __FUNCTION__, __LINE__, s->data );
		failed++;
	}
	if ( newstr_is_mixedcase( s ) ) {
		fprintf( stdout, "%s line %d: newstr_is_mixedcase('%s') returned true\n", __FUNCTION__, __LINE__, s->data );
		failed++;
	}

	newstr_strcpy( s, "ASDFJALSKJFLJASDFJLSFJD" );
	if ( newstr_is_lowercase( s ) ) {
		fprintf( stdout, "%s line %d: newstr_is_lowercase('%s') returned true\n", __FUNCTION__, __LINE__, s->data );
		failed++;
	}
	if ( !newstr_is_uppercase( s ) ) {
		fprintf( stdout, "%s line %d: newstr_is_uppercase('%s') returned false\n", __FUNCTION__, __LINE__, s->data );
		failed++;
	}
	if ( newstr_is_mixedcase( s ) ) {
		fprintf( stdout, "%s line %d: newstr_is_mixedcase('%s') returned true\n", __FUNCTION__, __LINE__, s->data );
		failed++;
	}

	newstr_strcpy( s, "ASdfjalsKJFLJASdfjlsfjd" );
	if ( newstr_is_lowercase( s ) ) {
		fprintf( stdout, "%s line %d: newstr_is_lowercase('%s') returned true\n", __FUNCTION__, __LINE__, s->data );
		failed++;
	}
	if ( newstr_is_uppercase( s ) ) {
		fprintf( stdout, "%s line %d: newstr_is_uppercase('%s') returned true\n", __FUNCTION__, __LINE__, s->data );
		failed++;
	}
	if ( !newstr_is_mixedcase( s ) ) {
		fprintf( stdout, "%s line %d: newstr_is_mixedcase('%s') returned false\n", __FUNCTION__, __LINE__, s->data );
		failed++;
	}

	return failed;
}

static int
test_newstrcmp( newstr *s )
{
	int failed = 0;
	newstr t;

	newstr_init( &t );

	newstr_empty( s );
	if ( newstr_newstrcmp( s, s ) ) {
		fprintf( stdout, "%s line %d: newstr_newstrcmp(s,s) returned non-zero\n", __FUNCTION__, __LINE__ );
		failed++;
	}
	if ( newstr_newstrcmp( s, &t ) ) {
		fprintf( stdout, "%s line %d: newstr_newstrcmp(s,t) returned non-zero\n", __FUNCTION__, __LINE__ );
		failed++;
	}

	newstr_strcpy( s, "lakjsdlfjdskljfklsjf" );
	if ( newstr_newstrcmp( s, s ) ) {
		fprintf( stdout, "%s line %d: newstr_newstrcmp(s,s) returned non-zero\n", __FUNCTION__, __LINE__ );
		failed++;
	}
	if ( !newstr_newstrcmp( s, &t ) ) {
		fprintf( stdout, "%s line %d: newstr_newstrcmp(s,t) returned zero\n", __FUNCTION__, __LINE__ );
		failed++;
	}

	newstr_newstrcpy( &t, s );
	if ( newstr_newstrcmp( s, s ) ) {
		fprintf( stdout, "%s line %d: newstr_newstrcmp(s,s) returned non-zero\n", __FUNCTION__, __LINE__ );
		failed++;
	}
	if ( newstr_newstrcmp( s, &t ) ) {
		fprintf( stdout, "%s line %d: newstr_newstrcmp(s,t) returned non-zero\n", __FUNCTION__, __LINE__ );
		failed++;
	}

	newstr_free( &t );

	return failed;
}

static int
test_match( newstr *s )
{
	int failed = 0;

	newstr_empty( s );
	if ( newstr_match_first( s, '0' ) ) {
		fprintf( stdout, "%s line %d: newstr_match_first() returned non-zero\n", __FUNCTION__, __LINE__ );
		failed++;
	}
	newstr_strcpy( s, "012345" );
	if ( !newstr_match_first( s, '0' ) ) {
		fprintf( stdout, "%s line %d: newstr_match_first() returned zero\n", __FUNCTION__, __LINE__ );
		failed++;
	}
	if ( !newstr_match_end( s, '5' ) ) {
		fprintf( stdout, "%s line %d: newstr_match_end() returned zero\n", __FUNCTION__, __LINE__ );
		failed++;
	}

	return failed;
}

static int
test_char( newstr *s )
{
	unsigned long i;
	newstr t, u;
	int failed = 0;

	newstr_init( &t );
	newstr_init( &u );

	newstr_empty( s );
	for ( i=0; i<5; ++i ) {
		if ( newstr_char( s, i ) != '\0' ) {
			fprintf( stdout, "%s line %d: newstr_char() did not return '\\0'\n", __FUNCTION__, __LINE__ );
			failed++;
		}
		if ( newstr_revchar( s, i ) != '\0' ) {
			fprintf( stdout, "%s line %d: newstr_revchar() did not return '\\0'\n", __FUNCTION__, __LINE__ );
			failed++;
		}
	}

	newstr_strcpy( s, "0123456789" );
	for ( i=0; i<s->len; ++i ) {
		newstr_addchar( &t, newstr_char( s, i ) );
		newstr_addchar( &u, newstr_revchar( s, i ) );
	}

	if ( string_mismatch( &t, s->len, s->data ) ) failed++;

	newstr_reverse( s );
	if ( string_mismatch( &u, s->len, s->data ) ) failed++;

	newstr_free( &t );
	newstr_free( &u );

	return failed;
}

static int
test_swapstrings( newstr *s )
{
	int failed = 0;
	newstr t;

	newstr_init( &t );

	newstr_strcpy( &t, "0123456789" );
	newstr_strcpy( s,  "abcde" );

	newstr_swapstrings( s, &t );
	if ( string_mismatch( &t, 5, "abcde" ) ) failed++;
	if ( string_mismatch( s, 10, "0123456789" ) ) failed++;

	newstr_swapstrings( s, &t );
	if ( string_mismatch( s, 5, "abcde" ) ) failed++;
	if ( string_mismatch( &t, 10, "0123456789" ) ) failed++;

	newstr_free( &t );

	return failed;
}

int
main ( int argc, char *argv[] )
{
	int failed = 0;
	int ntest = 2;
	int i;
	newstr s;
	newstr_init( &s );

	/* ...core functions */
	for ( i=0; i<ntest; ++i )
		failed += test_empty( &s );

	/* ...adding functions */
	for ( i=0; i<ntest; ++i)
		failed += test_addchar( &s );
	for ( i=0; i<ntest; ++i)
		failed += test_strcat( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_newstrcat( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_segcat( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_indxcat( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_cattodelim( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_prepend( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_pad( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_mergestrs( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_makepath( &s );

	/* ...copying functions */
	for ( i=0; i<ntest; ++i)
		failed += test_strcpy( &s );
	for ( i=0; i<ntest; ++i)
		failed += test_newstrcpy( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_cpytodelim( &s );
	for ( i=0; i<ntest; ++i)
		failed += test_segcpy( &s );
	for ( i=0; i<ntest; ++i)
		failed += test_indxcpy( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_copyposlen( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_strdup();

	/* ...utility functions */
	for ( i=0; i<ntest; ++i)
		failed += test_findreplace( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_reverse( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_toupper( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_tolower( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_trimws( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_trim( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_case( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_newstrcmp( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_char( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_swapstrings( &s );
	for ( i=0; i<ntest; ++i )
		failed += test_match( &s );

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
