/*
 * list_test.c
 *
 * Copyright (c) 2013-2016
 *
 * Source code released under the GPL version 2
 *
 *
 * test list functions
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>
#include "list.h"

char progname[] = "list_test";
char version[] = "0.2";

#define check( a, b ) { \
	if ( !(a) ) { \
		fprintf( stderr, "Failed %s (%s) in %s line %d\n", #a, b, __FUNCTION__, __LINE__ );\
		return 1; \
	} \
}

#define check_len( a, b ) if ( !_check_len( a, b, __FUNCTION__, __LINE__ ) ) return 1;
int
_check_len( list *a, int expected, const char *fn, int line )
{
	if ( a->n == expected ) return 1;
	fprintf( stderr, "Failed: %s() line %d: Expected list length of %d, found %d\n", fn, line, expected, a->n );
	return 0;
}

#define check_entry( a, b, c ) if ( !_check_entry( a, b, c, __FUNCTION__, __LINE__ ) ) return 1;
int
_check_entry( list *a, int n, const char *expected, const char *fn, int line )
{
	char *s;
	s = list_getc( a, n );
	if ( s==NULL && expected==NULL ) return 1;
	if ( s!=NULL && expected==NULL ) {
		fprintf( stderr, "Failed: %s() line %d: Expected list element %d to be NULL, found '%s'\n",
			fn, line, n, s );
		return 0;
	}
	if ( s==NULL && expected!=NULL ) {
		fprintf( stderr, "Failed: %s() line %d: Expected list element %d to be '%s', found NULL\n",
			fn, line, n, expected );
		return 0;
	}
	if ( !strcmp( s, expected ) ) return 1;
	fprintf( stderr, "Failed: %s() line %d: Expected list element %d to be '%s', found '%s'\n",
		fn, line, n, expected, s );
	return 0;
}

#define check_add_result( a, b ) if ( !_check_add_result( a, b, __FUNCTION__, __LINE__ ) ) return 1;
int
_check_add_result( newstr *obtained, newstr *expected, const char *fn, int line )
{
	if ( obtained==NULL && expected!=NULL ) {
		fprintf( stderr, "Failed to add string: %s() line %d: Expected '%s'\n",
			fn, line, expected->data );
		return 0;
	}
	return 1;
}

#define check_addc_result( a, b ) if ( !_check_addc_result( a, b, __FUNCTION__, __LINE__ ) ) return 1;
int
_check_addc_result( newstr *obtained, char *expected, const char *fn, int line )
{
	if ( obtained==NULL && expected!=NULL ) {
		fprintf( stderr, "Failed to add string: %s() line %d: Expected '%s'\n",
			fn, line, expected );
		return 0;
	}
	return 1;
}

void
list_dump( list *a )
{
	int i;
	printf( "{" );
	for ( i=0; i<a->n; ++i ) {
		if ( i==0 ) printf( " \"%s\"", list_getc( a, i ) );
		else printf( ", \"%s\"", list_getc( a, i ) );
	}
	printf( " }\n" );
}

int
test_init( void )
{
	list a;

	list_init( &a );

	check_len( &a, 0 );
	check_entry( &a, -1, NULL );
	check_entry( &a,  0, NULL );
	check_entry( &a,  1, NULL );

	list_free( &a );

	return 0;
}

int
test_add( void )
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

	list_free( &a );
	newstr_free( &s );
	return 0;
}

int
test_addc( void )
{
	newstr *t;
	list a;
	list_init( &a );

	t = list_addc( &a, "1" );
	check_addc_result( t, "1" );
	check_len( &a, 1 );
	check_entry( &a, 0, "1" );
	check_entry( &a, 1, NULL );

	t = list_addc( &a, "2" );
	check_addc_result( t, "2" );
	check_len( &a, 2 );
	check_entry( &a, 0, "1" );
	check_entry( &a, 1, "2" );
	check_entry( &a, 2, NULL );

	list_free( &a );
	return 0;
}

int
test_addvp( void )
{
	newstr s, *t;
	list a;
	newstr_init( &s );
	list_init( &a );

	t= list_addvp( &a, LIST_CHR, "1" );
	check_addc_result( t, "1" );
	check_len( &a, 1 );
	check_entry( &a, 0, "1" );
	check_entry( &a, 1, NULL );

	newstr_strcpy( &s, "2" );
	t = list_addvp( &a, LIST_STR, &s );
	check_add_result( t, &s );
	check_len( &a, 2 );
	check_entry( &a, 0, "1" );
	check_entry( &a, 1, "2" );
	check_entry( &a, 2, NULL );

	newstr_free( &s );
	list_free( &a );
	return 0;
}

int
test_add_all( void )
{
	newstr s, t;
	int i, j;
	list a;

	newstr_initstr( &s, "a" );
	newstr_initstr( &t, "b" );
	list_init( &a );

	for ( j=0; j<10; ++j ) {
		for ( i=0; i<10; ++i ) {
			list_add_all( &a, &s, &t, NULL );
			check_len( &a, (i+1)*2 );
		}
		list_empty( &a );
	}

	for ( i=0; i<a.n; ++i ) {
		if ( i % 2 == 0 ) {
			check_entry( &a, i, "a" );
		} else {
			check_entry( &a, i, "b" );
		}
	}

	newstr_free( &s );
	newstr_free( &t );
	list_free( &a );

	return 0;
}

int
test_addc_all( void )
{
	int i, j;
	char *u;
	list a;

	list_init( &a );

	for ( j=0; j<10; ++j ) {
		for ( i=0; i<10; ++i ) {
			list_addc_all( &a, "a", "b", NULL );
			check_len( &a, (i+1)*2 );
		}
		list_empty( &a );
	}

	for ( i=0; i<a.n; ++i ) {
		u = list_getc( &a, i );
		if ( i % 2 == 0 ) {
			check( (!strcmp(u,"a")), "even entries should be 'a'" );
		} else {
			check( (!strcmp(u,"b")), "odd entries should be 'b'" );
		}
	}

	list_free( &a );

	return 0;
}

int
test_addvp_all( void )
{
	newstr s, t;
	int i, j;
	char *u;
	list a;

	newstr_init( &s );
	newstr_init( &t );
	list_init( &a );

	newstr_strcpy( &s, "amateurish" );
	newstr_strcpy( &s, "boorish" );
	for ( j=0; j<10; ++j ) {
		for ( i=0; i<10; ++i ) {
			if ( i%2==0 ) list_addvp_all( &a, LIST_CHR, "amateurish", "boorish", NULL );
			else          list_addvp_all( &a, LIST_STR, &s,  &t,  NULL );
			check( ( a.n == (i+1)*2 ), "length should increase by 2 each time" );
		}
		list_empty( &a );
	}

	for ( i=0; i<a.n; ++i ) {
		u = list_getc( &a, i );
		if ( i % 2 == 0 ) {
			check( (!strcmp(u,"amateurish")), "even entries should be 'amateurish'" );
		} else {
			check( (!strcmp(u,"boorish")), "odd entries should be 'boorish'" );
		}
	}

	newstr_free( &s );
	newstr_free( &t );
	list_free( &a );

	return 0;
}

/*
 * newstr * list_add_unique( list *a, newstr *value );
 */
