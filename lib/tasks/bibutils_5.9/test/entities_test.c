/*
 * entities_test.c
 *
 * Copyright (c) 2012-2016
 *
 * Source code released under the GPL version 2
 */
#include <stdio.h>
#include <stdlib.h>
#include "entities.h"

char progname[] = "entities_test";
char version[] = "0.1";

int
test_decimal_entities1( void )
{
	unsigned int i, answer, pos_in;
	int failed = 0, err, unicode = 0;
	char buf[512];
	for ( i=0; i<10000; ++i ) {
		pos_in = 0;
		err = 0;
		sprintf( buf, "&#%u;*", i );
		answer = decode_entity( buf, &pos_in, &unicode, &err );
		if ( err ) {
			failed = 1;
			printf("%s: Error test_decimal_entities received "
				"error, sent '%s' returned %u\n", 
				progname, buf, answer );
		}
		if ( answer!=i ) {
			failed = 1;
			printf("%s: Error test_decimal_entities mismatch, "
				"sent '%s' returned %u\n", 
				progname, buf, answer );
		}
		if ( buf[pos_in]!='*' ) {
			failed = 1;
			printf("%s: Error test_decimal_entities bad ending pos,"
				"sent '%s' returned pointer to '%s'\n",
				progname, buf, &(buf[pos_in]) );
		}
	}
	return failed;
}

int
test_decimal_entities2( void )
{
	unsigned int i, answer, pos_in;
	int failed = 0, err, unicode = 0;
	char buf[512];
	for ( i=0; i<10000; ++i ) {
		pos_in = 1;
		err = 0;
		sprintf( buf, "&#%u;*", i );
		answer = decode_entity( buf, &pos_in, &unicode, &err );
		if ( !err ) {
			failed = 1;
			printf("%s: Error test_decimal_entities should have "
				"received error, sent '%s' returned %u\n", 
				progname, &(buf[1]), answer );
		}
	}
	for ( i=0; i<1000; ++i ) {
		pos_in = 0;
		err = 0;
		sprintf( buf, "&#%u ;", i );
		answer = decode_entity( buf, &pos_in, &unicode, &err );
		if ( !err ) {
			failed = 1;
			printf("%s: Error test_decimal_entities should have "
				"received error, sent '%s' returned %u\n", 
				progname, buf, answer );
		}
	}
	return failed;
}

int
test_hex_entities( void )
{
	unsigned int i, answer, pos_in;
	int failed = 0, err, unicode = 0;
	char buf[512];
	for ( i=0; i<10000; ++i ) {
		pos_in = 0;
		err = 0;
		sprintf( buf, "&#x%x;*", i );
		answer = decode_entity( buf, &pos_in, &unicode, &err );
		if ( err ) {
			failed = 1;
			printf("%s: Error test_hex_entities received error, "
				"sent '%s' = %u returned %u\n", 
				progname, buf, i, answer );
		}
		if ( answer!=i ) {
			failed = 1;
			printf("%s: Error test_hex_entities mismatch, "
				"sent '%s' = %u returned %u\n", 
				progname, buf, i, answer );
		}
		if ( buf[pos_in]!='*' ) {
			failed = 1;
			printf("%s: Error test_decimal_entities bad ending pos,"
				"sent '%s' returned pointer to '%s'\n",
				progname, buf, &(buf[pos_in]) );
		}
	}
	return failed;
}

int
main( int argc, char *argv[] )
{
	int failed = 0;
	failed += test_decimal_entities1();
	failed += test_decimal_entities2();
	failed += test_hex_entities();
	if ( !failed ) {
		printf( "%s: PASSED\n", progname );
		return EXIT_SUCCESS;
	} else {
		printf( "%s: FAILED\n", progname );
		return EXIT_FAILURE;
	}
}

