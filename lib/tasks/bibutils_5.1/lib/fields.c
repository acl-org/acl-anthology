/*
 * fields.c
 *
 * Copyright (c) Chris Putnam 2003-2013
 *
 * Source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include "fields.h"

fields*
fields_new( void )
{
	fields *f = ( fields * ) malloc( sizeof( fields ) );
	if ( f ) fields_init( f );
	return f;
}

void
fields_init( fields *f )
{
	assert( f );

	f->used  = NULL;
	f->level = NULL;
	f->tag   = NULL;
	f->data  = NULL;
	f->max   = f->n = 0;
}

void
fields_free( fields *f )
{
	int i;

	assert( f );

	for ( i=0; i<f->max; ++i ) {
		newstr_free( &(f->tag[i]) );
		newstr_free( &(f->data[i]) );
	}
	if ( f->tag )   free( f->tag );
	if ( f->data )  free( f->data );
	if ( f->used )  free( f->used );
	if ( f->level ) free( f->level );

	fields_init( f );
}

static int
fields_alloc( fields *f )
{
	int i, alloc = 20;

	f->tag   = (newstr *) malloc( sizeof(newstr) * alloc );
	f->data  = (newstr *) malloc( sizeof(newstr) * alloc );
	f->used  = (int *)    calloc( alloc, sizeof(int) );
	f->level = (int *)    calloc( alloc, sizeof(int) );
	if ( !f->tag || !f->data || !f->used || !f->level ){
		if ( f->tag )   free( f->tag );
		if ( f->data )  free( f->data );
		if ( f->used )  free( f->used );
		if ( f->level ) free( f->level );
		fields_init( f );
		return 0;
	}

	f->max = alloc;
	f->n = 0;
	for ( i=0; i<alloc; ++i ) {
		newstr_init( &(f->tag[i]) );
		newstr_init( &(f->data[i]) );
	}
	return 1;
}

static int
fields_realloc( fields *f )
{
	newstr *newtags, *newdata;
	int *newused, *newlevel;
	int i, alloc = f->max * 2;

	newtags = (newstr*) realloc( f->tag, sizeof(newstr) * alloc );
	newdata = (newstr*) realloc( f->data, sizeof(newstr) * alloc );
	newused = (int*)    realloc( f->used, sizeof(int) * alloc );
	newlevel= (int*)    realloc( f->level, sizeof(int) * alloc );

	if ( newtags )  f->tag   = newtags;
	if ( newdata )  f->data  = newdata;
	if ( newused )  f->used  = newused;
	if ( newlevel ) f->level = newlevel;
	
	if ( !newtags || !newdata || !newused || !newlevel )
		return 0;

	f->max = alloc;

	for ( i=f->n; i<alloc; ++i ) {
		newstr_init( &(f->tag[i]) );
		newstr_init( &(f->data[i]) );
	}

	return 1;
}

int
fields_add( fields *f, char *tag, char *data, int level )
{
	int i, found;

	assert( f );

	if ( !tag || !data ) return 1;

	if ( f->max==0 ) {
		if ( !fields_alloc( f ) ) return 0;
	} else if ( f->n >= f->max ) {
		if ( !fields_realloc( f ) ) return 0;
	}

	/* Don't duplicate identical entries */
	found = 0;
	for ( i=0; i<f->n && !found; ++i ) {
		if ( f->level[i]==level &&
		     !strcasecmp( f->tag[i].data, tag ) &&
		     !strcasecmp( f->data[i].data, data ) ) found = 1;
	}
	if ( !found ) {
		newstr_strcpy( &(f->tag[f->n]), tag );
		newstr_strcpy( &(f->data[f->n]), data );
		f->used[ f->n ] = 0;
		f->level[ f->n ] = level;
		f->n++;
	}
	return 1;
}

int
fields_add_tagsuffix( fields *f, char *tag, char *suffix,
		char *data, int level )
{
	newstr newtag;
	int ret;

	assert( f );
	assert( tag );
	assert( suffix );

	newstr_init( &newtag );
	newstr_mergestrs( &newtag, tag, suffix, NULL );
	ret = fields_add( f, newtag.data, data, level );
	newstr_free( &newtag );

	return ret;
}

/* fields_get_level()
 *
 */
inline int
fields_get_level( fields *f, int n )
{
	assert( f );
	assert( n>=0 );
	assert( n<f->n );

	return f->level[n];
}

