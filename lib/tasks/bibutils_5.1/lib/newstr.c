/*
 * newstr.c
 *
 * Version: 05/29/13
 *
 * Copyright (c) Chris Putnam 1999-2013
 *
 * Source code released under the GPL version 2
 *
 *
 * routines for dynamically allocated strings
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <ctype.h>
#include <limits.h>
#include "newstr.h"
#include "is_ws.h"

#include <assert.h>

#define newstr_initlen (64)

#ifndef NEWSTR_PARANOIA

static void 
newstr_realloc( newstr *s, unsigned long minsize )
{
	char *newptr;
	unsigned long size;
	assert( s );
	size = 2 * s->dim;
	if (size < minsize) size = minsize;
	newptr = (char *) realloc( s->data, sizeof( *(s->data) )*size );
	if ( !newptr ) {
		fprintf(stderr,"Error.  Cannot reallocate memory (%ld bytes) in newstr_realloc.\n", sizeof(*(s->data))*size);
		exit( EXIT_FAILURE );
	}
	s->data = newptr;
	s->dim = size;
}

/* define as no-op */
static inline void
newstr_nullify( newstr *s )
{
}

#else

static void 
newstr_realloc( newstr *s, unsigned long minsize )
{
	char *newptr;
	unsigned long size;
	assert( s );
	size = 2 * s->dim;
	if ( size < minsize ) size = minsize;
	newptr = (char *) malloc( sizeof( *(s->data) ) * size );
	if ( !newptr ) {
		fprintf( stderr, "Error.  Cannot reallocate memory (%d bytes)"
			" in newstr_realloc.\n", sizeof(*(s->data))*size );
		exit( EXIT_FAILURE );
	}
	if ( s->data ) {
		newstr_nullify( s );
		free( s->data );
	}
	s->data = newptr;
	s->dim = size;
}

static inline void
newstr_nullify( newstr *s )
{
	memset( s->data, 0, s->dim );
}

#endif

void 
newstr_init( newstr *s )
{
	assert( s );
	s->dim = 0;
	s->len = 0;
	s->data = NULL;
}

void
newstr_initstr( newstr *s, char *initstr )
{
	assert( s );
	assert( initstr );
	newstr_init( s );
	newstr_strcpy( s, initstr );
}

void
newstrs_init( newstr *s, ... )
{
	newstr *s2;
	va_list ap;
	newstr_init( s );
	va_start( ap, s );
	do {
		s2 = va_arg( ap, newstr * );
		if ( s2 ) newstr_init( s2 );
	} while ( s2 );
	va_end( ap );
}

void
newstr_mergestrs( newstr *s, ... )
{
	va_list ap;
	char *cp;
	newstr_empty( s );
	va_start( ap, s );
	do {
		cp = va_arg( ap, char * );
		if ( cp ) newstr_strcat( s, cp );
	} while ( cp );
	va_end( ap );
}

static void 
newstr_initalloc( newstr *s, unsigned long minsize )
{
	unsigned long size = newstr_initlen;
	assert( s );
	if ( minsize > newstr_initlen ) size = minsize;
	s->data = (char *) malloc (sizeof( *(s->data) ) * size);
	if ( !s->data ) {
		fprintf(stderr,"Error.  Cannot allocate memory in newstr_initalloc.\n");
		exit( EXIT_FAILURE );
	}
	s->data[0]='\0';
	s->dim=size;
	s->len=0;
}

newstr *
newstr_new( void )
{
	newstr *s = (newstr *) malloc( sizeof( *s ) );
	if ( s )
		newstr_initalloc( s, newstr_initlen );
	return s;
}

void 
newstr_free( newstr *s )
{
	assert( s );
	if ( s->data ) {
		newstr_nullify( s );
		free( s->data );
	}
	s->dim = 0;
	s->len = 0;
	s->data = NULL;
}

void
newstrs_free( newstr *s, ... )
{
	newstr *s2;
	va_list ap;
	newstr_free( s );
	va_start( ap, s );
	do {
		s2 = va_arg( ap, newstr * );
		if ( s2 ) newstr_free( s2 );
	} while ( s2 );
	va_end( ap );
}

