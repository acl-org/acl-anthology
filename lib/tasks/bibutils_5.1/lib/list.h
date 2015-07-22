/*
 * list.h
 *
 * version: 2013-08-29
 *
 * Copyright (c) Chris Putnam 2004-2013
 *
 * Source code released under the GPL version 2
 *
 */

#ifndef LISTS_H
#define LISTS_H

#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include "newstr.h"

#define LIST_CHR (0)
#define LIST_STR (1)

typedef struct list {
	int n, max;
	int sorted;
	newstr *str;
} list;


extern void    lists_init( list *a, ... );
extern void    lists_free( list *a, ... );
extern void    lists_empty( list *a, ... );


extern void    list_init( list *a );
extern void    list_free( list *a );
extern void    list_empty( list *a );

extern list *  list_new( void );
extern void    list_delete( list * );

extern list*   list_dup( list *a );
extern void    list_copy( list *to, list *from );

extern newstr * list_add( list *a, char *value );
extern newstr * list_addstr( list *a, newstr *value );
extern newstr * list_addvp( list *a, void *vp, unsigned char mode );

extern int      list_adds( list *a, ... );

extern newstr * list_add_unique( list *a, char *value );
extern newstr * list_addstr_unique( list *a, newstr *value );
extern newstr * list_addvp_unique( list *a, void *vp, unsigned char mode );

extern void    list_append( list *a, list *toadd );
extern void    list_append_unique( list *a, list *toadd );

extern void    list_remove( list *a, int n );

extern newstr* list_get( list *a, int n );
extern newstr* list_getstr( list *a, int n );
extern char*   list_getc( list *a, int n );
extern char*   list_getstr_char( list *a, int n );

extern int     list_set( list *a, int n, char *s );

extern void    list_sort( list *a );

extern int     list_find( list *a, char *searchstr );
extern int     list_findnocase( list *a, char *searchstr );
extern int     list_find_or_add( list *a, char *searchstr );
extern int     list_match_entry( list *a, int n, char *s );
extern void    list_trimend( list *a, int n );

extern int     list_fill( list *a, char *filename );
extern void    list_fillfp( list *a, FILE *fp );
extern void    list_tokenize( list *tokens, newstr *in, const char *delim, int merge_delim );
extern void    list_newstrtok( list *t, newstr *s, char *sep );


#endif
