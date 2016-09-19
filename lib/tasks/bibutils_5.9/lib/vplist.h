/*
 * vplist.h
 *
 * Version: 11/20/2014
 *
 * Copyright (c) Chris Putnam 2011-2016
 *
 * Source code released under the GPL version 2
 *
 */

#ifndef VPLIST_H
#define VPLIST_H

#define VPLIST_ERR (1)
#define VPLIST_OK  (0)

/* vplist = void pointer list (generic container struct)
 */
typedef struct vplist {
	int n, max;
	void **data;
} vplist;

typedef void (*vplist_ptrfree)(void*);

extern void     vplist_init( vplist *vpl );
extern vplist * vplist_new( void );
extern int      vplist_add( vplist *vpl, void *v );
extern int      vplist_copy( vplist *to, vplist *from );
extern int      vplist_append( vplist *to, vplist *from );
extern void *   vplist_get( vplist *vpl, int n );
extern void     vplist_set( vplist *vpl, int n, void *v );
extern void     vplist_swap( vplist *vpl, int n1, int n2 );
extern void     vplist_remove( vplist *vpl, int n );
extern void     vplist_removevp( vplist *vpl, void *v );
extern int      vplist_find( vplist *vpl, void *v );
/*
 * vplist_empty does not free space
 *
 * if members require their own free calls, then call vplist_emptyfn()
 *
 * void
 * member_free( void *v )
 * {
 *     member *m = ( member * ) v;
 *     member_free( m );
 *     free( m );
 * }
 * vplist_emptyfn( &vpl, member_free );
 *
 * if members are simply allocated with malloc(), then use free()
 *
 * vplist_emptyfn( &vpl, free );
 */
extern void   vplist_empty( vplist *vpl );
extern void   vplist_emptyfn( vplist *vpl, vplist_ptrfree fn );
/*
 * vplist_free frees the space for the data array of void * elements.
 *
 * if members require their own free calls, then call vplist_freefn()
 */
extern void vplist_free( vplist *vpl );
extern void vplist_freefn( vplist *vpl, vplist_ptrfree fn );
/*
 * vplist_delete does vplist_free and deallocates the struct
 * vplist * and replaces with NULL.
 */
extern void vplist_delete( vplist **vpl );
extern void vplist_deletefn( vplist **vpl, vplist_ptrfree fn );

#endif
