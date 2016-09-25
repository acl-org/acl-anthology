/*
 * vplist_test.c
 *
 * Copyright (c) 2014-2016
 *
 * Source code released under the GPL version 2
 *
 *
 * test vplist functions
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>
#include "vplist.h"

/*
 * extern void     vplist_remove( vplist *vpl, int n );
 * extern void     vplist_removevp( vplist *vpl, void *v );
 * extern int      vplist_find( vplist *vpl, void *v );
 */

char progname[] = "vplist_test";
char version[] = "0.1";

#define check( a, b ) { \
	if ( !(a) ) { \
		fprintf( stderr, "Failed %s (%s) in %s line %d\n", #a, b, __FUNCTION__, __LINE__ );\
		return 1; \
	} \
}

#define check_len( a, b ) if ( !_check_len( a, b, __FUNCTION__, __LINE__ ) ) return 1;
int
_check_len( vplist *a, int expected, const char *fn, int line )
{
	if ( a->n == expected ) return 1;
	fprintf( stderr, "Failed: %s() line %d: Expected list length of %d, found %d\n", fn, line, expected, a->n );
	return 0;
}

#define check_entry( a, b, c ) if ( !_check_entry( a, b, c, __FUNCTION__, __LINE__ ) ) return 1;
int
_check_entry( vplist *a, int n, const void *expected, const char *fn, int line )
{
	void *v;
	v = vplist_get( a, n );
	if ( v==NULL && expected==NULL ) return 1;
	if ( v!=NULL && expected==NULL ) {
		fprintf( stderr, "Failed: %s() line %d: Expected list element %d to be NULL, found %p '%s'\n",
			fn, line, n, v, (char*)v );
		return 0;
	}
	if ( v==NULL && expected!=NULL ) {
		fprintf( stderr, "Failed: %s() line %d: Expected list element %d to be %p '%s', found NULL\n",
			fn, line, n, expected, (char*)expected );
		return 0;
	}
	if ( v == expected ) return 1;
	fprintf( stderr, "Failed: %s() line %d: Expected list element %d to be %p '%s', found %p '%s'\n",
		fn, line, n, expected, (char*)expected, v, (char*)v );
	return 0;
}

int
test_init( void )
{
	vplist a;

	vplist_init( &a );

	check_len( &a, 0 );
	check_entry( &a, -1, NULL );
	check_entry( &a,  0, NULL );
	check_entry( &a,  1, NULL );

	vplist_free( &a );

	return 0;
}

int
test_new( void )
{
	vplist *a;

	a = vplist_new();

	check_len( a, 0 );
	check_entry( a, -1, NULL );
	check_entry( a, 0, NULL );
	check_entry( a, 1, NULL );

	vplist_free( a );
	free( a );

	return 0;
}

int
test_add( void )
{
	char *s[5];
	vplist a;
	int i, j;

	vplist_init( &a );
	check_len( &a, 0 );

	s[0] = strdup( "0" );
	s[1] = strdup( "1" );
	s[2] = strdup( "2" );
	s[3] = strdup( "3" );
	s[4] = strdup( "4" );

	for ( i=0; i<5; ++i ) {
		vplist_add( &a, s[i] );
		check_len( &a, i+1 );
		check_entry( &a, -1, NULL );
		for ( j=0; j<=i; ++j )
			check_entry( &a, j, s[j] );
		check_entry( &a, i+1, NULL );
	}

	for ( i=0; i<5; ++i )
		free( s[i] );
	vplist_free( &a );

	return 0;
}

/*
 * extern int vplist_copy( vplist *to, vplist *from );
 */
