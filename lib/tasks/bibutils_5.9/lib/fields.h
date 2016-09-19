/*
 * fields.h
 *
 * Copyright (c) Chris Putnam 2003-2016
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef FIELDS_H
#define FIELDS_H

#define FIELDS_OK     (1)
#define FIELDS_ERR    (0)

#define LEVEL_ANY    (-1)
#define LEVEL_MAIN    (0)
#define LEVEL_HOST    (1)
#define LEVEL_SERIES  (2)

#define LEVEL_ORIG (-2)

#include <stdarg.h>
#include "newstr.h"
#include "vplist.h"

typedef struct fields {
	newstr    *tag;
	newstr    *data;
	int       *used;
	int       *level;
	int       n;
	int       max;
} fields;

void    fields_init( fields *f );
fields *fields_new( void );
void    fields_free( fields *f );

#define FIELDS_CAN_DUP (0)
#define FIELDS_NO_DUPS (1)

#define fields_add( a, b, c, d )         _fields_add( a, b, c, d, FIELDS_NO_DUPS )
#define fields_add_can_dup( a, b, c, d ) _fields_add( a, b, c, d, FIELDS_CAN_DUP )
#define fields_add_tagsuffix( a, b, c, d, e )         _fields_add( a, b, c, d, e, FIELDS_NO_DUPS )
#define fields_add_tagsuffix_can_dup( a, b, c, d, e ) _fields_add( a, b, c, d, e, FIELDS_CAN_DUP )

int  _fields_add( fields *f, char *tag, char *data, int level, int mode );
int  _fields_add_tagsuffix( fields *f, char *tag, char *suffix,
		char *data, int level, int mode );

int  fields_maxlevel( fields *f );
void fields_clearused( fields *f );
void fields_setused( fields *f, int n );
int  fields_replace_or_add( fields *f, char *tag, char *data, int level );

int fields_num( fields *f );
int fields_used( fields *f, int n );
int fields_notag( fields *f, int n );
int fields_nodata( fields *f, int n );

int fields_match_level( fields *f, int n, int level );
int fields_match_tag( fields *f, int n, char *tag );
int fields_match_casetag( fields *f, int n, char *tag );
int fields_match_tag_level( fields *f, int n, char *tag, int level );
int fields_match_casetag_level( fields *f, int n, char *tag, int level );

void fields_report( fields *f, FILE *fp );

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

void *fields_tag( fields *f, int n, int mode );
void *fields_value( fields *f, int n, int mode );
int   fields_level( fields *f, int n );
 
int   fields_find( fields *f, char *searchtag, int level );

void *fields_findv( fields *f, int level, int mode, char *tag );
void *fields_findv_firstof( fields *f, int level, int mode, ... );

void  fields_findv_each( fields *f, int level, int mode, vplist *a, char *tag );
void  fields_findv_eachof( fields *f, int level, int mode, vplist *a, ... );

#endif