/* fields_match_level()
 *
 * returns 1 if level matched, 0 if not
 *
 * level==-1 is a special flag meaning any level can match
 */
inline int
fields_match_level( fields *f, int n, int level )
{
	assert( f );

	if ( level==LEVEL_ANY ) return 1;
	if ( fields_get_level( f, n )==level ) return 1;
	return 0;
}

/* fields_match_tag()
 *
 * returns 1 if tag matches, 0 if not
 *
 */
inline int
fields_match_tag( fields *info, int n, char *tag )
{
	if ( !strcmp( fields_tag( info, n, FIELDS_CHRP ), tag ) ) return 1;
	return 0;
}

inline int
fields_match_casetag( fields *info, int n, char *tag )
{
	if ( !strcasecmp( fields_tag( info, n, FIELDS_CHRP ), tag ) ) return 1;
	return 0;
}

inline int
fields_match_tag_level( fields *info, int n, char *tag, int level )
{
	if ( !fields_match_level( info, n, level ) ) return 0;
	return fields_match_tag( info, n, tag );
}

inline int
fields_match_casetag_level( fields *info, int n, char *tag, int level )
{
	if ( !fields_match_level( info, n, level ) ) return 0;
	return fields_match_casetag( info, n, tag );
}

/* fields_find()
 *
 * Return position [0,f->n) for match of the tag.
 * Return -1 if tag isn't found.
 */
int
fields_find( fields *f, char *tag, int level )
{
	int i;

	assert( f );
	assert( tag );

	for ( i=0; i<f->n; ++i ) {
		if ( !fields_match_casetag_level( f, i, tag, level ) )
			continue;
		if ( f->data[i].len ) return i;
		else {
			/* if there is no data for the tag, don't "find" it */
			/* and set "used" so noise is suppressed */
			f->used[i] = 1;
		}
	}

	return -1;
}

int
fields_maxlevel( fields *f )
{
	int i, max = 0;

	assert( f );

	for ( i=0; i<f->n; ++i ) {
		if ( f->level[i] > max )
			max = f->level[i];
	}

	return max;
}

void
fields_clearused( fields *f )
{
	int i;

	assert( f );

	for ( i=0; i<f->n; ++i )
		f->used[i] = 0;
}

void
fields_setused( fields *f, int n )
{
	assert( f );

	if ( n < f->n )
		f->used[n] = 1;
}

/* fields_replace_or_add()
 *
 * return 1 on success, 0 on memory error
 */
int
fields_replace_or_add( fields *f, char *tag, char *data, int level )
{
	int n = fields_find( f, tag, level );
	if ( n==-1 ) return fields_add( f, tag, data, level );
	else {
		newstr_strcpy( &(f->data[n]), data );
		return 1;
	}
}

char *fields_null_value = "\0";

inline int
fields_used( fields *f, int n )
{
	if ( n < f->n ) return f->used[n];
	else return 0;
}

inline int
fields_nodata( fields *f, int n )
{
	newstr *d;
	if ( n < f->n ) {
		d = &( f->data[n] );
		if ( d->len > 0 ) return 0;
		return 1;
	} else {
		return 1;
	}
}

inline int
fields_num( fields *f )
{
	assert( f );
	return f->n;
}

/*
 * #define FIELDS_CHRP       
 * #define FIELDS_STRP       
 * #define FIELDS_CHRP_NOLEN
 * #define FIELDS_STRP_NOLEN
 * 
 * If the length of the tagged value is zero and the mode is
 * FIELDS_STRP_NOLEN or FIELDS_CHRP_NOLEN, return a pointer to
 * a static null string as the data field could be new due to
 * the way newstr handles initialized strings with no data.
 *
 */

void *
fields_value( fields *f, int n, int mode )
{
	intptr_t retn;

	assert( f );
	assert( n >= 0 );
	assert( n < f->n );

	if ( mode & FIELDS_SETUSE_FLAG )
		fields_setused( f, n );

	if ( mode & FIELDS_STRP_FLAG )
		return &(f->data[n]);
	else if ( mode & FIELDS_POSP_FLAG ) {
		retn = n;
		return ( void * ) retn; /* Rather pointless */
	} else {
		if ( f->data[n].len )
			return f->data[n].data;
		else
			return fields_null_value;
	}
}

