/*
 * newstr.c
 *
 * Version: 04/17/15
 *
 * Copyright (c) Chris Putnam 1999-2016
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

/* Do not use asserts in NEWSTR_NOASSERT defined */
#ifdef NEWSTR_NOASSERT
#define NDEBUG
#endif
#include <assert.h>

#define newstr_initlen (64)


/* Clear memory in resize/free if NEWSTR_PARANOIA defined */

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

/* define as a no-op */
#define newstr_nullify( s )

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
newstr_initstr( newstr *s, const char *initstr )
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

/*
 * This is currently a stub. Later it will
 * report whether or not a newstr function
 * could not be performed due to a memory
 * error.
 */
int
newstr_memerr( newstr *s )
{
	return 0;
}

void
newstr_mergestrs( newstr *s, ... )
{
	va_list ap;
	const char *cp;
	newstr_empty( s );
	va_start( ap, s );
	do {
		cp = va_arg( ap, const char * );
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
newstr_delete( newstr *s )
{
	assert( s );
	newstr_free( s );
	free( s );
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
		newstr_realloc( s, s->len*2 );
	s->data[s->len++] = newchar;
	s->data[s->len] = '\0';
}

void
newstr_fill( newstr *s, unsigned long n, char fillchar )
{
	unsigned long i;
	assert( s );
	if ( !s->data || s->dim==0 )
		newstr_initalloc( s, n+1 );
	if ( n + 1 > s->dim )
		newstr_realloc( s, n+1 );
	for ( i=0; i<n; ++i )
		s->data[i] = fillchar;
	s->data[n] = '\0';
	s->len = n;
}

/* newstr_addutf8
 *
 * Add potential multibyte character to s starting at pointer p.
 * Multibyte Unicode characters have the high bit set.
 *
 * Since we can progress more than one byte at p, return the
 * properly updated pointer p.
 */
const char *
newstr_addutf8( newstr *s, const char *p )
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
newstr_prepend( newstr *s, const char *addstr )
{
	unsigned long lenaddstr, i;
	assert( s && addstr );
	lenaddstr = strlen( addstr );
	if ( lenaddstr==0 ) return;
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
newstr_strcat_internal( newstr *s, const char *addstr, unsigned long n )
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
newstr_strcat( newstr *s, const char *addstr )
{
	unsigned long n;
	assert( s && addstr );
	n = strlen( addstr );
	newstr_strcat_internal( s, addstr, n );
}

void
newstr_segcat( newstr *s, const char *startat, const char *endat )
{
	unsigned long n;
	const char *p;

	assert( s && startat && endat );
	assert( (size_t) startat < (size_t) endat );

	if ( startat==endat ) return;

	n = 0;
	p = startat;
	while ( p!=endat ) {
		n++;
		p++;
	}

	newstr_strcat_internal( s, startat, n );
}

void
newstr_plcat( newstr *s, const char *startat, unsigned long n )
{
	assert( s && startat );
	newstr_strcat_internal( s, startat, n );
}

void
newstr_indxcat( newstr *s, char *p, unsigned long start, unsigned long stop )
{
	unsigned long i;
	assert( s && p );
	assert( start <= stop );
	for ( i=start; i<stop; ++i )
		newstr_addchar( s, p[i] );
}

/* newstr_cpytodelim()
 *     term      = string of characters to be used as terminators
 *     finalstep = set to non-zero to position return value past the
 *                 terminating character
 */
char *
newstr_cpytodelim( newstr *s, char *p, const char *delim, unsigned char finalstep )
{
	newstr_empty( s );
	return newstr_cattodelim( s, p, delim, finalstep );
}

/* newstr_cpytodelim()
 *     term      = string of characters to be used as terminators
 *     finalstep = set to non-zero to position return value past the
 *                 terminating character
 */
char *
newstr_cattodelim( newstr *s, char *p, const char *delim, unsigned char finalstep )
{
	while ( p && *p && !strchr( delim, *p ) ) {
		newstr_addchar( s, *p );
		p++;
	}
	if ( p && *p && finalstep ) p++;
	return p;
}

static inline void
newstr_strcpy_ensurespace( newstr *s, unsigned long n )
{
	unsigned long m = n + 1;
	if ( !s->data || !s->dim )
		newstr_initalloc( s, m );
	else if ( m > s->dim )
		newstr_realloc( s, m );
}

static inline void
newstr_strcpy_internal( newstr *s, const char *p, unsigned long n )
{
	newstr_strcpy_ensurespace( s, n );
	strncpy( s->data, p, n );
	s->data[n] = '\0';
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
newstr_strcpy( newstr *s, const char *addstr )
{
	unsigned long n;
	assert( s && addstr );
	n = strlen( addstr );
	newstr_strcpy_internal( s, addstr, n );
}

/* newstr_segcpy( s, start, end );
 *
 * copies [start,end) into s
 */
void
newstr_segcpy( newstr *s, const char *startat, const char *endat )
{
	unsigned long n;
	const char *p;

	assert( s && startat && endat );
	assert( ((size_t) startat) <= ((size_t) endat) );

	n = 0;
	p = startat;
	while ( p!=endat ) {
		p++;
		n++;
	}

	newstr_strcpy_internal( s, startat, n );
}

void
newstr_plcpy( newstr *s, const char *startat, unsigned long n )
{
	assert( s && startat );
	newstr_strcpy_internal( s, startat, n );
}

/*
 * newstr_indxcpy( s, in, start, stop );
 *
 * copies in[start,stop) (excludes stop) into s
 */
void
newstr_indxcpy( newstr *s, char *p, unsigned long start, unsigned long stop )
{
	unsigned long i;
	assert( s && p );
	assert( start <= stop );
	if ( start == stop ) {
		newstr_empty( s );
		return;
	}
	newstr_strcpy_ensurespace( s, stop-start+1 );
	for ( i=start; i<stop; ++i )
		s->data[i-start] = p[i];
	s->len = stop-start;
	s->data[s->len] = '\0';
}

newstr *
newstr_strdup( const char *s1 )
{
	newstr *s2 = newstr_new();
	if ( s2 )
		newstr_strcpy( s2, s1 );
	return s2;
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
newstr_findreplace( newstr *s, const char *find, const char *replace )
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
	assert( fp && outs );
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
	char *p, *q;
	int n;

	assert( s );

	if ( s->len==0 || !is_ws( s->data[0] ) ) return;

	n = 0;
	p = s->data;
	while ( is_ws( *p ) ) p++;

	q = s->data;
	while ( *p ) {
		*q++ = *p++;
		n++;
	}
	*q = '\0';

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
	assert( s );
	if ( !s->len ) return 0;
	if ( s->data[0] == ch ) return 1;
	return 0;
}

int
newstr_match_end( newstr *s, char ch )
{
	assert( s );
	if ( !s->len ) return 0;
	if ( s->data[ s->len - 1 ] == ch ) return 1;
	return 0;
}

void
newstr_trimbegin( newstr *s, unsigned long n )
{
	char *p, *q;

	assert( s );

	if ( n==0 ) return;
	if ( s->len==0 ) return;
	if ( n >= s->len ) {
		newstr_empty( s );
		return;
	}

	p = s->data;
	while ( n-- > 0 ) p++;

	n = 0;
	q = s->data;
	while ( *p ) {
		*q++ = *p++;
		n++;
	}
	*q = '\0';

	s->len = n;
}

void
newstr_trimend( newstr *s, unsigned long n )
{
	assert( s );

	if ( n==0 ) return;
	if ( n >= s->len ) {
		newstr_empty( s );
		return;
	}

	s->len -= n;
	s->data[ s->len ] = '\0';
}

void
newstr_pad( newstr *s, unsigned long len, char ch )
{
	unsigned long i;
	assert( s );
	for ( i=s->len; i<len; i++ )
		newstr_addchar( s, ch );
}

void
newstr_copyposlen( newstr *s, newstr *in, unsigned long pos, unsigned long len )
{
	unsigned long i, max;
	assert( s );
	newstr_empty( s );
	max = pos+len;
	if ( max > in->len ) max = in->len;
	for ( i=pos; i<max; ++i )
		newstr_addchar( s, in->data[i] );
}

static void
newstr_check_case( newstr *s, int *lowercase, int *uppercase )
{
	int i;
	assert( s );
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
newstr_newstrcmp( const newstr *s, const newstr *t )
{
	assert( s );
	assert( t );
	if ( s->len == 0 && t->len == 0 ) return 0;
	if ( s->len == 0 ) return strcmp( "", t->data );
	if ( t->len == 0 ) return strcmp( s->data, "" );
	return strcmp( s->data, t->data );
}

void
newstr_reverse( newstr *s )
{
	unsigned long i, max;
	char tmp;
	assert( s );
	max = s->len / 2;
	for ( i=0; i<max; ++i ) {
		tmp = s->data[ i ];
		s->data[ i ] = s->data[ s->len - 1 - i ];
		s->data[ s->len - 1 - i ] = tmp;
	}
}

int
newstr_fgetline( newstr *s, FILE *fp )
{
	int ch, eol = 0;
	assert( s );
	assert( fp );
	newstr_empty( s );
	if ( feof( fp ) ) return 0;
	while ( !feof( fp ) && !eol ) {
		ch = fgetc( fp );
		if ( ch == EOF ) {
			if ( s->len ) return 1;
			else return 0;
		}
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
 * newstr_char( s, 0 ) = 'H'  newstr_revchar( s, 0 ) = '!'
 * newstr_char( s, 1 ) = 'i'  newstr_revchar( s, 1 ) = 'i'
 * newstr_char( s, 2 ) = '!'  newstr_revchar( s, 2 ) = 'H'
 * newstr_char( s, 3 ) = '\0' newstr_revchar( s, 3 ) = '\0'
 */
char
newstr_char( newstr *s, unsigned long n )
{
	assert( s );
	if ( s->len==0 || n >= s->len ) return '\0';
	return s->data[ n ];
}

char
newstr_revchar( newstr *s, unsigned long n )
{
	assert( s );
	if ( s->len==0 || n >= s->len ) return '\0';
	return s->data[ s->len - n - 1];
}

void
newstr_makepath( newstr *path, const char *dirname, const char *filename, char sep )
{
	assert( path );
	if ( dirname ) newstr_strcpy( path, dirname );
	else newstr_empty( path );

	if ( path->len && path->data[path->len-1]!=sep )
		newstr_addchar( path, sep );

	if ( filename ) newstr_strcat( path, filename );
}