int
test_copy( void )
{
	char *s[5], *t[5];
	vplist a, b;
	int i, j;

	vplist_init( &a );
	check_len( &a, 0 );

	vplist_init( &b );
	check_len( &b, 0 );

	s[0] = strdup( "0" );
	s[1] = strdup( "1" );
	s[2] = strdup( "2" );
	s[3] = strdup( "3" );
	s[4] = strdup( "4" );

	t[0] = strdup( "a" );
	t[1] = strdup( "b" );
	t[2] = strdup( "c" );
	t[3] = strdup( "d" );
	t[4] = strdup( "e" );

	for ( i=0; i<5; ++i ) {
		vplist_add( &a, s[i] );
		check_len( &a, i+1 );
		check_entry( &a, -1, NULL );
		for ( j=0; j<=i; ++j )
			check_entry( &a, j, s[j] );
		check_entry( &a, i+1, NULL );
	}

	for ( i=0; i<5; ++i ) {
		vplist_add( &b, t[i] );
		check_len( &b, i+1 );
		check_entry( &b, -1, NULL );
		for ( j=0; j<=i; ++j )
			check_entry( &b, j, t[j] );
		check_entry( &b, i+1, NULL );
	}

	if ( !vplist_copy( &b, &a ) ) {
		fprintf( stderr, "Failed: %s() line %d: vplist_copy() returned 0, memory error\n",
			__FUNCTION__, __LINE__ );
		return 1;
	}

	check_len( &b, 5 );
	check_entry( &b, -1, NULL );
	for ( j=0; j<5; ++j )
		check_entry( &b, j, s[j] );
	check_entry( &b, 5, NULL );

	for ( i=0; i<5; ++i ) {
		free( s[i] );
		free( t[i] );
	}
	vplist_free( &a );
	vplist_free( &b );

	return 0;
}

/*
 * extern int vplist_append( vplist *to, vplist *from );
 */
int
test_append( void )
{
	char *s[5], *t[5];
	vplist a, b;
	int i, j;

	vplist_init( &a );
	check_len( &a, 0 );

	vplist_init( &b );
	check_len( &b, 0 );

	s[0] = strdup( "0" );
	s[1] = strdup( "1" );
	s[2] = strdup( "2" );
	s[3] = strdup( "3" );
	s[4] = strdup( "4" );

	t[0] = strdup( "a" );
	t[1] = strdup( "b" );
	t[2] = strdup( "c" );
	t[3] = strdup( "d" );
	t[4] = strdup( "e" );

	for ( i=0; i<5; ++i ) {
		vplist_add( &a, s[i] );
		check_len( &a, i+1 );
		check_entry( &a, -1, NULL );
		for ( j=0; j<=i; ++j )
			check_entry( &a, j, s[j] );
		check_entry( &a, i+1, NULL );
	}

	for ( i=0; i<5; ++i ) {
		vplist_add( &b, t[i] );
		check_len( &b, i+1 );
		check_entry( &b, -1, NULL );
		for ( j=0; j<=i; ++j )
			check_entry( &b, j, t[j] );
		check_entry( &b, i+1, NULL );
	}

	if ( !vplist_append( &b, &a ) ) {
		fprintf( stderr, "Failed: %s() line %d: vplist_copy() returned 0, memory error\n",
			__FUNCTION__, __LINE__ );
		return 1;
	}

	check_len( &b, 10 );
	check_entry( &b, -1, NULL );
	for ( j=0; j<5; ++j )
		check_entry( &b, j, t[j] );
	for ( j=0; j<5; ++j )
		check_entry( &b, j+5, s[j] );
	check_entry( &b, 10, NULL );

	for ( i=0; i<5; ++i ) {
		free( s[i] );
		free( t[i] );
	}
	vplist_free( &a );
	vplist_free( &b );

	return 0;
}

/*
 * extern void * vplist_get( vplist *vpl, int n );
 */
int
test_get( void )
{
	char *s[5];
	vplist a;
	int i, j;

	vplist_init( &a );
	check_len( &a, 0 );

	s[0] = strdup( "0" );
	s[1] = strdup( "1" );
	s[2] = strdup( "2" );
	s[3] = strdup( "3" );
	s[4] = strdup( "4" );

	for ( i=0; i<5; ++i ) {
		vplist_add( &a, s[i] );
		check_len( &a, i+1 );
		check_entry( &a, -1, NULL );
		for ( j=0; j<=i; ++j )
			check_entry( &a, j, s[j] );
		check_entry( &a, i+1, NULL );
	}

	for ( i=0; i<5; ++i ) {
		if ( vplist_get( &a, i ) != s[i] ) {
			fprintf( stderr, "Failed: %s() line %d: vplist_get() returned %p '%s', expected %p '%s'\n",
				__FUNCTION__, __LINE__, vplist_get( &a, i ), (char*)vplist_get( &a, i ),
				s[i], (char*)s[i] );
			return 1;
		}
	}

	for ( i=0; i<5; ++i )
		free( s[i] );
	vplist_free( &a );

	return 0;
}


