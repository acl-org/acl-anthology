/*
 * newstring_conv.h
 *
 * Copyright (c) Chris Putnam 1999-2016
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef NEWSTR_CONV_H
#define NEWSTR_CONV_H

#define NEWSTR_CONV_XMLOUT_FALSE    (0)
#define NEWSTR_CONV_XMLOUT_TRUE     (1)
#define NEWSTR_CONV_XMLOUT_ENTITIES (3)

#include "newstr.h"

extern int newstr_convert( newstr *s,
		int charsetin, int latexin, int utf8in, int xmlin, 
		int charsetout, int latexout, int utf8out, int xmlout );

#endif

