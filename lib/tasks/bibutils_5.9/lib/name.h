/*
 * name.h
 *
 * mangle names w/ and w/o commas
 *
 * Copyright (c) Chris Putnam 2004-2016
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef NAME_H
#define NAME_H

#include "newstr.h"
#include "list.h"
#include "fields.h"

extern int  name_add( fields *info, char *tag, char *q, int level, list *asis, list *corps );
extern void name_build_withcomma( newstr *s, char *p );
extern int  name_parse( newstr *outname, newstr *inname, list *asis, list *corps );
extern int  name_addsingleelement( fields *info, char *tag, char *name, int level, int corp );
extern int  name_addmultielement( fields *info, char *tag, list *tokens, int begin, int end, int level );
extern int  name_findetal( list *tokens );

#endif

