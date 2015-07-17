/*
 * biblatexin.h
 *
 * Copyright (c) Chris Putnam 2008-2013
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef BIBLATEXIN_H
#define BIBLATEXIN_H

#include "newstr.h"
#include "list.h"
#include "fields.h"
#include "bibl.h"
#include "bibutils.h"
#include "reftypes.h"

extern int  biblatexin_convertf( fields *bibin, fields *info, int reftype, param *p, variants *all, int nall );
extern int  biblatexin_processf( fields *bibin, char *data, char *filename, long nref );
extern void biblatexin_cleanf( bibl *bin, param *p );
extern int  biblatexin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset );
extern int  biblatexin_typef( fields *bibin, char *filename, int nrefs,
        param *p, variants *all, int nall );

extern void biblatexin_initparams( param *p, const char *progname );

extern variants biblatex_all[];
extern int biblatex_nall;


#endif

