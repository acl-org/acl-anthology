/*
 * adsout.h
 *
 * Copyright (c) Richard Mathar 2007-2013
 * Copyright (c) Chris Putnam 2007-2013
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef ADSOUT_H
#define ADSOUT_H

#include <stdio.h>
#include "bibutils.h"

extern void adsout_write( fields *info, FILE *fp, param *p,
		unsigned long refnum );
extern void adsout_writeheader( FILE *outptr, param *p );

extern void adsout_initparams( param *p, const char *progname );

#endif
