/*
 * vplist.c
 *
 * Version: 11/20/2014
 *
 * Copyright (c) Chris Putnam 2011-2016
 *
 * Source code released under the GPL version 2
 *
 * Implements a simple managed array of pointers to void
 *
 */
#include <stdlib.h>
#include "vplist.h"

/* Do not use asserts in VPLIST_NOASSERT defined */
#ifdef VPLIST_NOASSERT
#define NDEBUG
#endif
#include <assert.h>

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
		if ( !to->data ) return VPLIST_ERR;
		to->max = from->n;
	}
	for ( i=0; i<from->n; ++i )
		to->data[i] = from->data[i];
	to->n = from->n;
	return VPLIST_OK;
}

int
vplist_append( vplist *to, vplist *from )
{
	int i, status;
	assert( to );
	assert( from );
	for ( i=0; i<from->n; ++i ) {
		status = vplist_add( to, from->data[i] );
		if ( status!=VPLIST_OK ) return status;
	}
	return VPLIST_OK;
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
	if ( !vpl->data ) return VPLIST_ERR;
	vpl->max = alloc;
	vpl->n = 0;
	return VPLIST_OK;
}

static int
vplist_realloc( vplist *vpl )
{
	void **more;
	int alloc = vpl->max * 2;
	more = ( void ** ) realloc( vpl->data, sizeof( void * ) * alloc );
	if ( !more ) return VPLIST_ERR;
	vpl->data = more;
	vpl->max = alloc;
	return VPLIST_OK;
}

int
vplist_add( vplist *vpl, void *v )
{
	int status = VPLIST_OK;

	assert( vpl );

	/* ensure sufficient space */
	if ( vpl->max==0 ) status = vplist_alloc( vpl );
	else if ( vpl->n >= vpl->max ) status = vplist_realloc( vpl );

	if ( status==VPLIST_OK ) {
		vpl->data[vpl->n] = v;
		vpl->n++;
	}

	return status;
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
	assert( vplist_validindex( vpl, n ) );

	vpl->data[ n ] = v;
}

void
vplist_swap( vplist *vpl, int n1, int n2 )
{
	void *v1, *v2;

	assert( vpl );
	assert( vplist_validindex( vpl, n1 ) );
	assert( vplist_validindex( vpl, n2 ) );

	v1 = vpl->data[n1];
	v2 = vpl->data[n2];

	vpl->data[n1] = v2;
	vpl->data[n2] = v1;
}

void
vplist_remove( vplist *vpl, int n )
{
	int i;

	assert( vpl );
	assert( vplist_validindex( vpl, n ) );

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
	void *v;
	int i;
	for ( i=0; i<vpl->n; ++i ) {
		v = vplist_get( vpl, i );
		if ( v ) (*vpf)( v );
	}
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
vplist_delete( vplist **vpl )
{
	assert( *vpl );
	vplist_free( *vpl );
	free( *vpl );
	*vpl = NULL;
}

void
vplist_deletefn( vplist **vpl, vplist_ptrfree vpf )
{
	assert( *vpl );
	vplist_freemembers( *vpl, vpf );
	vplist_delete( vpl );
}
