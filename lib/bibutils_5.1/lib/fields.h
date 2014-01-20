/*
 * fields.h
 *
 * Copyright (c) Chris Putnam 2003-2013
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef FIELDS_H
#define FIELDS_H

#define LEVEL_ANY    (-1)
#define LEVEL_MAIN    (0)
#define LEVEL_HOST    (1)
#define LEVEL_SERIES  (2)

#define LEVEL_ORIG (-2)

#include <stdarg.h>
#include "newstr.h"
#include "vplist.h"

typedef struct {
	newstr    *tag;
	newstr    *data;
	int       *used;
	int       *level;
	int       n;
	int       max;
} fields;

extern void fields_init( fields *f );
extern fields *fields_new( void );
extern void fields_free( fields *f );

extern int  fields_add( fields *f, char *tag, char *data, int level );
extern int  fields_add_tagsuffix( fields *f, char *tag, char *suffix,
		char *data, int level );

extern int  fields_maxlevel( fields *f );
extern void fields_clearused( fields *f );
extern void fields_setused( fields *f, int n );
extern int  fields_replace_or_add( fields *f, char *tag, char *data, int level );

extern inline int fields_num( fields *f );
extern inline int fields_used( fields *f, int n );
extern inline int fields_nodata( fields *f, int n );
extern inline int fields_get_level( fields *f, int n );

extern inline int fields_match_level( fields *f, int n, int level );
extern inline int fields_match_tag( fields *f, int n, char *tag );
extern inline int fields_match_casetag( fields *f, int n, char *tag );
extern inline int fields_match_tag_level( fields *f, int n, char *tag, int level );
extern inline int fields_match_casetag_level( fields *f, int n, char *tag, int level );

#define FIELDS_STRP_FLAG     (2)
#define FIELDS_POSP_FLAG     (4)
#define FIELDS_NOLENOK_FLAG  (8)
#define FIELDS_SETUSE_FLAG  (16)

#define FIELDS_CHRP        (FIELDS_SETUSE_FLAG                                         )
#define FIELDS_STRP        (FIELDS_SETUSE_FLAG | FIELDS_STRP_FLAG                      )
#define FIELDS_POSP        (FIELDS_SETUSE_FLAG | FIELDS_POSP_FLAG                      )
#define FIELDS_CHRP_NOLEN  (FIELDS_SETUSE_FLAG |                    FIELDS_NOLENOK_FLAG)
#define FIELDS_STRP_NOLEN  (FIELDS_SETUSE_FLAG | FIELDS_STRP_FLAG | FIELDS_NOLENOK_FLAG)
#define FIELDS_POSP_NOLEN  (FIELDS_SETUSE_FLAG | FIELDS_POSP_FLAG | FIELDS_NOLENOK_FLAG)
#define FIELDS_CHRP_NOUSE  (                            0                              )
#define FIELDS_STRP_NOUSE  (                     FIELDS_STRP_FLAG                      )

extern void *fields_tag( fields *f, int n, int mode );
extern void *fields_value( fields *f, int n, int mode );
extern int   fields_level( fields *f, int n );
 
extern int   fields_find( fields *f, char *searchtag, int level );

extern void *fields_findv( fields *f, int level, int mode, char *tag );
extern void *fields_findv_firstof( fields *f, int level, int mode, ... );

extern void  fields_findv_each( fields *f, int level, int mode, vplist *a, char *tag );
extern void  fields_findv_eachof( fields *f, int level, int mode, vplist *a, ... );

#endif
