/*
 * reftypes.h
 *
 * Copyright (c) Chris Putnam 2003-2013
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef REFTYPES_H
#define REFTYPES_H

/* Reftypes handled by core code */
#define ALWAYS          (0)
#define DEFAULT         (1)

/* Reftypes to be handled by converters */
#define SIMPLE          (2)
#define TYPE            (3)
#define PERSON          (4)
#define DATE            (5)
#define PAGES           (6)
#define SERIALNO        (7)
#define TITLE           (8)
#define NOTES           (9)
#define DOI             (10)
#define HOWPUBLISHED    (11)
#define LINKEDFILE      (12)
#define KEYWORD         (13)
#define BT_URL          (14) /* Bibtex URL */
#define BT_NOTE         (15) /* Bibtex Note */
#define BT_SENTE        (16) /* Bibtex 'Sente' */
#define BT_GENRE        (17) /* Bibtex Genre */
#define BT_EPRINT       (18) /* Bibtex 'Eprint' */
#define BT_ORG          (19) /* Bibtex Organization */
#define BLT_THESIS_TYPE (20) /* Biblatex Thesis Type */
#define BLT_SCHOOL      (21) /* Biblatex School */
#define BLT_EDITOR      (22) /* Biblatex Editor */
#define BLT_SUBTYPE     (23) /* Biblatex entrysubtype */
#define BLT_SKIP        (24) /* Biblatex Skip Entry */

typedef struct {
	char *oldstr;
	char *newstr;
	int  processingtype;
	int  level;
} lookups;

typedef struct {
	char    type[25];
	lookups *tags;
	int     ntags;
} variants;

extern int get_reftype( char *q, long refnum, char *progname, variants *all, int nall, char *tag );
extern int process_findoldtag( char *oldtag, int reftype, variants all[], int nall );
extern int translate_oldtag( char *oldtag, int reftype, variants all[], int nall, int *processingtype, int *level, char **newtag );



#endif