void
newstr_empty( newstr *s )
{
	assert( s );
	if ( s->data ) {
		newstr_nullify( s );
		s->data[0] = '\0';
	}
	s->len = 0;
}

void
newstrs_empty( newstr *s, ... )
{
	newstr *s2;
	va_list ap;
	newstr_empty( s );
	va_start( ap, s );
	do {
		s2 = va_arg( ap, newstr * );
		if ( s2 ) newstr_empty( s2 );
	} while ( s2 );
	va_end( ap );
}

void
newstr_addchar( newstr *s, char newchar )
{
	assert( s );
	if ( newchar=='\0' ) return; /* appending '\0' is a null operation */
	if ( !s->data || s->dim==0 ) 
		newstr_initalloc( s, newstr_initlen );
	if ( s->len + 2 > s->dim ) 
		newstr_realloc( s, s->len+2 );
	s->data[s->len++] = newchar;
	s->data[s->len] = '\0';
}

/* newstr_addutf8
 *
 * Add potential multibyte character to s starting at pointer p.
 * Multibyte Unicode characters have the high bit set.
 *
 * Since we can progress more than one byte at p, return the
 * properly updated pointer p.
 */
char *
newstr_addutf8( newstr *s, char *p )
{
	if ( ! ((*p) & 128 ) ) {
		newstr_addchar( s, *p );
		p++;
	} else {
		while ( ((*p) & 128) ) {
			newstr_addchar( s, *p );
			p++;
		}
	}
	return p;
}

void 
newstr_fprintf( FILE *fp, newstr *s )
{
	assert( s );
	if ( s->data ) fprintf( fp, "%s", s->data );
}

void
newstr_prepend( newstr *s, char *addstr )
{
	unsigned long lenaddstr, i;
	assert( s && addstr );
	lenaddstr = strlen( addstr );
	if ( !s->data || !s->dim )
		newstr_initalloc( s, lenaddstr+1 );
	else {
		if ( s->len + lenaddstr  + 1 > s->dim )
			newstr_realloc( s, s->len + lenaddstr + 1 );
		for ( i=s->len+lenaddstr-1; i>=lenaddstr; i-- )
			s->data[i] = s->data[i-lenaddstr];
	}
	strncpy( s->data, addstr, lenaddstr );
	s->len += lenaddstr;
	s->data[ s->len ] = '\0';
}

static inline void
newstr_strcat_ensurespace( newstr *s, unsigned long n )
{
	unsigned long m = s->len + n + 1;
	if ( !s->data || !s->dim )
		newstr_initalloc( s, m );
	else if ( s->len + n + 1 > s->dim )
		newstr_realloc( s, m );
}

static inline void 
newstr_strcat_internal( newstr *s, char *addstr, unsigned long n )
{
	newstr_strcat_ensurespace( s, n );
	strncat( &(s->data[s->len]), addstr, n );
	s->len += n;
	s->data[s->len]='\0';
}

void
newstr_newstrcat( newstr *s, newstr *old )
{
	assert ( s && old );
	if ( !old->data ) return;
	else newstr_strcat_internal( s, old->data, old->len );
}

void
newstr_strcat( newstr *s, char *addstr )
{
	unsigned long n;
	assert( s && addstr );
	n = strlen( addstr );
	newstr_strcat_internal( s, addstr, n );
}

void
newstr_segcat( newstr *s, char *startat, char *endat )
{
	size_t seglength;
	char *p, *q;

	assert( s && startat && endat );
	assert( (size_t) startat < (size_t) endat );

	seglength=(size_t) endat - (size_t) startat;
	if ( !s->data || !s->dim )
		newstr_initalloc( s, seglength+1 );
	else {
		if ( s->len + seglength + 1 > s->dim )
			newstr_realloc( s, s->len + seglength+1 );
	}
	q = &(s->data[s->len]);
	p = startat;
	while ( *p && p!=endat ) *q++ = *p++;
	*q = '\0';
	s->len += seglength;
}

