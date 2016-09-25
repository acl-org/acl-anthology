/*
 * list.h
 *
 * version: 2014-11-15
 *
 * Copyright (c) Chris Putnam 2004-2016
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

#define LIST_ERR (0)
#define LIST_ERR_CANNOTOPEN (-1)
#define LIST_OK  (1)

#define LIST_CHR (0)
#define LIST_STR (1)

typedef struct list {
	int n, max;
	newstr *str;
	unsigned char sorted;
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
extern int     list_copy( list *to, list *from );

extern newstr * list_addvp( list *a, unsigned char mode, void *vp );
extern newstr * list_addc( list *a, const char *value );
extern newstr * list_add( list *a, newstr *value );

extern int      list_addvp_all( list *a, unsigned char mode, ... );
extern int      list_addc_all( list *a, ... );
extern int      list_add_all( list *a, ... );

extern newstr * list_addvp_unique( list *a, unsigned char mode, void *vp );
extern newstr * list_addc_unique( list *a, const char *value );
extern newstr * list_add_unique( list *a, newstr *value );

extern int     list_append( list *a, list *toadd );
extern int     list_append_unique( list *a, list *toadd );

extern int     list_remove( list *a, int n );

extern newstr* list_get( list *a, int n );
extern char*   list_getc( list *a, int n );

extern newstr* list_set( list *a, int n, newstr *s );
extern newstr* list_setc( list *a, int n, const char *s );

extern void    list_sort( list *a );

extern void    list_swap( list *a, int n1, int n2 );

extern int     list_find( list *a, const char *searchstr );
extern int     list_findnocase( list *a, const char *searchstr );
extern int     list_match_entry( list *a, int n, char *s );
extern void    list_trimend( list *a, int n );

extern int     list_fill( list *a, const char *filename, unsigned char skip_blank_lines );
extern int     list_fillfp( list *a, FILE *fp, unsigned char skip_blank_lines );
extern int     list_tokenize( list *tokens, newstr *in, const char *delim, int merge_delim );
extern int     list_tokenizec( list *tokens, char *p, const char *delim, int merge_delim );

#endif
