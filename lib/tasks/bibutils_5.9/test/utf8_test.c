/*
 * utf8_test.c
 *
 * Copyright (c) 2012-2016
 *
 * Source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include "utf8.h"

char progname[] = "utf8_test";

int
test_utf8( void )
{
	unsigned char ubuf[512];
	char buf[512];
	unsigned int i, j, pos_out;
	int nc, pos, failed = 0;
	for ( i=0; i<1000000; ++i ) {
		nc = utf8_encode( i, ubuf );
		ubuf[ nc ] = '*';
		ubuf[ nc+1 ] = '\0';
		for ( pos=0; pos < nc+2; ++pos )
			buf[pos] = (char)ubuf[pos];
		pos_out = 0;
		j = utf8_decode( buf, &pos_out );
		if ( i != j ) {
			printf( "%s: Error test_utf8 mismatch, "
				"send %u got back %u\n", progname, i, j );
			failed = 1;
		}
		if ( buf[pos_out]!='*' ) {
			printf( "%s: Error test_utf8 bad ending pos, "
				"expect '*', got back '%c'\n", progname,
				buf[pos] );
		}
	}
	return failed;
}


int
main( int argc, char *argv[] )
{
	int failed = 0;
	failed += test_utf8();
	if ( !failed ) {
		printf( "%s: PASSED\n", progname );
		return EXIT_SUCCESS;
	} else {
		printf( "%s: FAILED\n", progname );
		return EXIT_FAILURE;
	}
}
