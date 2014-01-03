/*
 * modsin.h
 *
 * Copyright (c) Chris Putnam 2004-2013
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef MODSIN_H
#define MODSIN_H

#include "newstr.h"
#include "fields.h"
#include "reftypes.h"

extern int modsin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset );
extern int modsin_processf( fields *medin, char *data, char *filename, long nref );
extern void modsin_initparams( param *p, const char *progname );

#endif