/*
 * extern void vplist_set( vplist *vpl, int n, void *v );
 */
int
test_set( void )
{
	char *s[5], *t[5];
	vplist a;
	int i, j;

	vplist_init( &a );
	check_len( &a, 0 );

	s[0] = strdup( "0" );
	s[1] = strdup( "1" );
	s[2] = strdup( "2" );
	s[3] = strdup( "3" );
	s[4] = strdup( "4" );

	t[0] = strdup( "a" );
	t[1] = strdup( "b" );
	t[2] = strdup( "c" );
	t[3] = strdup( "d" );
	t[4] = strdup( "e" );

	for ( i=0; i<5; ++i ) {
		vplist_add( &a, s[i] );
		check_len( &a, i+1 );
		check_entry( &a, -1, NULL );
		for ( j=0; j<=i; ++j )
			check_entry( &a, j, s[j] );
		check_entry( &a, i+1, NULL );
	}

	for ( i=0; i<5; ++i ) {
		vplist_set( &a, i, t[i] );
		check_len( &a, 5 );
		check_entry( &a, -1, NULL );
		for ( j=0; j<i+1; ++j )
			check_entry( &a, j, t[j] );
		for ( j=i+1; j<5; ++j )
			check_entry( &a, j, s[j] );
	}

	for ( i=0; i<5; ++i ) {
		free( s[i] );
		free( t[i] );
	}
	vplist_free( &a );

	return 0;
}

/*
 * extern int vplist_find( vplist *vpl, void *v );
 */
int
test_find( void )
{
	char *s[5], *t[5];
	vplist a;
	int i, j, n;

	vplist_init( &a );
	check_len( &a, 0 );

	s[0] = strdup( "0" );
	s[1] = strdup( "1" );
	s[2] = strdup( "2" );
	s[3] = strdup( "3" );
	s[4] = strdup( "4" );

	t[0] = strdup( "a" );
	t[1] = strdup( "b" );
	t[2] = strdup( "c" );
	t[3] = strdup( "d" );
	t[4] = strdup( "e" );

	for ( i=0; i<5; ++i ) {
		vplist_add( &a, s[i] );
		check_len( &a, i+1 );
		check_entry( &a, -1, NULL );
		for ( j=0; j<=i; ++j )
			check_entry( &a, j, s[j] );
		check_entry( &a, i+1, NULL );
	}

	for ( i=0; i<5; ++i ) {
		n = vplist_find( &a, s[i] );
		if ( n!=i ) {
			fprintf( stderr, "Failed: %s() line %d: vplist_find() returned %d, expected %d\n",
				__FUNCTION__, __LINE__, n, i );
			return 1;
		}
		n = vplist_find( &a, t[i] );
		if ( n!=-1 ) {
			fprintf( stderr, "Failed: %s() line %d: vplist_find() returned %d, expected -1\n",
				__FUNCTION__, __LINE__, n );
			return 1;
		}
	}

	for ( i=0; i<5; ++i ) {
		free( s[i] );
		free( t[i] );
	}
	vplist_free( &a );

	return 0;

}

#if 0

int
test_empty( void )
{
	newstr s, *t;
	list a;
	newstr_init( &s );
	list_init( &a );

	newstr_strcpy( &s, "1" );
	t = list_add( &a, &s );
	check_add_result( t, &s );
	check_len( &a, 1 );
	check_entry( &a, 0, "1" );
	check_entry( &a, 1, NULL );

	newstr_strcpy( &s, "2" );
	t = list_add( &a, &s );
	check_add_result( t, &s );
	check_len( &a, 2 );
	check_entry( &a, 0, "1" );
	check_entry( &a, 1, "2" );
	check_entry( &a, 2, NULL );

	list_empty( &a );
	check_len( &a, 0 );
	check_entry( &a, 0, NULL );

	list_free( &a );
	newstr_free( &s );
	return 0;
}

