/*
 * list.c
 *
 * version: 2014-11-15
 *
 * Copyright (c) Chris Putnam 2004-2016
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
	a->sorted = 1;
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

static int
list_comp_step( list *a, int n1, int n2 )
{
	return list_comp( (const void*) &(a->str[n1]), (const void*) &(a->str[n2]) );
}

static newstr *
list_set_cleanup( list *a, int n )
{
	if ( newstr_memerr( &(a->str[n]) ) ) return NULL;
	if ( a->sorted ) {
		if ( n>0 && list_comp_step( a, n-1, n )>0 )
			a->sorted = 0;
	}
	if ( a->sorted ) {
		if ( n<a->n-1 && list_comp_step( a, n, n+1 )>0 )
			a->sorted = 0;
	}
	return &(a->str[n]);
}

newstr *
list_set( list *a, int n, newstr *s )
{
	if ( !list_valid_num( a, n ) ) return NULL;
	newstr_newstrcpy( &(a->str[n]), s );
	return list_set_cleanup( a, n );
}

newstr *
list_setc( list *a, int n, const char *s )
{
	if ( !list_valid_num( a, n ) ) return NULL;
	newstr_strcpy( &(a->str[n]), s );
	return list_set_cleanup( a, n );
}

/*
 * return pointer to newstr 'n'
 */
newstr *
list_get( list *a, int n )
{
	if ( !list_valid_num( a, n ) ) return NULL;
	else return &(a->str[n]);
}

