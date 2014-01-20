/*
 * medin.h
 *
 * Copyright (c) Chris Putnam 2004-2013
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef MEDIN_H
#define MEDIN_H

#include "newstr.h"
#include "fields.h"
#include "reftypes.h"
#include "bibutils.h"

extern int medin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset );
extern int medin_processf( fields *medin, char *data, char *filename, long nref );

extern void medin_initparams( param *p, const char *progname );

extern variants med_all[];
extern int med_nall;

#endif