int
test_dup( void )
{
	char buf[1000];
	list a, *dupa;
	int i;

	list_init( &a );

	for ( i=0; i<100; ++i ) {
		sprintf( buf, "Test%d", i );
		list_addc( &a, buf );
	}

	dupa = list_dup( &a );
	if ( !dupa ) {
		fprintf( stderr, "Memory error at %s() line %d\n", __FUNCTION__, __LINE__ );
		goto out;
	}
	check_len( dupa, 100 );
	for ( i=0; i<100; ++i ) {
		sprintf( buf, "Test%d", i );
		check_entry( dupa, i, buf );
	}
	check_entry( dupa, 101, NULL );

	list_delete( dupa );

out:
	list_free( &a );

	return 0;
}

/*
 * int list_append( list *a, list *toadd );
 */
int
test_append( void )
{
	int status;
	newstr *s;
	list a, c;

	list_init( &a );
	list_init( &c );

	status = list_addc_all( &a, "amateurish", "boorish", NULL );
	if ( status!=LIST_OK ) { return 1; }

	check_len( &a, 2 );
	check_entry( &a, 0, "amateurish" );
	check_entry( &a, 1, "boorish" );
	check_entry( &a, 2, NULL );

	status = list_addc_all( &c, "churlish", "dull", NULL );
	if ( status!=LIST_OK ) { return 1; }

	check_len( &c, 2 );
	check_entry( &c, 0, "churlish" );
	check_entry( &c, 1, "dull" );
	check_entry( &c, 2, NULL );

	status = list_append( &a, &c );
	if ( status!=LIST_OK ) { return 1; }

	check_len( &a, 4 );
	check_entry( &a, 0, "amateurish" );
	check_entry( &a, 1, "boorish" );
	check_entry( &a, 2, "churlish" );
	check_entry( &a, 3, "dull" );
	check_entry( &a, 4, NULL );

	check_len( &c, 2 );
	check_entry( &c, 0, "churlish" );
	check_entry( &c, 1, "dull" );
	check_entry( &c, 2, NULL );

	list_free( &a );
	list_free( &c );

	return 0;
}

/*
 * int list_append_unique( list *a, list *toadd );
 */
int
test_append_unique( void )
{
	int status;
	newstr *s;
	list a, c;

	list_init( &a );
	list_init( &c );

	status = list_addc_all( &a, "amateurish", "boorish", NULL );
	if ( status!=LIST_OK ) { return 1; }

	check_len( &a, 2 );
	check_entry( &a, 0, "amateurish" );
	check_entry( &a, 1, "boorish" );
	check_entry( &a, 2, NULL );

	status = list_addc_all( &c, "churlish", "boorish", NULL );
	if ( status!=LIST_OK ) { return 1; }

	check_len( &c, 2 );
	check_entry( &c, 0, "churlish" );
	check_entry( &c, 1, "boorish" );
	check_entry( &c, 2, NULL );

	status = list_append_unique( &a, &c );
	if ( status!=LIST_OK ) { return 1; }

	check_len( &a, 3 );
	check_entry( &a, 0, "amateurish" );
	check_entry( &a, 1, "boorish" );
	check_entry( &a, 2, "churlish" );
	check_entry( &a, 3, NULL );

	check_len( &c, 2 );
	check_entry( &c, 0, "churlish" );
	check_entry( &c, 1, "boorish" );
	check_entry( &c, 2, NULL );

	status = list_append_unique( &a, &c );
	if ( status!=LIST_OK ) { return 1; }

	check_len( &a, 3 );
	check_entry( &a, 0, "amateurish" );
	check_entry( &a, 1, "boorish" );
	check_entry( &a, 2, "churlish" );
	check_entry( &a, 3, NULL );

	check_len( &c, 2 );
	check_entry( &c, 0, "churlish" );
	check_entry( &c, 1, "boorish" );
	check_entry( &c, 2, NULL );

	list_free( &a );
	list_free( &c );

	return 0;
}

/*
 * int list_remove( list *a, int n );
 */
