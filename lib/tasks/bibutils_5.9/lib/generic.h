/* generic.h
 *
 * Copyright (c) Chris Putnam 2016
 *
 * Source code released under GPL version 2
 *
 */
#ifndef GENERIC_H
#define GENERIC_H

#include "bibutils.h"

int generic_null( fields *bibin, newstr *intag, newstr *invalue, int level, param *pm, char *outtag, fields *bibout );
int generic_notes( fields *bibin, newstr *intag, newstr *invalue, int level, param *pm, char *outtag, fields *bibout );
int generic_pages( fields *bibin, newstr *intag, newstr *invalue, int level, param *pm, char *outtag, fields *bibout );
int generic_person( fields *bibin, newstr *intag, newstr *invalue, int level, param *pm, char *outtag, fields *bibout );
int generic_serialno( fields *bibin, newstr *intag, newstr *invalue, int level, param *pm, char *outtag, fields *bibout );
int generic_simple( fields *bibin, newstr *intag, newstr *invalue, int level, param *pm, char *outtag, fields *bibout );
int generic_skip( fields *bibin, newstr *intag, newstr *invalue, int level, param *pm, char *outtag, fields *bibout );
int generic_title( fields *bibin, newstr *intag, newstr *invalue, int level, param *pm, char *outtag, fields *bibout );

#endif
