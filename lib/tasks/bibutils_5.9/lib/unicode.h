/*
 * unicode.h
 *
 * Copyright (c) Chris Putnam 2004-2016
 *
 * Program and source code released under the GPL version 2
 */
#ifndef UNICODE_H
#define UNICODE_H

#include "newstr.h"

#define UNICODE_SYMBOL    (1)
#define UNICODE_UPPER     (2) /* Uppercase letter */
#define UNICODE_LOWER     (4) /* Lowercase letter */
#define UNICODE_NUMBER    (8) /* Numeric character */
#define UNICODE_MIXEDCASE ( UNICODE_UPPER | UNICODE_LOWER )

extern unsigned short unicode_utf8_classify( char *p );
extern unsigned short unicode_utf8_classify_newstr( newstr *s );

#endif