int
test_remove( void )
{
	int status;
	list a;

	list_init( &a );

	status = list_addc_all( &a, "amateurish", "boorish", "churlish", "dull", NULL );
	if ( status!=LIST_OK ) { return 1; }

	check_len( &a, 4 );
	check_entry( &a, 0, "amateurish" );
	check_entry( &a, 1, "boorish" );
	check_entry( &a, 2, "churlish" );
	check_entry( &a, 3, "dull" );
	check_entry( &a, 4, NULL );

	status = list_remove( &a, 2 );
	if ( status!=LIST_OK ) { return 1; }

	check_len( &a, 3 );
	check_entry( &a, 0, "amateurish" );
	check_entry( &a, 1, "boorish" );
	check_entry( &a, 2, "dull" );
	check_entry( &a, 3, NULL );

	status = list_remove( &a, 1 );
	if ( status!=LIST_OK ) { return 1; }

	check_len( &a, 2 );
	check_entry( &a, 0, "amateurish" );
	check_entry( &a, 1, "dull" );
	check_entry( &a, 2, NULL );

	status = list_remove( &a, 100 );
	if ( status!=-1 ) { return 1; }

	check_len( &a, 2 );
	check_entry( &a, 0, "amateurish" );
	check_entry( &a, 1, "dull" );
	check_entry( &a, 2, NULL );

	list_free( &a );

	return 0;
}

/*
 * void list_sort( list *a );
 */
int
test_sort( void )
{
	int status;
	list a;

	list_init( &a );

	list_sort( &a );

	check_len( &a, 0 );

	status = list_addc_all( &a, "dull", "churlish", "boorish", "amateurish", NULL );
	if ( status!=LIST_OK ) { return 1; }

	check_len( &a, 4 );
	check_entry( &a, 0, "dull" );
	check_entry( &a, 1, "churlish" );
	check_entry( &a, 2, "boorish" );
	check_entry( &a, 3, "amateurish" );
	check_entry( &a, 4, NULL );

	list_sort( &a );

	check_len( &a, 4 );
	check_entry( &a, 0, "amateurish" );
	check_entry( &a, 1, "boorish" );
	check_entry( &a, 2, "churlish" );
	check_entry( &a, 3, "dull" );
	check_entry( &a, 4, NULL );

	list_empty( &a );

	status = list_addc_all( &a, "churlish", "boorish", "amateurish", NULL );
	if ( status!=LIST_OK ) { return 1; }

	check_len( &a, 3 );
	check_entry( &a, 0, "churlish" );
	check_entry( &a, 1, "boorish" );
	check_entry( &a, 2, "amateurish" );
	check_entry( &a, 3, NULL );

	list_sort( &a );

	check_len( &a, 3 );
	check_entry( &a, 0, "amateurish" );
	check_entry( &a, 1, "boorish" );
	check_entry( &a, 2, "churlish" );
	check_entry( &a, 3, NULL );

	list_free( &a );

	return 0;
}

/*
 * newstr* list_get( list *a, int n );
 */
int
test_get( void )
{
	int status;
	newstr *s;
	list a;

	list_init( &a );

	status = list_addc_all( &a, "churlish", "boorish", "amateurish", NULL );
	if ( status!=LIST_OK ) { return 1; }

	s = list_get( &a, -1 );
	if ( s!=NULL ) return 1;

	s = list_get( &a, 0 );
	if ( s==NULL || strcmp( s->data, "churlish" ) ) return 1;

	s = list_get( &a, 1 );
	if ( s==NULL || strcmp( s->data, "boorish" ) ) return 1;

	s = list_get( &a, 2 );
	if ( s==NULL || strcmp( s->data, "amateurish" ) ) return 1;

	s = list_get( &a, 3 );
	if ( s!=NULL ) return 1;

	list_free( &a );

	return 0;
}

/*
 * char* list_getc( list *a, int n );
 */
int
test_getc( void )
{
	int status;
	char *s;
	list a;

	list_init( &a );

	status = list_addc_all( &a, "churlish", "boorish", "amateurish", NULL );
	if ( status!=LIST_OK ) { return 1; }

	s = list_getc( &a, -1 );
	if ( s!=NULL ) return 1;

	s = list_getc( &a, 0 );
	if ( s==NULL || strcmp( s, "churlish" ) ) return 1;

	s = list_getc( &a, 1 );
	if ( s==NULL || strcmp( s, "boorish" ) ) return 1;

	s = list_getc( &a, 2 );
	if ( s==NULL || strcmp( s, "amateurish" ) ) return 1;

	s = list_getc( &a, 3 );
	if ( s!=NULL ) return 1;

	list_free( &a );

	return 0;
}

