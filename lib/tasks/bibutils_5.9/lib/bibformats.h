/*
 * bibformats.h
 *
 * Copyright (c) Chris Putnam 2007-2016
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef BIBFORMATS_H
#define BIBFORMATS_H

#include "bibutils.h"

void adsout_initparams(     param *p, const char *progname );
void biblatexin_initparams( param *p, const char *progname );
void bibtexin_initparams(   param *p, const char *progname );
void bibtexout_initparams(  param *p, const char *progname );
void copacin_initparams(    param *p, const char *progname );
void ebiin_initparams(      param *p, const char *progname );
void endin_initparams(      param *p, const char *progname );
void endout_initparams(     param *p, const char *progname );
void endxmlin_initparams(   param *p, const char *progname );
void isiin_initparams(      param *p, const char *progname );
void isiout_initparams(     param *p, const char *progname );
void medin_initparams(      param *p, const char *progname );
void modsin_initparams(     param *p, const char *progname );
void modsout_initparams(    param *p, const char *progname );
void risin_initparams(      param *p, const char *progname );
void risout_initparams(     param *p, const char *progname );
void wordin_initparams(     param *p, const char *progname );
void wordout_initparams(    param *p, const char *progname );

#endif

