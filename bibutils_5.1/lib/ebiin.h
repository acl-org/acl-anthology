/*
 * ebiin.h
 *
 * Copyright (c) Chris Putnam 2004-2013
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef PUBIN_H
#define PUBIN_H

#include "newstr.h"
#include "fields.h"
#include "reftypes.h"
#include "bibutils.h"

extern int ebiin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset );
extern int ebiin_processf( fields *ebiin, char *data, char *filename, long nref );

extern void ebiin_initparams( param *p, const char *progname );


extern variants med_all[];
extern int med_nall;

#endif