int
test_add_unique( void )
{
	newstr s, t;
	int i, j;
	list a;

	newstr_initstr( &s, "amateurish" );
	newstr_initstr( &t, "boorish" );
	list_init( &a );

	for ( j=0; j<10; ++j ) {
		for ( i=0; i<10; ++i ) {
			list_add_unique( &a, &s );
			check_len( &a, 1 );
		}
		list_empty( &a );
	}

	for ( j=0; j<10; ++j ) {
		for ( i=0; i<10; ++i ) {
			list_add_unique( &a, &s );
			list_add_unique( &a, &t );
			check_len( &a, 2 );
		}
		list_empty( &a );
	}

	newstr_free( &s );
	newstr_free( &t );
	list_free( &a );

	return 0;
}

/*
 * newstr * list_addc_unique( list *a, const char *value );
 */
int
test_addc_unique( void )
{
	int i, j;
	list a;

	list_init( &a );

	for ( j=0; j<10; ++j ) {
		for ( i=0; i<10; ++i ) {
			list_addc_unique( &a, "puerile" );
			check_len( &a, 1 );
		}
		list_empty( &a );
	}

	for ( j=0; j<10; ++j ) {
		for ( i=0; i<10; ++i ) {
			list_addc_unique( &a, "puerile" );
			list_addc_unique( &a, "immature" );
			check_len( &a, 2 );
		}
		list_empty( &a );
	}

	list_free( &a );

	return 0;
}

/*
 * newstr * list_addvp_unique( list *a, unsigned char mode, void *vp );
 */