static inline void
newstr_strcpy_ensurespace( newstr *s, unsigned long n )
{
	unsigned long m = n + 1;
	if ( !s->data || !s->dim )
		newstr_initalloc( s, m );
	else if ( n+1 > s->dim ) 
		newstr_realloc( s, m );
}

static inline void
newstr_strcpy_internal( newstr *s, char *p, unsigned long n )
{
	newstr_strcpy_ensurespace( s, n );
	strcpy( s->data, p );
	s->len = n;
}

void
newstr_newstrcpy( newstr *s, newstr *old )
{
	assert( s );
	if ( s==old ) return;
	else if ( !old || old->len==0 ) newstr_empty( s );
	else newstr_strcpy_internal( s, old->data, old->len );
}

void 
newstr_strcpy( newstr *s, char *addstr )
{
	unsigned long n;
	assert( s && addstr );
	n = strlen( addstr );
	newstr_strcpy_internal( s, addstr, n );
}

newstr *
newstr_strdup( char *s1 )
{
	newstr *s2 = newstr_new();
	if ( s2 )
		newstr_strcpy( s2, s1 );
	return s2;
}

/*
 * newstr_indxcpy( s, in, start, stop );
 *
 * copies in[start] to in[stop] (includes stop) into s
 */
void
newstr_indxcpy( newstr *s, char *p, int start, int stop )
{
	int i;
	assert( s );
	assert( p );
	assert( start <= stop );
	newstr_strcpy_ensurespace( s, stop-start+1 );
	for ( i=start; i<=stop; ++i )
		s->data[i-start] = p[i];
	s->data[i] = '\0';
	s->len = stop-start+1;
}

void
newstr_indxcat( newstr *s, char *p, int start, int stop )
{
	int i;
	assert( s );
	assert( p );
	assert( start <= stop );
	for ( i=start; i<=stop; ++i )
		newstr_addchar( s, p[i] );
}

/* newstr_segcpy( s, start, end );
 *
 * copies [start,end) into s
 */
void
newstr_segcpy( newstr *s, char *startat, char *endat )
{
	size_t n;
	char *p, *q;

	assert( s && startat && endat );
	assert( ((size_t) startat) <= ((size_t) endat) );

	n = (size_t) endat - (size_t) startat;
	newstr_strcpy_ensurespace( s, n );
	q = s->data;
	p = startat;
	while ( *p && p!=endat ) *q++ = *p++;
	*q = '\0';
	s->len = n;
}

void
newstr_segdel( newstr *s, char *p, char *q )
{
	newstr tmp1, tmp2;
	char *r;
	assert( s );
	r = &(s->data[s->len]);
	newstr_init( &tmp1 );
	newstr_init( &tmp2 );
	newstr_segcpy( &tmp1, s->data, p );
	newstr_segcpy( &tmp2, q, r );
	newstr_empty( s );
	if ( tmp1.data ) newstr_strcat( s, tmp1.data );
	if ( tmp2.data ) newstr_strcat( s, tmp2.data );
	newstr_free( &tmp2 );
	newstr_free( &tmp1 );
}

/*
 * newstr_findreplace()
 *
 *   if replace is "" or NULL, then delete find
 */

int
newstr_findreplace( newstr *s, char *find, char *replace )
{
	long diff;
	size_t findstart, searchstart;
	size_t p1, p2;
	size_t find_len, rep_len, curr_len;
	char empty[2] = "";
	unsigned long minsize;
	char *p;
	int n = 0;

	assert( s && find );
	if ( !s->data || !s->dim ) return n;
	if ( !replace ) replace = empty;

	find_len = strlen( find );
	rep_len  = strlen( replace );
	diff     = rep_len - find_len;
	if ( diff < 0 ) diff = 0;

	searchstart=0;
	while ((p=strstr(s->data + searchstart,find))!=NULL) {
		curr_len = strlen(s->data);
		findstart=(size_t) p - (size_t) s->data;
		minsize = curr_len + diff + 1;
	 	if (s->dim <= minsize) newstr_realloc( s, minsize );
		if ( find_len > rep_len ) {
			p1 = findstart + rep_len;
			p2 = findstart + find_len;
			while( s->data[p2] )
				s->data[p1++]=s->data[p2++];
			s->data[p1]='\0';
			n++;
		} else if ( find_len < rep_len ) {
			for ( p1=curr_len; p1>=findstart+find_len; p1-- )
				s->data[p1+diff] = s->data[p1];
			n++;
		}
		for (p1=0; p1<rep_len; p1++)
			s->data[findstart+p1]=replace[p1];
		searchstart = findstart + rep_len; 
		s->len += rep_len - find_len;
	}
	return n;
}


