/*
 * vplist.c
 *
 * Version: 4/08/2013
 *
 * Copyright (c) Chris Putnam 2011-2013
 *
 * Source code released under the GPL version 2
 *
 * Implements a simple managed array of pointers to void
 *
 */
#include <stdlib.h>
#include <assert.h>
#include "vplist.h"

void
vplist_init( vplist *vpl )
{
	assert( vpl );
	vpl->data = NULL;
	vpl->n = vpl->max = 0;
}

vplist *
vplist_new( void )
{
	vplist *vpl;
	vpl = ( vplist * ) malloc( sizeof( vplist ) );
	if ( vpl ) vplist_init( vpl );
	return vpl;
}

int
vplist_find( vplist *vpl, void *v )
{
	int i;
	assert( vpl );
	for ( i=0; i<vpl->n; ++i )
		if ( vpl->data[i]==v ) return i;
	return -1;
}

int
vplist_copy( vplist *to, vplist *from )
{
	int i;
	assert( to );
	assert( from );
	if ( from->n > to->max ) {
		if ( to->max ) free( to->data );
		to->data = ( void ** ) malloc( sizeof( void * ) * from->n );
		if ( !to->data ) return 0;
		to->max = from->n;
	}
	for ( i=0; i<from->n; ++i )
		to->data[i] = from->data[i];
	to->n = from->n;
	return 1;
}

int
vplist_append( vplist *to, vplist *from )
{
	int i, ok;
	assert( to );
	assert( from );
	for ( i=0; i<from->n; ++i ) {
		ok = vplist_add( to, from->data[i] );
		if ( !ok ) return 0;
	}
	return 1;
}

static int
vplist_validindex( vplist *vpl, int n )
{
	if ( n < 0 || n >= vpl->n ) return 0;
	return 1;
}

static int
vplist_alloc( vplist *vpl )
{
	int alloc = 20;
	vpl->data = ( void ** ) malloc( sizeof( void * ) * alloc );
	if ( !vpl->data ) return 0;
	vpl->max = alloc;
	vpl->n = 0;
	return 1;
}

static int
vplist_realloc( vplist *vpl )
{
	void **more;
	int alloc = vpl->max * 2;
	more = ( void ** ) realloc( vpl->data, sizeof( void * ) * alloc );
	if ( !more ) return 0;
	vpl->data = more;
	vpl->max = alloc;
	return 1;
}

int
vplist_add( vplist *vpl, void *v )
{
	int ok = 1;

	assert( vpl );

	/* ensure sufficient space */
	if ( vpl->max==0 ) ok = vplist_alloc( vpl );
	else if ( vpl->n >= vpl->max ) ok = vplist_realloc( vpl );

	if ( ok ) {
		vpl->data[vpl->n] = v;
		vpl->n++;
	}

	return ok;
}

void *
vplist_get( vplist *vpl, int n )
{
	assert( vpl );
	if ( !vplist_validindex( vpl, n ) ) return NULL;
	return vpl->data[ n ];
}

void
vplist_set( vplist *vpl, int n, void *v )
{
	assert( vpl );
	if ( !vplist_validindex( vpl, n ) ) return;
	vpl->data[ n ] = v;
}

void
vplist_remove( vplist *vpl, int n )
{
	int i;
	assert( vpl );
	if ( !vplist_validindex( vpl, n ) ) return;
	for ( i=n+1; i<vpl->n; ++i )
		vpl->data[ i-1 ] = vpl->data[ i ];
	vpl->n -= 1;
}

void
vplist_removevp( vplist *vpl, void *v )
{
	int n;
	assert( vpl );
	do {
		n = vplist_find( vpl, v );
		if ( n!=-1 ) vplist_remove( vpl, n );
	} while ( n!=-1 );
}

static void
vplist_freemembers( vplist *vpl, vplist_ptrfree vpf )
{
	int i;
	for ( i=0; i<vpl->n; ++i )
		(*vpf)( vplist_get( vpl, i ) );
}

void
vplist_empty( vplist *vpl )
{
	assert( vpl );
	vpl->n = 0;
}

void
vplist_emptyfn( vplist *vpl, vplist_ptrfree vpf )
{
	assert( vpl );
	vplist_freemembers( vpl, vpf );
	vplist_empty( vpl );
}

void
vplist_free( vplist *vpl )
{
	assert( vpl );
	if ( vpl->data ) free( vpl->data );
	vplist_init( vpl );
}

void
vplist_freefn( vplist *vpl, vplist_ptrfree vpf )
{
	assert( vpl );
	vplist_freemembers( vpl, vpf );
	vplist_free( vpl );
}

void
vplist_destroy( vplist **vpl )
{
	assert( *vpl );
	vplist_free( *vpl );
	free( *vpl );
	*vpl = NULL;
}

void
vplist_destroyfn( vplist **vpl, vplist_ptrfree vpf )
{
	assert( *vpl );
	vplist_freemembers( *vpl, vpf );
	vplist_destroy( vpl );
}
