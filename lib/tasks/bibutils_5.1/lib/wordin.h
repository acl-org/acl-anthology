/*
 * wordin.h
 *
 * Copyright (c) Chris Putnam 2009-2013
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef WORDIN_H
#define WORDIN_H

#include "newstr.h"
#include "fields.h"
#include "reftypes.h"
#include "bibutils.h"

extern int wordin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset );
extern int wordin_processf( fields *wordin, char *data, char *filename, long nref );

extern void wordin_initparams( param *p, const char *progname );

#endif

