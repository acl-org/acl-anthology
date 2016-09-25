/*
 * intlist.c
 *
 * Copyright (c) Chris Putnam 2007-2016
 *
 * Version 9/5/2013
 *
 * Source code released under the GPL version 2
 *
 * Implements a simple managed array of ints
 *
 */
#include "intlist.h"

static int
intlist_alloc( intlist *il )
{
	int alloc = 20, i;
	il->data = ( int * ) malloc( sizeof( int ) * alloc );
	if ( !(il->data) ) return 0;
	for ( i=0; i<alloc; ++i )
		il->data[i] = 0;
	il->max = alloc;
	il->n = 0;
	return 1;
}

static int
intlist_realloc( intlist *il )
{
	int *more;
	int alloc = il->max * 2, i;
	more = ( int * ) realloc( il->data, sizeof( int ) * alloc );
	if ( !more ) return 0;
	il->data = more;
	for ( i=il->max; i<alloc; ++i )
		il->data[i] = 0;
	il->max = alloc;
	return 1;
}

/* intlist_add()
 *
 * Returns position of newly added value in range [0,n), -1 on error
 */
int
intlist_add( intlist *il, int value )
{
	if ( il->max==0 ) {
		if ( !intlist_alloc( il ) ) return -1;
	} else if ( il->n >= il->max ) {
		if ( !intlist_realloc( il ) ) return -1;
	}
	il->data[ il->n ] = value;
	il->n++;
	return il->n - 1;
}

/* intlist_add_unique()
 *
 * Returns position of newly added (or previously added) value
 * Returns -1 on (memory) error
 */
int
intlist_add_unique( intlist *il, int value )
{
	int n;
	n = intlist_find( il, value );
	if ( n==-1 )
		n = intlist_add( il, value );
	return n;
}
int
intlist_find_or_add( intlist *il, int value )
{
	return intlist_add_unique( il, value );
}

/* intlist_find()
 *
 * Returns position of value in range [0,n), or -1 if
 * value cannot be found
 */
int
intlist_find( intlist *il, int value )
{
	int i;
	for ( i=0; i<il->n; ++i )
		if ( il->data[i]==value ) return i;
	return -1;
}

static void
intlist_remove_pos_core( intlist *il, int pos )
{
	int i;
	for ( i=pos; i<il->n-1; ++i )
		il->data[i] = il->data[i+1];
	il->n -= 1;
}

/* intlist_remove_pos()
 *
 * Returns 1 on success, 0 on failure.
 */
int
intlist_remove_pos( intlist *il, int pos )
{
	if ( pos < 0 || pos >= il->n ) return 0;
	intlist_remove_pos_core( il, pos );
	return 1;
}

/* intlist_remove()
 *
 * Removes first instance of value from the intlist.
 * Returns 1 on success, 0 on error.
 */
int
intlist_remove( intlist *il, int value )
{
	int pos = intlist_find( il, value );
	if ( pos==-1 ) return 0;
	intlist_remove_pos_core( il, pos );
	return 1;
}

/* don't actually free space, just reset counter */
void
intlist_empty( intlist *il )
{
	il->n = 0;
}

void
intlist_free( intlist *il )
{
	if ( il->data ) free( il->data );
	intlist_init( il );
}

void
intlist_delete( intlist *il )
{
	intlist_free( il );
	free( il );
}

void
intlist_init( intlist *il  )
{
	il->data = NULL;
	il->max = 0;
	il->n = 0;
}

/* intlist_init_range()
 *
 * Initializes intlist to values from [low,high) with step step.
 * Returns -1 on failure, number of elements on success.
 */
int
intlist_init_range( intlist *il, int low, int high, int step )
{
	int i, n;
	intlist_init( il );
	for ( i=low; i<high; i+= step ) {
		n = intlist_add( il, i );
		if ( n==-1 ) return -1;
	}
	return il->n;
}

/* intlist_new()
 *
 * Allocates an empty intlist.
 * Returns pointer to intlist on success, NULL on memory error.
 */
intlist *
intlist_new( void )
{
	intlist *il = ( intlist * ) malloc( sizeof( intlist ) );
	if ( il ) intlist_init( il );
	return il;
}