/*
 * newstr* list_set( list *a, int n, newstr *s );
 */
int
test_set( void )
{
	int status;
	newstr s, *t;
	list a;

	list_init( &a );
	newstr_init( &s );

	newstr_strcpy( &s, "puerile" );

	status = list_addc_all( &a, "churlish", "boorish", "amateurish", NULL );
	if ( status!=LIST_OK ) { return 1; }

	t = list_set( &a, -1, &s );
	if ( t!=NULL ) return 1;

	t = list_set( &a, 3, &s );
	if ( t!=NULL ) return 1;

	t = list_set( &a, 1, &s );
	if ( t==NULL ) return 1;

	check_len( &a, 3 );
	check_entry( &a, 0, "churlish" );
	check_entry( &a, 1, "puerile" );
	check_entry( &a, 2, "amateurish" );

	t = list_set( &a, 0, &s );
	if ( t==NULL ) return 1;

	check_len( &a, 3 );
	check_entry( &a, 0, "puerile" );
	check_entry( &a, 1, "puerile" );
	check_entry( &a, 2, "amateurish" );

	t = list_set( &a, 2, &s );
	if ( t==NULL ) return 1;

	check_len( &a, 3 );
	check_entry( &a, 0, "puerile" );
	check_entry( &a, 1, "puerile" );
	check_entry( &a, 2, "puerile" );

	list_free( &a );
	newstr_free( &s );

	return 0;
}

/*
 * newstr* list_setc( list *a, int n, const char *s );
 */
int
test_setc( void )
{
	int status;
	newstr *t;
	list a;

	list_init( &a );

	status = list_addc_all( &a, "churlish", "boorish", "amateurish", NULL );
	if ( status!=LIST_OK ) { return 1; }

	t = list_setc( &a, -1, "puerile" );
	if ( t!=NULL ) return 1;

	t = list_setc( &a, 3, "puerile" );
	if ( t!=NULL ) return 1;

	t = list_setc( &a, 1, "puerile" );
	if ( t==NULL ) return 1;

	check_len( &a, 3 );
	check_entry( &a, 0, "churlish" );
	check_entry( &a, 1, "puerile" );
	check_entry( &a, 2, "amateurish" );

	t = list_setc( &a, 0, "puerile" );
	if ( t==NULL ) return 1;

	check_len( &a, 3 );
	check_entry( &a, 0, "puerile" );
	check_entry( &a, 1, "puerile" );
	check_entry( &a, 2, "amateurish" );

	t = list_setc( &a, 2, "puerile" );
	if ( t==NULL ) return 1;

	check_len( &a, 3 );
	check_entry( &a, 0, "puerile" );
	check_entry( &a, 1, "puerile" );
	check_entry( &a, 2, "puerile" );

	list_free( &a );

	return 0;
}

/*
 * int list_find( list *a, const char *searchstr );
 */
int
test_find( void )
{
	int n, status;
	list a;

	list_init( &a );

	status = list_addc_all( &a, "churlish", "boorish", "amateurish", NULL );
	if ( status!=LIST_OK ) { return 1; }

	n = list_find( &a, "dull" );
	if ( n!=-1 ) return 1;

	n = list_find( &a, "churlish" );
	if ( n!=0 ) return 1;

	n = list_find( &a, "boorish" );
	if ( n!=1 ) return 1;

	n = list_find( &a, "amateurish" );
	if ( n!=2 ) return 1;

	list_free( &a );

	return 0;
}

/*
 * int list_findnocase( list *a, const char *searchstr );
 */
