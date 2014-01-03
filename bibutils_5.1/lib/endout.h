/*
 * endout.h
 *
 * Copyright (c) Chris Putnam 2005-2013
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef ENDOUT_H
#define ENDOUT_H

#include <stdio.h>
#include "bibutils.h"

extern void endout_write( fields *info, FILE *fp, param *p, 
		unsigned long refnum );
extern void endout_writeheader( FILE *outptr, param *p );

extern void endout_initparams( param *p, const char *progname );


#endif
