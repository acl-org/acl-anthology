/*
 * list.c
 *
 * version: 2013-08-29
 *
 * Copyright (c) Chris Putnam 2004-2013
 *
 * Source code released under the GPL version 2
 *
 * Implements a simple managed array of newstrs.
 *
 */
#include "list.h"

void
list_init( list *a  )
{
	a->str = NULL;
	a->max = 0;
	a->n = 0;
	a->sorted = 0;
}

void
list_empty( list *a )
{
	int i;
	for ( i=0; i<a->max; ++i )
		newstr_empty( &(a->str[i]) );
	a->n = 0;
	a->sorted = 1;
}

void
list_free( list *a )
{
	int i;
	for ( i=0; i<a->max; ++i )
		newstr_free( &(a->str[i]) );
	free( a->str );
	list_init( a );
}

list *
list_new( void )
{
	list *a = ( list * ) malloc( sizeof ( list ) );
	if ( a ) list_init( a );
	return a;
}

void
list_delete( list *a )
{
	list_free( a );
	free( a );
}

/*
 * returns 1 if n is valid string in list
 */
static inline int
list_valid_num( list *a, int n )
{
	if ( n < 0 || n >= a->n ) return 0;
	return 1;
}

int
list_set( list *a, int n, char *s )
{
	if ( !list_valid_num( a, n ) ) return 0;
	newstr_strcpy( &(a->str[n]), s );
	return 1;
}

/*
 * return pointer to newstr 'n', list_getstr() is deprecated
 */
newstr *
list_get( list *a, int n )
{
	if ( !list_valid_num( a, n ) ) return NULL;
	else return &(a->str[n]);
}
newstr *
list_getstr( list *a, int n )
{
	if ( !list_valid_num( a, n ) ) return NULL;
	else return &(a->str[n]);
}

/*
 * return pointer to C string 'n', list_getstr_char() is deprecated
 *
 * Ensure that a pointer is returned even if the newstr doesn't
 * point to data. Thus we can convert loops like:
 *
 * for ( i=0; i<a->n; ++i ) {
 *      p = list_getc( a, i );
 *      if ( p==NULL ) continue; // empty string
 *      ...
 * }
 *
 * to
 *
 * i = 0;
 * while ( ( p = list_getc( a, i ) ) ) {
 *      ...
 *      i++;
 * }
 *
 */
char *
list_getc( list *a, int n )
{
	static char empty[] = "";
	char *p;
	if ( !list_valid_num( a, n ) ) return NULL;
	p = a->str[n].data;
	if ( p ) return p;
	else return empty;
}
char *
list_getstr_char( list *a, int n )
{
	return list_getc( a, n );
}

static int
list_alloc( list *a )
{
	int i, alloc = 20;
	a->str = ( newstr* ) malloc( sizeof( newstr ) * alloc );
	if ( !(a->str) ) return 0;
	a->max = alloc;
	a->n = 0;
	for ( i=0; i<alloc; ++i )
		newstr_init( &(a->str[i]) );
	return 1;
}

static int
list_realloc( list *a )
{
	newstr *more;
	int i, alloc = a->max * 2;
	more = ( newstr* ) realloc( a->str, sizeof( newstr ) * alloc );
	if ( !more ) return 0;
	a->str = more;
	for ( i=a->max; i<alloc; ++i )
		newstr_init( &(a->str[i]) );
	a->max = alloc;
	return 1;
}

static int
list_ensure_space( list *a )
{
	int ok = 1;
	if ( a->max==0 ) ok = list_alloc( a );
	else if ( a->n >= a->max ) ok = list_realloc( a );
	return ok;
}

newstr *
list_addvp( list *a, void *vp, unsigned char mode )
{
	newstr *s = NULL;
	int ok;
	ok = list_ensure_space( a );
	if ( ok ) {
		s = &( a->str[a->n] );
		if ( mode==LIST_CHR )
			newstr_strcpy( s, (char*) vp );
		else if ( mode==LIST_STR )
			newstr_newstrcpy( s, (newstr*) vp );
		else
			return NULL;
		a->sorted = 0;
		a->n++;
	}
	return s;
}
newstr *
list_add( list *a, char *s )
{
	return list_addvp( a, (void*)s, LIST_CHR );
}
newstr *
list_addstr( list *a, newstr *s )
{
	return list_addvp( a, (void*)s, LIST_STR );
}