int
test_findnocase( void )
{
	int n, status;
	list a;

	list_init( &a );

	status = list_addc_all( &a, "churlish", "boorish", "amateurish", NULL );
	if ( status!=LIST_OK ) { return 1; }

	n = list_findnocase( &a, "dull" );
	if ( n!=-1 ) return 1;

	n = list_findnocase( &a, "churlish" );
	if ( n!=0 ) return 1;

	n = list_findnocase( &a, "CHURlish" );
	if ( n!=0 ) return 1;

	n = list_findnocase( &a, "churLISH" );
	if ( n!=0 ) return 1;

	n = list_findnocase( &a, "boorish" );
	if ( n!=1 ) return 1;

	n = list_findnocase( &a, "Boorish" );
	if ( n!=1 ) return 1;

	n = list_findnocase( &a, "BOORISH" );
	if ( n!=1 ) return 1;

	n = list_findnocase( &a, "aMaTeUrIsH" );
	if ( n!=2 ) return 1;

	list_free( &a );

	return 0;
}

/*
 * int list_match_entry( list *a, int n, char *s );
 */
int
test_match_entry( void )
{
	int n, status;
	list a;

	list_init( &a );

	status = list_addc_all( &a, "churlish", "boorish", "amateurish", NULL );
	if ( status!=LIST_OK ) { return 1; }

	n = list_match_entry( &a, 0, "churlish" );
	if ( n==0 ) return 1;
	n = list_match_entry( &a, 0, "boorish" );
	if ( n ) return 1;
	n = list_match_entry( &a, 0, "amateurish" );
	if ( n ) return 1;
	n = list_match_entry( &a, 0, "dull" );
	if ( n ) return 1;

	n = list_match_entry( &a, 1, "churlish" );
	if ( n ) return 1;
	n = list_match_entry( &a, 1, "boorish" );
	if ( n==0 ) return 1;
	n = list_match_entry( &a, 1, "amateurish" );
	if ( n ) return 1;
	n = list_match_entry( &a, 1, "dull" );
	if ( n ) return 1;

	n = list_match_entry( &a, 2, "churlish" );
	if ( n ) return 1;
	n = list_match_entry( &a, 2, "boorish" );
	if ( n ) return 1;
	n = list_match_entry( &a, 2, "amateurish" );
	if ( n==0 ) return 1;
	n = list_match_entry( &a, 2, "dull" );
	if ( n ) return 1;

	n = list_match_entry( &a, 3, "churlish" );
	if ( n ) return 1;
	n = list_match_entry( &a, 3, "boorish" );
	if ( n ) return 1;
	n = list_match_entry( &a, 3, "amateurish" );
	if ( n ) return 1;
	n = list_match_entry( &a, 3, "dull" );
	if ( n ) return 1;

	list_free( &a );

	return 0;
}

/*
 * void list_trimend( list *a, int n );
 */
int
test_trimend( void )
{
	int n, status;
	list a;

	list_init( &a );

	status = list_addc_all( &a, "churlish", "boorish", "amateurish", NULL );
	if ( status!=LIST_OK ) { return 1; }

	check_len( &a, 3 );
	check_entry( &a, 0, "churlish" );
	check_entry( &a, 1, "boorish" );
	check_entry( &a, 2, "amateurish" );
	check_entry( &a, 3, NULL );

	list_trimend( &a, 1 );

	check_len( &a, 2 );
	check_entry( &a, 0, "churlish" );
	check_entry( &a, 1, "boorish" );
	check_entry( &a, 2, NULL );

	list_trimend( &a, 2 );

	check_len( &a, 0 );
	check_entry( &a, 0, NULL );

	list_free( &a );

	return 0;
}

/*
extern int     list_fill( list *a, const char *filename, unsigned char skip_blank_lines );
extern int     list_fillfp( list *a, FILE *fp, unsigned char skip_blank_lines );
*/

