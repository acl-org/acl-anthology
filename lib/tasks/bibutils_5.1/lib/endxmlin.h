/*
 * endxmlin.h
 *
 * Copyright (c) Chris Putnam 2006-2013
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef ENDXMLIN_H
#define ENDXMLIN_H

#include "newstr.h"
#include "fields.h"
#include "reftypes.h"
#include "bibutils.h"

extern int endxmlin_readf( FILE *fp, char *buf, int bufsize, int *bufpos,
	newstr *line, newstr *reference, int *fcharset );
extern int endxmlin_processf( fields *endin, char *p, char *filename, long nref );

extern void endxmlin_initparams( param *p, const char *progname );

#endif