/* intlist_new_range()
 *
 * Allocates a intlist initialized to values from [low,high) with step step.
 * Returns pointer to intlist on success, NULL on memory error;
 */
intlist *
intlist_new_range( int low, int high, int step )
{
	intlist *il;
	int n;
	il = ( intlist * ) malloc( sizeof( intlist ) );
	if ( il ) {
		n = intlist_init_range( il, low, high, step );
		if ( n==-1 ) {
			intlist_free( il );
			free( il );
			il = NULL;
		}
	}
	return il;
}

static int
intcomp( const void *v1, const void *v2 )
{
	int *i1 = ( int * ) v1;
	int *i2 = ( int * ) v2;
	if ( *i1 < *i2 ) return -1;
	else if ( *i1 > *i2 ) return 1;
	return 0;
}

void
intlist_sort( intlist *il )
{
	qsort( il->data, il->n, sizeof( int ), intcomp );
}

/* Returns random integer in the range [floor,ceil) */
static int
randomint( int floor, int ceil )
{
	int len = ceil - floor;
	return floor + rand() % len;
}

static void
swap( int *a, int *b )
{
	int tmp;
	tmp = *a;
	*a = *b;
	*b = tmp;
}

void
intlist_randomize( intlist *il )
{
	int i, j;
	if ( il->n < 2 ) return;
	for ( i=0; i<il->n; ++i ) {
		j = randomint( i, il->n );
		if ( i==j ) continue;
		swap( &(il->data[i]), &(il->data[j]) );
	}
}

/* Returns 1 on success, 0 on error */
int
intlist_copy( intlist *to, intlist *from )
{
	int i;
	intlist_free( to );
	to->data = ( int* ) malloc( sizeof( int ) * from->n );
	if ( !to->data ) return 0;
	to->n = to->max = from->n;
	for ( i=0; i<from->n; ++i ) 
		to->data[i] = from->data[i];
	return 1;
}

/* Returns pointer on success, NULL on error */
intlist *
intlist_dup( intlist *il )
{
	intlist *l;
	int n;

	l = intlist_new();
	if ( l ) {
		n = intlist_copy( l, il );
		if ( !n ) {
			intlist_delete( l );
			l = NULL;
		}
	}

	return l;
}

int
intlist_append( intlist *to, intlist *from )
{
	int i, n, nsave = to->n;
	for ( i=0; i<from->n; ++i ) {
		n = intlist_add( to, from->data[i] );
		if ( n==-1 ) {
			to->n = nsave;
			return -1;
		}
	}
	return to->n;
}

int
intlist_append_unique( intlist *to, intlist *from )
{
	int i, n, nsave = to->n;
	for ( i=0; i<from->n; ++i ) {
		if ( intlist_find( to, from->data[i] )!=-1 ) continue;
		n = intlist_add( to, from->data[i] );
		if ( n==-1 ) {
			to->n = nsave;
			return -1;
		}
	}
	return to->n;
}

int
intlist_get( intlist *il, int pos )
{
	if ( pos<0 || pos>=il->n ) return 0;
	else return il->data[pos];
}

/* intlist_set()
 *
 *   Returns 1 on success, 0 on failure
 */
int
intlist_set( intlist *il, int pos, int value )
{
	if ( pos<0 || pos>=il->n ) return 0;
	il->data[pos] = value;
	return 1;
}

float
intlist_median( intlist *il )
{
	intlist *tmp;
	float median;
	int m1, m2;

	if ( il->n==0 ) return 0.0;

	tmp = intlist_dup( il );
	if ( !tmp ) return 0.0;

	intlist_sort( tmp );

	if ( tmp->n % 2 == 1 ) {
		median = intlist_get( tmp, tmp->n / 2 );
	} else {
		m1 = intlist_get( tmp, tmp->n / 2 );
		m2 = intlist_get( tmp, tmp->n / 2 + 1);
		median = ( m1 + m2 ) / 2.0;
	}

	intlist_delete( tmp );

	return median;
}

float
intlist_mean( intlist *il )
{
	float sum = 0.0;
	int i;

	if ( il->n==0 ) return 0.0;

	for ( i=0; i<il->n; ++i )
		sum += intlist_get( il, i );

	return sum / il->n;
}