/*
 * return pointer to C string 'n'
 *
 * So long as the index is a valid number ensure
 * that a pointer is returned even if the newstr doesn't
 * point to data. Only return NULL if the index
 * is invalid. Thus we can convert loops like:
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

static int
list_alloc( list *a )
{
	int i, alloc = 20;
	a->str = ( newstr* ) malloc( sizeof( newstr ) * alloc );
	if ( !(a->str) ) return LIST_ERR;
	a->max = alloc;
	a->n = 0;
	for ( i=0; i<alloc; ++i )
		newstr_init( &(a->str[i]) );
	return LIST_OK;
}

static int
list_realloc( list *a )
{
	newstr *more;
	int i, alloc = a->max * 2;
	more = ( newstr* ) realloc( a->str, sizeof( newstr ) * alloc );
	if ( !more ) return LIST_ERR;
	a->str = more;
	for ( i=a->max; i<alloc; ++i )
		newstr_init( &(a->str[i]) );
	a->max = alloc;
	return LIST_OK;
}


static int
list_ensure_space( list *a )
{
	int status = LIST_OK;
	if ( a->max==0 )
		status = list_alloc( a );
	else if ( a->n >= a->max )
		status = list_realloc( a );
	return status;
}

newstr *
list_addvp( list *a, unsigned char mode, void *vp )
{
	newstr *s = NULL;
	int status;
	status = list_ensure_space( a );
	if ( status==LIST_OK ) {
		s = &( a->str[a->n] );
		if ( mode==LIST_CHR )
			newstr_strcpy( s, (const char*) vp );
		else if ( mode==LIST_STR )
			newstr_newstrcpy( s, (newstr*) vp );
		else
			return NULL;
		if ( newstr_memerr( s ) ) return NULL;
		a->n++;
		if ( a->sorted && a->n > 1 ) {
			if ( list_comp_step( a, a->n-2, a->n-1 ) > 0 )
				a->sorted = 0;
		}
	}
	return s;
}
newstr *
list_addc( list *a, const char *s )
{
	return list_addvp( a, LIST_CHR, (void*)s );
}
newstr *
list_add( list *a, newstr *s )
{
	return list_addvp( a, LIST_STR, (void*)s );
}

newstr *
list_addvp_unique( list *a, unsigned char mode, void *vp )
{
	newstr *s;
	int n;
	if ( mode==LIST_CHR )
		n = list_find( a, (const char*) vp );
	else if ( mode==LIST_STR )
		n = list_find( a, ( (newstr*) vp )->data );
	else
		return NULL;
	if ( n!=-1 )
		s = &( a->str[n] );
	else {
		s = list_addvp( a, mode, vp );
	}
	return s;
}
newstr *
list_addc_unique( list *a, const char *s )
{
	return list_addvp_unique( a, LIST_CHR, (void*)s );
}
newstr *
list_add_unique( list *a, newstr *s )
{
	return list_addvp_unique( a, LIST_STR, (void*)s );
}

int
list_addvp_all( list *a, unsigned char mode, ... )
{
	int ret = LIST_OK;
	va_list ap;
	newstr *s;
	void *v;
	va_start( ap, mode );
	do {
		if ( mode==LIST_CHR ) v = va_arg( ap, char * );
		else v = va_arg( ap, newstr * );
		if ( v ) {
			s = list_addvp( a, mode, v );
			if ( s==NULL ) { ret = LIST_ERR; goto out; }
		}
	} while ( v );
out:
	va_end( ap );
	return ret;
}

int
list_add_all( list *a, ... )
{
	int ret = LIST_OK;
	va_list ap;
	newstr *s, *v;
	va_start( ap, a );
	do {
		v = va_arg( ap, newstr * );
		if ( v ) {
			s = list_addvp( a, LIST_STR, (void*)v );
			if ( s==NULL ) { ret = LIST_ERR; goto out; }
		}
	} while ( v );
out:
	va_end( ap );
	return ret;
}

int
list_addc_all( list *a, ... )
{
	int ret = LIST_OK;
	va_list ap;
	newstr *s;
	const char *v;
	va_start( ap, a );
	do {
		v = va_arg( ap, const char * );
		if ( v ) {
			s = list_addvp( a, LIST_CHR, (void*)v );
			if ( s==NULL ) { ret = LIST_ERR; goto out; }
		}
	} while ( v );
out:
	va_end( ap );
	return ret;
}

int
list_append( list *a, list *toadd )
{
	newstr *s;
	int i;
	for ( i=0; i<toadd->n; ++i ) {
		s = list_add( a, &(toadd->str[i]) );
		if ( !s ) return LIST_ERR;
	}
	return LIST_OK;
}

int
list_append_unique( list *a, list *toadd )
{
	newstr *s;
	int i;
	for ( i=0; i<toadd->n; ++i ) {
		s = list_add_unique( a, &(toadd->str[i]) );
		if ( !s ) return LIST_ERR;
	}
	return LIST_OK;
}

int
list_remove( list *a, int n )
{
	int i;
	if ( !list_valid_num( a, n ) ) return -1;
	for ( i=n+1; i<a->n; ++i ) {
		newstr_newstrcpy( &(a->str[i-1]), &(a->str[i]) );
		if ( newstr_memerr( &(a->str[i-1]) ) ) return LIST_ERR;
	}
	a->n--;
	return LIST_OK;
}

void
list_swap( list *a, int n1, int n2 )
{
	newstr_swapstrings( &(a->str[n1]), &(a->str[n2]) );
}

void
list_sort( list *a )
{
	qsort( a->str, a->n, sizeof( newstr ), list_comp );
	a->sorted = 1;
}

static int
list_find_sorted( list *a, const char *searchstr )
{
	int min, max, mid, comp;
	newstr s, *cs;
	newstr_init( &s );
	newstr_strcpy( &s, searchstr );
	min = 0;
	max = a->n - 1;
	while ( min <= max ) {
		mid = ( min + max ) / 2;
		cs = list_get( a, mid );
		comp = list_comp( (void*)cs, (void*) (&s) );
		if ( comp==0 ) {
			newstr_free( &s );
			return mid;
		}
		else if ( comp > 0 ) max = mid - 1;
		else if ( comp < 0 ) min = mid + 1;
	}
	newstr_free( &s );
	return -1;
}

static int
list_find_simple( list *a, const char *searchstr, int nocase )
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
list_find( list *a, const char *searchstr )
{
	if ( a->n==0 ) return -1;
	if ( a->sorted )
		return list_find_sorted( a, searchstr );
	else
		return list_find_simple( a, searchstr, 0 );
}

int
list_findnocase( list *a, const char *searchstr )
{
	return list_find_simple( a, searchstr, 1 );
}

int
list_fillfp( list *a, FILE *fp, unsigned char skip_blank_lines )
{
	int bufpos = 0, ret = LIST_OK;
	char buf[512]="";
	newstr line;

	list_empty( a );
	newstr_init( &line );
	while ( newstr_fget( fp, buf, sizeof(buf), &bufpos, &line ) ) {
		if ( skip_blank_lines && line.len==0 ) continue;
		if ( !list_add( a, &line ) ) { ret = LIST_ERR; goto out; }
	}
out:
	newstr_free( &line );
	return ret;
}

int
list_fill( list *a, const char *filename, unsigned char skip_blank_lines )
{
	FILE *fp;
	int ret;

	fp = fopen( filename, "r" );
	if ( !fp ) return LIST_ERR_CANNOTOPEN;

	ret = list_fillfp( a, fp, skip_blank_lines );

	fclose( fp );

	return ret;
}

int
list_copy( list *to, list *from )
{
	int i;

	list_free( to );

	if ( from->n==0 ) return LIST_OK;

	to->str = ( newstr * ) malloc( sizeof( newstr ) * from->n );
	if ( !to->str ) {
		to->n = to->max = 0;
		return LIST_ERR;
	}

	to->max = from->n;
	to->sorted = from->sorted;

	for ( i=0; i<from->n; i++ )
		newstr_init( &(to->str[i]) );

	for ( i=0; i<from->n; i++ ) {
		newstr_newstrcpy( &(to->str[i]), &(from->str[i]) );
		if ( newstr_memerr( &(to->str[i]) ) ) return LIST_ERR;
		to->n += 1;
	}
	return LIST_OK;
}

list *
list_dup( list *from )
{
	list *to;
	int ok;

	to = list_new();
	if ( to ) {
		ok = list_copy( to, from );
		if ( !ok ) {
			list_delete( to );
			to = NULL;
		}
	}

	return to;
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

int
list_tokenizec( list *tokens, char *p, const char *delim, int merge_delim )
{
	int ret = LIST_OK;
	newstr s, *t;
	char *q;
	list_empty( tokens );
	newstr_init( &s );
	while ( p && *p ) {
		q = p;
		while ( *q && !strchr( delim, *q ) ) q++;
		newstr_segcpy( &s, p, q );
		if ( newstr_memerr( &s ) ) { ret = LIST_ERR; goto out; }
		if ( s.len ) {
			t = list_addvp( tokens, LIST_STR, (void*) &s );
			if ( !t ) { ret = LIST_ERR; goto out; }
		} else if ( !merge_delim ) {
			t = list_addvp( tokens, LIST_CHR, (void*) "" );
			if ( !t ) { ret = LIST_ERR; goto out; }
		}
		p = q;
		if ( *p ) p++;
	}
out:
	newstr_free( &s );
	return ret;
}

int
list_tokenize( list *tokens, newstr *in, const char *delim, int merge_delim )
{
	return list_tokenizec( tokens, in->data, delim, merge_delim );
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