int
test_addvp_unique( void )
{
	newstr s, t;
	int i, j;
	list a;

	list_init( &a );
	newstr_init( &s );
	newstr_init( &t );

	newstr_strcpy( &s, "puerile" );
	newstr_strcpy( &t, "immature" );

	for ( j=0; j<10; ++j ) {
		for ( i=0; i<10; ++i ) {
			if ( i%2==0 ) list_addvp_unique( &a, LIST_CHR, "puerile" );
			else          list_addvp_unique( &a, LIST_STR, &s );
			check_len( &a, 1 );
		}
		list_empty( &a );
	}

	for ( j=0; j<10; ++j ) {
		for ( i=0; i<10; ++i ) {
			if ( i%2==0 ) {
				list_addvp_unique( &a, LIST_CHR, "puerile" );
				list_addvp_unique( &a, LIST_CHR, "immature" );
			} else {
				list_addvp_unique( &a, LIST_STR, &s );
				list_addvp_unique( &a, LIST_STR, &t );
			}
			check_len( &a, 2 );
		}
		list_empty( &a );
	}

	list_free( &a );
	newstr_free( &s );
	newstr_free( &t );

	return 0;
}

int
test_addsorted( void )
{
	int status, i;
	list a, b, *c;

	list_init( &a );
	list_init( &b );

	/* Check to see if sorted flag is initialized and reset with empty lists */
	check( (a.sorted!=0), "empty list a should be sorted" );
	list_addc_all( &a, "1", "2", "10", "40", "0", "100", NULL );
	check( (a.sorted==0 ), "added elements aren't sorted" );
	list_empty( &a );
	check_len( &a, 0 );
	check( (a.sorted!=0), "empty list a should be sorted" );

	/* Check to see if list_add_all() recognizes unsorted input */
	list_addc_all( &a, "1", "2", "10", "40", "0", "100", NULL );
	check( (a.sorted==0 ), "added elements aren't sorted" );

	list_sort( &a );
	check( (a.sorted!=0 ), "list_sort() should sort list" );

	/* Copy list entries from sorted list a to list b and check b sort status */
	for ( i=0; i<a.n; ++i )
		list_add( &b, list_get( &a, i ) );
	check_len( &a, b.n );
	check( (b.sorted!=0), "empty list b should be sorted" );

	/* Copy list with list_copy() and check sort status */
	list_empty( &b );
	status = list_copy( &b, &a );
	check( (status==LIST_OK), "list_copy() return LIST_OK on success" );
	check_len( &a, b.n );
	check( (b.sorted!=0), "empty list b should be sorted" );

	/* Copy list with list_dup() and check sort status */
	c = list_dup( &a );
	check_len( &a, c->n );
	check( (c->sorted!=0), "empty list b should be sorted" );
	list_delete( c );

	/* Check to see if list_addc_all() recognizes sorted inserts */
	list_empty( &a );
	check_len( &a, 0 );
	list_addc_all( &a, "0", "1", "10", "100", "2", "40", NULL );
	check( (a.sorted!=0), "list a should be sorted" );

	list_free( &a );
	list_free( &b );
	return 0;
}

