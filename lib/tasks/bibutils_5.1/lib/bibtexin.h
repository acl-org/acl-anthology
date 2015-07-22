/*
 * bibtexin.h
 *
 * Copyright (c) Chris Putnam 2003-2013
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef BIBTEXIN_H
#define BIBTEXIN_H

#include "newstr.h"
#include "list.h"
#include "fields.h"
#include "bibl.h"
#include "bibutils.h"
#include "reftypes.h"

extern int  bibtexin_convertf( fields *bibin, fields *info, int reftype, param *p, variants *all, int nall );
extern int  bibtexin_processf( fields *bibin, char *data, char *filename, long nref );
extern void bibtexin_cleanf( bibl *bin, param *p );
extern int  bibtexin_readf( FILE *fp, char *buf, int bufsize, int *bufpos, newstr *line, newstr *reference, int *fcharset );
extern int  bibtexin_typef( fields *bibin, char *filename, int nrefs,
        param *p, variants *all, int nall );
extern void bibtexin_initparams( param *p, const char *progname );


extern variants bibtex_all[];
extern int bibtex_nall;


#endif

