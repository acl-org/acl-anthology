/*
 * newstr.h
 *
 * Version: 05/29/13
 *
 * Copyright (c) Chris Putnam 1999-2013
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

void    newstr_init        ( newstr *s );
void    newstr_initstr     ( newstr *s, char *initstr );
void    newstr_empty       ( newstr *s );
void    newstr_free        ( newstr *s );

void    newstrs_init       ( newstr *s, ... );
void    newstrs_empty      ( newstr *s, ... );
void    newstrs_free       ( newstr *s, ... );

void newstr_mergestrs   ( newstr *s, ... );
newstr *newstr_strdup   ( char *buf );
void newstr_addchar     ( newstr *s, char newchar );
void newstr_reverse     ( newstr *s );
char *newstr_addutf8    ( newstr *s, char *p );
void newstr_strcat      ( newstr *s, char *addstr );
void newstr_newstrcat   ( newstr *s, newstr *old );
void newstr_segcat      ( newstr *s, char *startat, char *endat );
void newstr_prepend     ( newstr *s, char *addstr );
void newstr_strcpy      ( newstr *s, char *addstr );
void newstr_newstrcpy   ( newstr *s, newstr *old );
void newstr_segcpy      ( newstr *s, char *startat, char *endat );
void newstr_segdel      ( newstr *s, char *startat, char *endat );
void newstr_indxcpy     ( newstr *s, char *p, int start, int stop );
void newstr_indxcat     ( newstr *s, char *p, int start, int stop );
void newstr_fprintf     ( FILE *fp, newstr *s );
int  newstr_fget        ( FILE *fp, char *buf, int bufsize, int *pbufpos,
                          newstr *outs );
char newstr_char        ( newstr *s, unsigned long n );
char newstr_revchar     ( newstr *s, unsigned long n );
int  newstr_fgetline    ( newstr *s, FILE *fp );
int  newstr_findreplace ( newstr *s, char *find, char *replace );
void newstr_toupper     ( newstr *s );
void newstr_tolower     ( newstr *s );
void newstr_trimstartingws( newstr *s );
void newstr_trimendingws( newstr *s );
void newstr_swapstrings ( newstr *s1, newstr *s2 );

int  newstr_match_first ( newstr *s, char ch );
int  newstr_match_end   ( newstr *s, char ch );
void newstr_trimbegin   ( newstr *s, int n );
void newstr_trimend     ( newstr *s, int n );

int  newstr_is_mixedcase( newstr *s );
int  newstr_is_lowercase( newstr *s );
int  newstr_is_uppercase( newstr *s );

int newstr_newstrcmp    ( newstr *s, newstr *t );

/* NEWSTR_PARANOIA
 *
 * set to clear memory before it is freed or reallocated
 * note that this is slower...may be important if string
 * contains sensitive information
 */

#undef NEWSTR_PARANOIA

#endif

