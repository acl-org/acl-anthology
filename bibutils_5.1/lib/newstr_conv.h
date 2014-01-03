/*
 * newstring_conv.h
 *
 * Copyright (c) Chris Putnam 1999-2013
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef NEWSTR_CONV_H
#define NEWSTR_CONV_H

#include "newstr.h"

extern int newstr_convert( newstr *s,
		int charsetin, int latexin, int utf8in, int xmlin, 
		int charsetout, int latexout, int utf8out, int xmlout );

#endif