int
test_tokenize( void )
{
	newstr s;
	list a;

	newstr_init( &s );
	list_init( &a );

	list_tokenizec( &a, "1 2 3 4 5", " \t", 0 );
	check( (a.n==5), "list a should have five elements" );
	check( (!strcmp(list_getc(&a,0),"1")), "first element should be '1'" );
	check( (!strcmp(list_getc(&a,1),"2")), "second element should be '2'" );
	check( (!strcmp(list_getc(&a,2),"3")), "third element should be '3'" );
	check( (!strcmp(list_getc(&a,3),"4")), "fourth element should be '4'" );
	check( (!strcmp(list_getc(&a,4),"5")), "fifth element should be '5'" );
	list_empty( &a );

	list_tokenizec( &a, "1\t2\t3\t4\t5", " \t", 1 );
	check( (a.n==5), "list a should have five elements" );
	check( (!strcmp(list_getc(&a,0),"1")), "first element should be '1'" );
	check( (!strcmp(list_getc(&a,1),"2")), "second element should be '2'" );
	check( (!strcmp(list_getc(&a,2),"3")), "third element should be '3'" );
	check( (!strcmp(list_getc(&a,3),"4")), "fourth element should be '4'" );
	check( (!strcmp(list_getc(&a,4),"5")), "fifth element should be '5'" );
	list_empty( &a );

	list_tokenizec( &a, "1  2 3 4", " \t", 0 );
	check( (a.n==5), "list a should have five elements" );
	check( (!strcmp(list_getc(&a,0),"1")), "first element should be '1'" );
	check( (!strcmp(list_getc(&a,1),"")), "second element should be ''" );
	check( (!strcmp(list_getc(&a,2),"2")), "third element should be '2'" );
	check( (!strcmp(list_getc(&a,3),"3")), "fourth element should be '3'" );
	check( (!strcmp(list_getc(&a,4),"4")), "fifth element should be '4'" );
	list_empty( &a );

	list_tokenizec( &a, "1  2 3 4", " \t", 1 );
	check( (a.n==4), "list a should have four elements" );
	check( (!strcmp(list_getc(&a,0),"1")), "first element should be '1'" );
	check( (!strcmp(list_getc(&a,1),"2")), "second element should be '2'" );
	check( (!strcmp(list_getc(&a,2),"3")), "third element should be '3'" );
	check( (!strcmp(list_getc(&a,3),"4")), "fourth element should be '4'" );
	list_empty( &a );

	newstr_strcpy( &s, "1 2 3 4 5" );
	list_tokenize( &a, &s, " \t", 0 );
	check( (a.n==5), "list a should have five elements" );
	check( (!strcmp(list_getc(&a,0),"1")), "first element should be '1'" );
	check( (!strcmp(list_getc(&a,1),"2")), "second element should be '2'" );
	check( (!strcmp(list_getc(&a,2),"3")), "third element should be '3'" );
	check( (!strcmp(list_getc(&a,3),"4")), "fourth element should be '4'" );
	check( (!strcmp(list_getc(&a,4),"5")), "fifth element should be '5'" );
	list_empty( &a );

	newstr_free( &s );
	list_free( &a );

	return 0;
}

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
test_new( void )
{
	char buf[1000];
	list *a;
	int i;

	a = list_new();
	check_len( a, 0 );
	check_entry( a, 0, NULL );

	for ( i=0; i<100; ++i ) {
		sprintf( buf, "Test%d", i );
		list_addc( a, buf );
	}
	check_len( a, 100 );
	for ( i=0; i<100; ++i ) {
		sprintf( buf, "Test%d", i );
		check_entry( a, i, buf );
	}
	check_entry( a, 101, NULL );

	list_delete( a );

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

/* int list_copy( list *to, list *from );
 */
int
test_copy( void )
{
	int i, status, ret = 0;
	char buf[1000];
	list a, copya;

	/* Build and test list to be copied */
	list_init( &a );
	for ( i=0; i<100; ++i ) {
		sprintf( buf, "ToBeCopied%d", i );
		list_addc( &a, buf );
	}
	check_len( &a, 100 );
	for ( i=0; i<100; ++i ) {
		sprintf( buf, "ToBeCopied%d", i );
		check_entry( &a, i, buf );
	}
	check_entry( &a, 101, NULL );

	/* Build and test list to be overwritten */
	list_init( &copya );
	for ( i=0; i<10; ++i ) {
		sprintf( buf, "ToBeOverwritten%d", i );
		list_addc( &copya, buf );
	}
	check_len( &copya, 10 );
	for ( i=0; i<10; ++i ) {
		sprintf( buf, "ToBeOverwritten%d", i );
		check_entry( &copya, i, buf );
	}
	check_entry( &copya, 10, NULL );

	/* Copy and check copy */
	status = list_copy( &copya, &a );
	if ( status!=LIST_OK ) {
		fprintf( stderr, "Memory error at %s() line %d\n", __FUNCTION__, __LINE__ );
		ret = 1;
		goto out;
	}
	check_len( &copya, 100 );
	for ( i=0; i<100; ++i ) {
		sprintf( buf, "ToBeCopied%d", i );
		check_entry( &copya, i, buf );
	}
	check_entry( &copya, 100, NULL );

out:
	list_free( &a );
	list_free( &copya );

	return ret;
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

int
main( int argc, char *argv[] )
{
	int failed = 0;

	failed += test_init();

	failed += test_add();
	failed += test_addc();
	failed += test_addvp();

	failed += test_add_all();
	failed += test_addc_all();
	failed += test_addvp_all();

	failed += test_add_unique();
	failed += test_addc_unique();
	failed += test_addvp_unique();

	failed += test_addsorted();
	failed += test_tokenize();

	failed += test_empty();
	failed += test_new();
	failed += test_dup();
	failed += test_copy();
	failed += test_append();
	failed += test_append_unique();
	failed += test_remove();
	failed += test_sort();

	failed += test_get();
	failed += test_getc();

	failed += test_set();
	failed += test_setc();

	failed += test_find();
	failed += test_findnocase();
	failed += test_match_entry();

	failed += test_fill();

	failed += test_trimend();

	failed += test_lists();

	if ( !failed ) {
		printf( "%s: PASSED\n", progname );
		return EXIT_SUCCESS;
	} else {
		printf( "%s: FAILED\n", progname );
		return EXIT_FAILURE;
	}

	return EXIT_SUCCESS;
}
