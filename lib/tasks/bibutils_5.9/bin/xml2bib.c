/*
 * xml2bib.c
 *
 * Copyright (c) Chris Putnam 2003-2016
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

const char progname[] = "xml2bib";

void
help( char *progname )
{
	args_tellversion( progname );
	fprintf( stderr, "Converts the MODS XML intermediate reference file "
			"into Bibtex\n\n");

	fprintf(stderr,"usage: %s xml_file > bibtex_file\n\n",progname);
        fprintf(stderr,"  xml_file can be replaced with file list or omitted to use as a filter\n\n");

	fprintf(stderr,"  -h,  --help               display this help\n");
	fprintf(stderr,"  -v,  --version            display version\n");
	fprintf(stderr,"  -at, --abbreviatedtitles  use abbreviated titles, if available\n");
	fprintf(stderr,"  -fc, --finalcomma         add final comman to bibtex output\n");
	fprintf(stderr,"  -sd, --singledash         use one dash '-', not two '--', in page ranges\n" );
	fprintf(stderr,"  -b,  --brackets           use brackets, not quotation marks surrounding data\n");
	fprintf(stderr,"  -w,  --whitespace         use beautifying whitespace to output\n");
	fprintf(stderr,"  -sk, --strictkey          use only alphanumeric characters for bibtex key\n");
	fprintf(stderr,"                            (overly strict, but useful for other programs)\n");
	fprintf(stderr,"  -nl, --no-latex           no latex encodings; put characters in directly\n");
	fprintf(stderr,"  -nb, --no-bom             do not write Byte Order Mark in UTF8 output\n");
	fprintf(stderr,"  -U,  --uppercase          write bibtex tags/types in upper case\n" );
	fprintf(stderr,"  -s,  --single-refperfile  one reference per output file\n");
	fprintf(stderr,"  -i, --input-encoding      interpret input file with requested character set\n" );
	fprintf(stderr,"                            (use argument for current list)\n");
	fprintf(stderr,"  -o, --output-encoding     write output file with requested character set\n" );
	fprintf(stderr,"                            (use argument for current list)\n");
	fprintf(stderr,"  --verbose                 for verbose\n" );
	fprintf(stderr,"  --debug                   for debug output\n" );
	fprintf(stderr,"\n");

	fprintf(stderr,"Citation codes generated from <REFNUM> tag.   See \n");
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
		} else if ( args_match( argv[i], "-fc", "--finalcomma" ) ) {
			p->format_opts |= BIBL_FORMAT_BIBOUT_FINALCOMMA;
			subtract = 1;
		} else if ( args_match( argv[i], "-s", "--single-refperfile" )){
			p->singlerefperfile = 1;
			subtract = 1;
		} else if ( args_match( argv[i], "-sd", "--singledash" ) ) {
			p->format_opts |= BIBL_FORMAT_BIBOUT_SINGLEDASH;
			subtract = 1;
		} else if ( args_match( argv[i], "-b", "--brackets" ) ) {
			p->format_opts |= BIBL_FORMAT_BIBOUT_BRACKETS;
			subtract = 1;
		} else if ( args_match( argv[i], "-w", "--whitespace" ) ) {
			p->format_opts |= BIBL_FORMAT_BIBOUT_WHITESPACE;
			subtract = 1;
		} else if ( args_match( argv[i], "-sk", "--strictkey" ) ) {
			p->format_opts |= BIBL_FORMAT_BIBOUT_STRICTKEY;
			subtract = 1;
		} else if ( args_match( argv[i], "-U", "--uppercase" ) ) {
			p->format_opts |= BIBL_FORMAT_BIBOUT_UPPERCASE;
			subtract = 1;
		} else if ( args_match( argv[i], "-at", "--abbreviated-titles" ) ) {
			p->format_opts |= BIBL_FORMAT_BIBOUT_SHORTTITLE;
			subtract = 1;
		} else if ( args_match( argv[i], "-nl", "--no-latex" ) ) {
			p->latexout = 0;
			subtract = 1;
		} else if ( args_match( argv[i], "-nb", "--no-bom" ) ) {
			p->utf8bom = 0;
			subtract = 1;
		} else if ( args_match( argv[i], "-d", "--drop-key" ) ) {
			p->format_opts |= BIBL_FORMAT_BIBOUT_DROPKEY;
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
			if ( argv[i][0]=='-' ) fprintf( stderr, "Warning did not recognize potential command-line option %s\n", argv[i] );
			i++;
		}
	}
}

int 
main( int argc, char *argv[] )
{
	param p;
	modsin_initparams( &p, progname );
	bibtexout_initparams( &p, progname );
	process_charsets( &argc, argv, &p );
	process_args( &argc, argv, &p );
	bibprog( argc, argv, &p );
	bibl_freeparams( &p );
	return EXIT_SUCCESS;
}
