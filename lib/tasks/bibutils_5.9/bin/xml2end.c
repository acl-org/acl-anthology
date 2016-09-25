/*
 * xml2end.c
 *
 * Copyright (c) Chris Putnam 2004-2016
 *
 * Program and source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include "bibutils.h"
#include "bibformats.h"
#include "args.h"
#include "bibprog.h"

const char progname[] = "xml2end";

void
help( char *progname )
{
	args_tellversion( progname );
	fprintf(stderr,"Converts an XML intermediate reference file into a pre-EndNote format\n\n");

	fprintf(stderr,"usage: %s xml_file > endnote_file\n\n",progname);
        fprintf(stderr,"  xml_file can be replaced with file list or omitted to use as a filter\n\n");

	fprintf(stderr,"  -h, --help     display this help\n");
	fprintf(stderr,"  -v, --version  display version\n\n");
	fprintf(stderr,"  -nb, --no-bom   do not write Byte Order Mark in UTF8 output\n");
	fprintf(stderr,"  -s, --single-refperfile one reference per output file\n");
	fprintf(stderr,"  -i, --input-encoding interpret input file with requested character set (use\n" );
	fprintf(stderr,"                       argument for current list)\n");
	fprintf(stderr,"  -o, --output-encoding interprest output file with requested character set\n" );
	fprintf(stderr,"  --verbose      for verbose output\n");
	fprintf(stderr,"  --debug        for debug output\n");

	fprintf(stderr,"http://sourceforge.net/p/bibutils/home/Bibutils for more details\n\n");
}

void
process_args( int *argc, char *argv[], param *p )
{
	int i, j, subtract;
	i = 1;
	while ( i<*argc ) {
		subtract = 0;
		if ( args_match( argv[i], "-h", "--help" ) ) {
			help( p->progname );
			exit( EXIT_SUCCESS );
		} else if ( args_match( argv[i], "-v", "--version" ) ) {
			args_tellversion( p->progname );
			exit( EXIT_SUCCESS );
		} else if ( args_match( argv[i], "-s", "--single-refperfile")){
			p->singlerefperfile = 1;
			subtract = 1;
		} else if ( args_match( argv[i], "-nb", "--no-bom" ) ) {
			p->utf8bom = 0;
			subtract = 1;
		} else if ( args_match( argv[i], "--verbose", "" ) ) {
			p->verbose = 1;
			subtract = 1;
		} else if ( args_match( argv[i], "--debug", "" ) ) {
			p->verbose = 3;
			subtract = 1;
		}
		if ( subtract ) {
			for ( j=i+subtract; j<*argc; ++j )
				argv[j-subtract] = argv[j];
			*argc -= subtract;
		} else {
			if ( argv[i][0]=='-' ) fprintf( stderr, "Warning: Did not recognize potential command-line argument %s\n", argv[i] );
			i++;
		}
	}
}

int 
main( int argc, char *argv[] )
{
	param p;
	modsin_initparams( &p, progname );
	endout_initparams( &p, progname );
	process_charsets( &argc, argv, &p );
	process_args( &argc, argv, &p );
	bibprog( argc, argv, &p );
	bibl_freeparams( &p );
	return EXIT_SUCCESS;
}