newstr *
list_addvp_unique( list *a, void *vp, unsigned char mode )
{
	newstr *s;
	int n;
	if ( mode==LIST_CHR )
		n = list_find( a, (char*) vp );
	else if ( mode==LIST_STR )
		n = list_find( a, ( (newstr*) vp )->data );
	else
		return NULL;
	if ( n!=-1 )
		s = &( a->str[n] );
	else
		s = list_addvp( a, vp, mode );
	return s;
}
newstr *
list_add_unique( list *a, char *s )
{
	return list_addvp_unique( a, (void*) s, LIST_CHR );
}
newstr *
list_addstr_unique( list *a, newstr *s )
{
	return list_addvp_unique( a, (void*) s, LIST_STR );
}

int
list_adds( list *a, ... )
{
	int ret = 1;
	va_list ap;
	newstr *s;
	char *v;
	va_start( ap, a );
	do {
		v = va_arg( ap, char * );
		if ( v ) {
			s = list_addvp( a, (void*) v, LIST_CHR );
			if ( s==NULL ) { ret = 0; goto out; }
		}
	} while ( v );
out:
	va_end( ap );
	return ret;
}

void
list_append( list *a, list *toadd )
{
	int i;
	for ( i=0; i<toadd->n; ++i ) {
		list_addstr( a, &(toadd->str[i]) );
	}
}

void
list_append_unique( list *a, list *toadd )
{
	int i;
	for ( i=0; i<toadd->n; ++i ) {
		list_addstr_unique( a, &(toadd->str[i]) );
	}
}

void
list_remove( list *a, int n )
{
	int i;
	if ( !list_valid_num( a, n ) ) return;
	for ( i=n+1; i<a->n; ++i )
		newstr_newstrcpy( &(a->str[i-1]), &(a->str[i]) );
	a->n--;
}

static int
list_comp( const void *v1, const void *v2 )
{
	newstr *s1 = ( newstr *) v1;
	newstr *s2 = ( newstr *) v2;
	if ( !s1->len && !s2->len ) return 0;
	else if ( !s1->len ) return -1;
	else if ( !s2->len ) return 1;
	else return strcmp( s1->data, s2->data );
}

void
list_sort( list *a )
{
	qsort( a->str, a->n, sizeof( newstr ), list_comp );
	a->sorted = 1;
}

static int
list_find_sorted( list *a, char *searchstr )
{
	int min, max, mid, comp;
	newstr s, *cs;
	if ( a->n==0 ) return -1;
	newstr_init( &s );
	newstr_strcpy( &s, searchstr );
	min = 0;
	max = a->n - 1;
	while ( min <= max ) {
		mid = ( min + max ) / 2;
		cs = list_get( a, mid );
		comp = list_comp( (void*)cs, (void*) (&s) );
		if ( comp==0 ) return mid;
		else if ( comp > 0 ) max = mid - 1;
		else if ( comp < 0 ) min = mid + 1;
	}
	newstr_free( &s );
	return -1;
}

static int
list_find_simple( list *a, char *searchstr, int nocase )
{
	int i;
	if ( nocase ) {
		for ( i=0; i<a->n; ++i )
			if ( !strcasecmp(a->str[i].data,searchstr) ) 
				return i;
	} else {
		for ( i=0; i<a->n; ++i )
			if ( !strcmp(a->str[i].data,searchstr) ) 
				return i;
	}
	return -1;
}

int
list_find( list *a, char *searchstr )
{
	if ( a->sorted )
		return list_find_sorted( a, searchstr );
	else
		return list_find_simple( a, searchstr, 0 );
}

int
list_findnocase( list *a, char *searchstr )
{
	return list_find_simple( a, searchstr, 1 );
}

/* Return the index of searched-for string.
 * If cannot find string, add to list and then
 * return the index
 */
int
list_find_or_add( list *a, char *searchstr )
{
	int n = list_find( a, searchstr );
	if ( n==-1 ) {
		list_add( a, searchstr );
		n = a->n - 1;
	}
	return n;
}

