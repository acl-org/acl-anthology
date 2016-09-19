/*
 * newstr.h
 *
 * Version: 04/17/15
 *
 * Copyright (c) Chris Putnam 1999-2016
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef NEWSTR_H
#define NEWSTR_H

#include <stdio.h>

typedef struct newstr {
	char *data;
	unsigned long dim;
	unsigned long len;
}  newstr;

newstr *newstr_new         ( void ); 
void    newstr_delete      ( newstr *s );

void     newstr_init      ( newstr *s );
void     newstr_initstr   ( newstr *s, const char *initstr );
void     newstr_empty     ( newstr *s );
void     newstr_free      ( newstr *s );
newstr * newstr_strdup    ( const char *p );

void     newstrs_init     ( newstr *s, ... );
void     newstrs_empty    ( newstr *s, ... );
void     newstrs_free     ( newstr *s, ... );

void     newstr_mergestrs ( newstr *s, ... );
void     newstr_fill      ( newstr *s, unsigned long n, char fillchar );
void     newstr_addchar   ( newstr *s, char newchar );
void     newstr_reverse   ( newstr *s );
void     newstr_strcat    ( newstr *s, const char *addstr );
void     newstr_newstrcat ( newstr *s, newstr *old );
void     newstr_segcat    ( newstr *s, const char *startat, const char *endat );
void     newstr_plcat     ( newstr *s, const char *startat, unsigned long n );
char *   newstr_cpytodelim( newstr *s, char *p, const char *delim, unsigned char finalstep );
char *   newstr_cattodelim( newstr *s, char *p, const char *delim, unsigned char finalstep );
void     newstr_prepend   ( newstr *s, const char *addstr );
void     newstr_strcpy    ( newstr *s, const char *addstr );
void     newstr_newstrcpy ( newstr *s, newstr *old );
void     newstr_segcpy    ( newstr *s, const char *startat, const char *endat );
void     newstr_plcpy     ( newstr *s, const char *startat, unsigned long n );
void     newstr_segdel    ( newstr *s, char *startat, char *endat );
void     newstr_indxcpy   ( newstr *s, char *p, unsigned long start, unsigned long stop );
void     newstr_indxcat   ( newstr *s, char *p, unsigned long start, unsigned long stop );
void     newstr_fprintf   ( FILE *fp, newstr *s );
int      newstr_fget      ( FILE *fp, char *buf, int bufsize, int *pbufpos, newstr *outs );
char     newstr_char      ( newstr *s, unsigned long n );
char     newstr_revchar   ( newstr *s, unsigned long n );
int      newstr_fgetline  ( newstr *s, FILE *fp );
void     newstr_toupper   ( newstr *s );
void     newstr_tolower   ( newstr *s );
int      newstr_findreplace( newstr *s, const char *find, const char *replace );
void     newstr_trimstartingws( newstr *s );
void     newstr_trimendingws( newstr *s );
void     newstr_swapstrings( newstr *s1, newstr *s2 );
void     newstr_stripws   ( newstr *s );

const char *newstr_addutf8( newstr *s, const char *p );

int  newstr_match_first ( newstr *s, char ch );
int  newstr_match_end   ( newstr *s, char ch );
void newstr_trimbegin   ( newstr *s, unsigned long n );
void newstr_trimend     ( newstr *s, unsigned long n );

void newstr_pad         ( newstr *s, unsigned long len, char ch );
void newstr_copyposlen  ( newstr *s, newstr *in, unsigned long pos, unsigned long len );

void newstr_makepath    ( newstr *path, const char *dirname, const char *filename, char sep );


int  newstr_is_mixedcase( newstr *s );
int  newstr_is_lowercase( newstr *s );
int  newstr_is_uppercase( newstr *s );

int  newstr_newstrcmp    ( const newstr *s, const newstr *t );

int  newstr_memerr( newstr *s );


/* #define NEWSTR_PARANOIA
 *
 * set to clear memory before it is freed or reallocated
 * note that this is slower...may be important if string
 * contains sensitive information
 */

/* #define NEWSTR_NOASSERT
 *
 * set to turn off the use of asserts (and associated call to exit)
 * in newstr functions...useful for library construction for
 * Linux distributions that don't want libraries calling exit, but
 * not useful during code development
 */

#endif

