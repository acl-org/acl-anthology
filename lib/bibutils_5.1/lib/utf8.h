/*
 * utf8.h
 *
 * Copyright (c) Chris Putnam 2004-2013
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef UTF8_H
#define UTF8_H

#include <stdio.h>

extern int utf8_encode( unsigned int value, unsigned char out[6] );
extern void utf8_encode_str( unsigned int value, char outstr[7] );
extern unsigned int utf8_decode( char *s, unsigned int *pi );
extern void utf8_writebom( FILE *outptr );


#endif
