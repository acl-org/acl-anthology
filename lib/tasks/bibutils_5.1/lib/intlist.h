/*
 * intlist.h
 *
 * Copyright (c) Chris Putnam 2007-2013
 *
 * Source code released under the GPL version 2
 *
 */

#ifndef INTLIST_H
#define INTLIST_H

#include <stdio.h>
#include <stdlib.h>

typedef struct intlist {
	int n, max;
	int *data;
} intlist;

extern void      intlist_init( intlist *il );
extern int       intlist_init_range( intlist *il, int low, int high, int step );
extern intlist * intlist_new( void );
extern intlist * intlist_new_range( int low, int high, int step );
extern void      intlist_delete( intlist *il );
extern void      intlist_sort( intlist *il );
extern void      intlist_randomize( intlist *il );
extern int       intlist_add( intlist *il, int value );
extern int       intlist_add_unique( intlist *il, int value );
extern int       intlist_find( intlist *il, int searchvalue );
extern int       intlist_find_or_add( intlist *il, int searchvalue );
extern void      intlist_empty( intlist *il );
extern void      intlist_free( intlist *il );
extern void      intlist_copy( intlist *to, intlist *from );
extern int       intlist_get( intlist *il, int pos );
extern void      intlist_set( intlist *il, int pos, int value );
extern void      intlist_remove( intlist *il, int searchvalue );
extern void      intlist_remove_pos( intlist *il, int pos );
extern int       intlist_append( intlist *to, intlist *from );
extern int       intlist_append_unique( intlist *to, intlist *from );

#endif