void *
fields_tag( fields *f, int n, int mode )
{
	intptr_t retn;

	assert( f );
	assert( n >= 0 );
	assert( n < f->n );

	if ( mode & FIELDS_STRP_FLAG )
		return &(f->tag[n]);
	else if ( mode & FIELDS_POSP_FLAG ) {
		retn = n;
		return ( void * ) retn; /* Rather pointless */
	} else {
		if ( f->tag[n].len )
			return f->tag[n].data;
		else
			return fields_null_value;
	}
}

int
fields_level( fields *f, int n )
{
	assert( f );
	assert( n >= 0 );
	assert( n < f->n );

	return f->level[n];
}

void *
fields_findv( fields *f, int level, int mode, char *tag )
{
	int i, found = -1;
	intptr_t retn;

	assert( f );
	assert( tag );

	for ( i=0; i<f->n && found==-1; ++i ) {

		if ( !fields_match_level( f, i, level ) ) continue;
		if ( !fields_match_casetag( f, i, tag ) ) continue;

		if ( f->data[i].len!=0 ) found = i;
		else {
			if ( mode & FIELDS_NOLENOK_FLAG ) {
				return (void *) fields_null_value;
			} else if ( mode & FIELDS_SETUSE_FLAG ) {
				f->used[i] = 1; /* Suppress "noise" of unused */
			}
		}
	}

	if ( found==-1 ) return NULL;

	if ( mode & FIELDS_SETUSE_FLAG )
		fields_setused( f, found );

	if ( mode & FIELDS_STRP_FLAG )
		return (void *) &(f->data[found]);
	else if ( mode & FIELDS_POSP_FLAG ) {
		retn = found;
		return (void *) retn;
	} else
		return (void *) f->data[found].data;
}

void *
fields_findv_firstof( fields *f, int level, int mode, ... )
{
	char *tag, *value;
	va_list argp;

	assert( f );

	va_start( argp, mode );
	while ( ( tag = ( char * ) va_arg( argp, char * ) ) ) {
		value = fields_findv( f, level, mode, tag );
		if ( value ) {
			va_end( argp );
			return value;
		}
	}
	va_end( argp );

	return NULL;
}

static void
fields_findv_each_add( fields *f, int mode, int n, vplist *a )
{
	intptr_t retn;

	assert( a );
	assert( f );
	assert( n >= 0 );
	assert( n < f->n );

	if ( mode & FIELDS_SETUSE_FLAG )
		fields_setused( f, n );

	if ( mode & FIELDS_STRP_FLAG ) {
		vplist_add( a, (void *) &(f->data[n]) );
	} else if ( mode & FIELDS_POSP_FLAG ) {
		retn = n;
		vplist_add( a, (void *) retn );
	} else {
		vplist_add( a, (void *) f->data[n].data );
	}
}

void
fields_findv_each( fields *f, int level, int mode, vplist *a, char *tag )
{
	int i;

	assert( a );
	assert( tag );
	assert( f );

	for ( i=0; i<f->n; ++i ) {

		if ( !fields_match_level( f, i, level ) ) continue;
		if ( !fields_match_casetag( f, i, tag ) ) continue;

		if ( f->data[i].len!=0 ) {
			fields_findv_each_add( f, mode, i, a );
		} else {
			if ( mode & FIELDS_NOLENOK_FLAG ) {
				fields_findv_each_add( f, mode, i, a );
			} else {
				f->used[i] = 1; /* Suppress "noise" of unused */
			}
		}

	}
}

void
fields_findv_eachof( fields *f, int level, int mode, vplist *a, ... )
{
	va_list argp;
	vplist tags;
	char *tag;
	int i, j, found;

	assert( f );
	assert( a );

	vplist_init( &tags );

	/* build list of tags to search for */
	va_start( argp, a );
	while ( ( tag = ( char * ) va_arg( argp, char * ) ) )
		vplist_add( &tags, tag );
	va_end( argp );

	/* search list */
	for ( i=0; i<f->n; ++i ) {

		if ( !fields_match_level( f, i, level ) ) continue;

		found = 0;
		for ( j=0; j<tags.n && !found; ++j ) {
			if ( fields_match_casetag( f, i, vplist_get( &tags, j ) ) )
				found = 1;
		}
		if ( !found ) continue;

		if ( f->data[i].len!=0 ) {
			fields_findv_each_add( f, mode, i, a );
		} else {
			if ( mode & FIELDS_NOLENOK_FLAG ) {
				fields_findv_each_add( f, mode, i, a );
			} else {
				f->used[i] = 1; /* Suppress "noise" of unused */
			}
		}

	}

	vplist_free( &tags );
}