int
test_fill( void )
{
	char filename[512];
	unsigned long val;
	int status, i;
	FILE *fp;
	list a;

	val = ( unsigned long ) getpid();
	sprintf( filename, "test_list.%lu", val );

	fp = fopen( filename, "w" );
	if ( !fp ) {
		fprintf( stderr, "%s: Could not open file %s\n", progname, filename );
		return 1;
	}

	fprintf( fp, "Line 1\n" );
	fprintf( fp, "Line 2\n" );
	fprintf( fp, "\n" );
	fprintf( fp, "Line 4\n" );
	fprintf( fp, "\n" );
	fprintf( fp, "Line 6\n" );

	fclose( fp );

	list_init( &a );

	status = list_fill( &a, filename, 0 );
	if ( status==LIST_ERR_CANNOTOPEN ) {
		fprintf( stderr, "%s: Could not open file %s\n", progname, filename );
		return 1;
	} else if ( status!=LIST_OK ) {
		fprintf( stderr, "%s: Could not list_fill() %s\n", progname, filename );
		return 1;
	}
	check_len( &a, 6 );
	check_entry( &a, 0, "Line 1" );
	check_entry( &a, 1, "Line 2" );
	check_entry( &a, 2, "" );
	check_entry( &a, 3, "Line 4" );
	check_entry( &a, 4, "" );
	check_entry( &a, 5, "Line 6" );

	list_empty( &a );

	status = list_fill( &a, filename, 1 );
	if ( status==LIST_ERR_CANNOTOPEN ) {
		fprintf( stderr, "%s: Could not open file %s\n", progname, filename );
		return 1;
	} else if ( status!=LIST_OK ) {
		fprintf( stderr, "%s: Could not list_fill() %s\n", progname, filename );
		return 1;
	}

	check_len( &a, 4 );
	check_entry( &a, 0, "Line 1" );
	check_entry( &a, 1, "Line 2" );
	check_entry( &a, 2, "Line 4" );
	check_entry( &a, 3, "Line 6" );

	list_free( &a );

	status = unlink( filename );
	if ( status!=0 )
		fprintf( stderr, "%s: Error unlink failed for %s\n", progname, filename );

	return 0;
}

/*
 * void lists_init( list *a, ... );
 * void lists_free( list *a, ... );
 * void lists_empty( list *a, ... );
 */
int
test_lists( void )
{
	char buf[1000];
	list a, b, c;
	int i;

	lists_init( &a, &b, &c, NULL );
	check_len( &a, 0 );
	check_len( &b, 0 );
	check_len( &c, 0 );
	check_entry( &a, 0, NULL );
	check_entry( &b, 0, NULL );
	check_entry( &c, 0, NULL );

	for ( i=0; i<10; ++i ) {
		sprintf( buf, "a_entry%d\n", i );
		list_addc( &a, buf );
	}
	for ( i=0; i<100; ++i ) {
		sprintf( buf, "b_entry%d\n", i );
		list_addc( &b, buf );
	}
	for ( i=0; i<1000; ++i ) {
		sprintf( buf, "c_entry%d\n", i );
		list_addc( &c, buf );
	}
	check_len( &a, 10 );
	check_len( &b, 100 );
	check_len( &c, 1000 );
	check_entry( &a, 10, NULL );
	check_entry( &b, 100, NULL );
	check_entry( &c, 1000, NULL );
	for ( i=0; i<10; ++i ) {
		sprintf( buf, "a_entry%d\n", i );
		check_entry( &a, i, buf );
	}
	for ( i=0; i<100; ++i ) {
		sprintf( buf, "b_entry%d\n", i );
		check_entry( &b, i, buf );
	}
	for ( i=0; i<1000; ++i ) {
		sprintf( buf, "c_entry%d\n", i );
		check_entry( &c, i, buf );
	}

	lists_empty( &a, &b, &c, NULL );
	check_len( &a, 0 );
	check_len( &b, 0 );
	check_len( &c, 0 );
	check_entry( &a, 0, NULL );
	check_entry( &b, 0, NULL );
	check_entry( &c, 0, NULL );

	lists_free( &a, &b, &c, NULL );

	return 0;
}
#endif

int
main( int argc, char *argv[] )
{
	int failed = 0;

	failed += test_init();
	failed += test_new();

	failed += test_add();
	failed += test_copy();
	failed += test_append();

	failed += test_get();
	failed += test_set();
#if 0

	failed += test_empty();
	failed += test_new();
	failed += test_dup();
	failed += test_copy();
	failed += test_append();
	failed += test_append_unique();
	failed += test_remove();
	failed += test_sort();

	failed += test_find();
	failed += test_findnocase();
	failed += test_match_entry();

	failed += test_fill();

	failed += test_trimend();

	failed += test_lists();
#endif
	if ( !failed ) {
		printf( "%s: PASSED\n", progname );
		return EXIT_SUCCESS;
	} else {
		printf( "%s: FAILED\n", progname );
		return EXIT_FAILURE;
	}

	return EXIT_SUCCESS;
}