/* newstr_fget()
 *   returns 0 if we're done, 1 if we're not done
 *   extracts line by line (regardless of end characters)
 *   and feeds from buf....
 */
int
newstr_fget( FILE *fp, char *buf, int bufsize, int *pbufpos, newstr *outs )
{
	int  bufpos = *pbufpos, done = 0;
	char *ok;
	newstr_empty( outs );
	while ( !done ) {
		while ( buf[bufpos] && buf[bufpos]!='\r' && buf[bufpos]!='\n' )
			newstr_addchar( outs, buf[bufpos++] );
		if ( buf[bufpos]=='\0' ) {
			ok = fgets( buf, bufsize, fp );
			bufpos=*pbufpos=0;
			if ( !ok && feof(fp) ) { /* end-of-file */
				buf[bufpos] = 0;
				if ( outs->len==0 ) return 0; /*nothing in out*/
				else return 1; /*one last out */
			}
		} else if ( buf[bufpos]=='\r' || buf[bufpos]=='\n' ) done=1;
	}
	if ( ( buf[bufpos]=='\n' && buf[bufpos+1]=='\r') ||
	     ( buf[bufpos]=='\r' && buf[bufpos+1]=='\n') ) bufpos+=2;
	else if ( buf[bufpos]=='\n' || buf[bufpos]=='\r' ) bufpos+=1; 
	*pbufpos = bufpos;
	return 1;
}

void
newstr_toupper( newstr *s )
{
	unsigned long i;
	assert( s );
	for ( i=0; i<s->len; ++i )
		s->data[i] = toupper( (unsigned char)s->data[i] );
}

void
newstr_tolower( newstr *s )
{
	unsigned long i;
	assert( s );
	for ( i=0; i<s->len; ++i )
		s->data[i] = tolower( (unsigned char)s->data[i] );
}

/* newstr_swapstrings( s1, s2 )
 * be sneaky and swap internal newstring data from one
 * string to another
 */
void
newstr_swapstrings( newstr *s1, newstr *s2 )
{
	char *tmpp;
	int tmp;

	assert( s1 && s2 );

	/* swap dimensioning info */
	tmp = s1->dim;
	s1->dim = s2->dim;
	s2->dim = tmp;

	/* swap length info */
	tmp = s1->len;
	s1->len = s2->len;
	s2->len = tmp;

	/* swap data */
	tmpp = s1->data;
	s1->data = s2->data;
	s2->data = tmpp;
}

void
newstr_trimstartingws( newstr *s )
{
	unsigned char still_ws;
	unsigned long n, m;

	assert( s );

	if ( s->len==0 || !is_ws( s->data[0] ) ) return;

	m = n = 0;
	still_ws = 1;
	while ( m <= s->len ) {
		if ( still_ws && !is_ws( s->data[ m ] ) ) {
			still_ws = 0;
		}
		if ( !still_ws ) {
			s->data[ n ] = s->data[ m ];
			n++;
		}
		m++;
	}

	s->len = n;
}
	

void
newstr_trimendingws( newstr *s )
{
	assert( s );
	while ( s->len > 0 && is_ws( s->data[s->len-1] ) ) {
		s->data[s->len-1] = '\0';
		s->len--;
	}
}

int
newstr_match_first( newstr *s, char ch )
{
	if ( !s->len ) return 0;
	if ( s->data[0] == ch ) return 1;
	return 0;
}

int
newstr_match_end( newstr *s, char ch )
{
	if ( !s->len ) return 0;
	if ( s->data[ s->len - 1 ] == ch ) return 1;
	return 0;
}