void
list_fillfp( list *a, FILE *fp )
{
	newstr line;
	char *p, buf[512]="";
	int  bufpos = 0;

	list_init( a );
	newstr_init( &line );
	while ( newstr_fget( fp, buf, sizeof(buf), &bufpos, &line ) ) {
		p = &(line.data[0]);
		if ( *p=='\0' ) continue;
		if ( !list_add( a, line.data ) ) return;
	}
	newstr_free( &line );
}

int
list_fill( list *a, char *filename )
{
	FILE *fp = fopen( filename, "r" );
	if ( !fp ) return 0;
	list_fillfp( a, fp );
	fclose( fp );
	return 1;
}

void
list_copy( list *to, list *from )
{
	int i;
	list_free( to );
	to->str = ( newstr * ) malloc( sizeof( newstr ) * from->n );
	if ( !to->str ) return;
	to->n = to->max = from->n;
	for ( i=0; i<from->n; ++i ) {
		newstr_init( &(to->str[i]) );
		newstr_strcpy( &(to->str[i]), from->str[i].data );
	}
}

list *
list_dup( list *aold )
{
	list *anew;
	int i;
	anew = ( list* ) malloc( sizeof( list ) );
	if ( !anew ) goto err0;
	anew->str = ( newstr* ) malloc( sizeof( newstr ) * aold->n );
	if ( !anew->str ) goto err1;
	anew->n = anew->max = aold->n;
	for ( i=0; i<aold->n; ++i ) {
		newstr_init( &(anew->str[i]) );
		newstr_strcpy( &(anew->str[i]), aold->str[i].data );
	}
	return anew;
err1:
	free( anew );
err0:
	return NULL;
}

int
list_match_entry( list *a, int n, char *s )
{
	if ( n < 0 || n >= a->n ) return 0;
	if ( strcmp( a->str[n].data, s ) ) return 0;
	return 1;
}

void
list_trimend( list *a, int n )
{
	int i;
	if ( a->n - n < 1 ) {
		list_empty( a );
	} else {
		for ( i=a->n -n; i<a->n; ++i ) {
			newstr_empty( &(a->str[i]) );
		}
		a->n -= n;
	}
}

void
list_tokenize( list *tokens, newstr *in, const char *delim, int merge_delim )
{
	newstr s;
	char *p;
	list_empty( tokens );
	p = in->data;
	newstr_init( &s );
	while ( p && *p ) {
		while ( *p && !strchr( delim, *p ) ) newstr_addchar( &s, *p++ );
		if ( s.len ) list_add( tokens, s.data );
		else if ( !merge_delim ) list_add( tokens, "" );
		newstr_empty( &s );
		if ( *p && strchr( delim, *p ) ) p++;
	}
	newstr_free( &s );
}

void
list_newstrtok( list *t, newstr *s, char *sep )
{
	newstr tmp;
	char *p;
	list_empty( t );
	if ( !s->len ) return;
	newstr_init( &tmp );
	p = s->data;
	while ( *p ) {
		if ( strchr( sep, *p ) ) {
			if ( tmp.len ) {
				list_add( t, tmp.data );
				newstr_empty( &tmp );
			}
		} else newstr_addchar( &tmp, *p );
		p++;
	}
	if ( tmp.len ) list_add( t, tmp.data );
	newstr_free( &tmp );
}

void
lists_init( list *a, ... )
{
	list *a2;
	va_list ap;
	list_init( a );
	va_start( ap, a );
	do {
		a2 = va_arg( ap, list * );
		if ( a2 ) list_init( a2 );
	} while ( a2 );
	va_end( ap );
}

void
lists_free( list *a, ... )
{
	list *a2;
	va_list ap;
	list_free( a );
	va_start( ap, a );
	do {
		a2 = va_arg( ap, list * );
		if ( a2 ) list_free( a2 );
	} while ( a2 );
	va_end( ap );
}

void
lists_empty( list *a, ... )
{
	list *a2;
	va_list ap;
	list_empty( a );
	va_start( ap, a );
	do {
		a2 = va_arg( ap, list * );
		if ( a2 ) list_empty( a2 );
	} while ( a2 );
	va_end( ap );
}