void
newstr_trimbegin( newstr *s, int n )
{
	int i;
	assert( s );
	if ( s->len - n < 1 ) newstr_empty( s );
	for ( i=1; i<=s->len; ++i ) /* pick up '\0' with '<=' */
		s->data[i-1] = s->data[i];
	s->len -= n;
}

void
newstr_trimend( newstr *s, int n )
{
	assert( s );
	if ( s->len - n < 1 ) newstr_empty( s );
	else {
		s->len -= n;
		s->data[ s->len ] = '\0';
	}
}

static void
newstr_check_case( newstr *s, int *lowercase, int *uppercase )
{
	int i;
	*lowercase = 0;
	*uppercase = 0;
	if ( s->len < 1 ) return;
	for ( i=0; i<s->len && !( *lowercase && *uppercase ); ++i ) {
		if ( isalpha( (unsigned char)s->data[i] ) ) {
			if ( isupper( (unsigned char)s->data[i] ) ) *uppercase += 1;
			else if ( islower( (unsigned char)s->data[i] ) ) *lowercase += 1;
		}
	}
}

int
newstr_is_mixedcase( newstr *s )
{
	int lowercase, uppercase;
	newstr_check_case( s, &lowercase, &uppercase );
	if ( lowercase > 0 && uppercase > 0 ) return 1;
	return 0;
}

int
newstr_is_lowercase( newstr *s )
{
	int lowercase, uppercase;
	newstr_check_case( s, &lowercase, &uppercase );
	if ( lowercase > 0 && uppercase == 0 ) return 1;
	return 0;
}

int
newstr_is_uppercase( newstr *s )
{
	int lowercase, uppercase;
	newstr_check_case( s, &lowercase, &uppercase );
	if ( lowercase == 0 && uppercase > 0 ) return 1;
	return 0;
}

void
newstr_stripws( newstr *s )
{
	unsigned long len = 0;
	char *p, *q;
	assert( s );
	if ( s->len ) {
		p = q = s->data;
		while ( *p ) {
			if ( !is_ws( *p ) ) {
				*q = *p;
				q++;
				len++;
			}
			p++;
		}
		*q = '\0';
	}
	s->len = len;
}

int
newstr_newstrcmp( newstr *s, newstr *t )
{
	assert( s );
	assert( t );
	if ( s->len == 0 && t->len == 0 ) return 0;
	return strcmp( s->data, t->data );
}

void
newstr_reverse( newstr *s )
{
	newstr ns;
	unsigned long i;

	assert( s );

	if ( s->len==0 ) return;
	newstr_init( &ns );
	i = s->len;
	do {
		i--;
		newstr_addchar( &ns, s->data[i] );
	} while ( i>0 );
	newstr_swapstrings( s, &ns );
	newstr_free( &ns );
}

int
newstr_fgetline( newstr *s, FILE *fp )
{
	int ch, eol = 0;
	assert( s );
	newstr_empty( s );
	if ( feof( fp ) ) return 0;
	while ( !feof( fp ) && !eol ) {
		ch = fgetc( fp );
		if ( ch == EOF ) eol = 1;
		else if ( ch == '\n' ) eol = 1;
		else if ( ch == '\r' ) {
			ch = fgetc( fp );
			if ( ch != '\n' ) ungetc( ch, fp );
			eol = 1;
		} else {
			newstr_addchar( s, (char) ch );
		}
	}
	return 1;
}

/*
 * s = "Hi!\0", s.len = 3
 *
 * newstr_char( s, 0 ) = 'H'  newstr_revchar( s, 0 ) = '\0'
 * newstr_char( s, 1 ) = 'i'  newstr_revchar( s, 1 ) = '!'
 * newstr_char( s, 2 ) = '!'  newstr_revchar( s, 2 ) = 'i'
 * newstr_char( s, 3 ) = '\0' newstr_revchar( s, 3 ) = 'H'
 */
char
newstr_char( newstr *s, unsigned long n )
{
	if ( s->len==0 || n >= s->len ) return '\0';
	return s->data[ n ];
}

char
newstr_revchar( newstr *s, unsigned long n )
{
	if ( s->len==0 || n >= s->len ) return '\0';
	return s->data[ s->len - n ];
}
