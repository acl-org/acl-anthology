/*
 * bibcore.c
 *
 * Copyright (c) Chris Putnam 2005-2013
 *
 * Source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include "bibutils.h"

/* internal includes */
#include "reftypes.h"
#include "charsets.h"
#include "newstr_conv.h"
#include "is_ws.h"

/* illegal modes to pass in, but use internally for consistency */
#define BIBL_INTERNALIN   (BIBL_LASTIN+1)
#define BIBL_INTERNALOUT  (BIBL_LASTOUT+1)

#define debug_set( p ) ( p->verbose > 1 )
#define verbose_set( p ) ( p->verbose )

static void
report_params( FILE *fp, const char *f, param *p )
{
	fprintf( fp, "-------------------params start for %s\n", f );
	fprintf( fp, "\tprogname='%s'\n\n", p->progname );

	fprintf( fp, "\treadformat=%d", p->readformat );
	switch ( p->readformat ) {
		case BIBL_INTERNALIN:   fprintf( fp, " (BIBL_INTERNALIN)\n" );   break;
		case BIBL_MODSIN:       fprintf( fp, " (BIBL_MODSIN)\n" );       break;
		case BIBL_BIBTEXIN:     fprintf( fp, " (BIBL_BIBTEXIN)\n" );     break;
		case BIBL_RISIN:        fprintf( fp, " (BIBL_RISIN)\n" );        break;
		case BIBL_ENDNOTEIN:    fprintf( fp, " (BIBL_ENDNOTEIN)\n" );    break;
		case BIBL_COPACIN:      fprintf( fp, " (BIBL_COPACIN)\n" );      break;
		case BIBL_ISIIN:        fprintf( fp, " (BIBL_ISIIN)\n" );        break;
		case BIBL_MEDLINEIN:    fprintf( fp, " (BIBL_MEDLINEIN)\n" );    break;
		case BIBL_ENDNOTEXMLIN: fprintf( fp, " (BIBL_ENDNOTEXMLIN)\n" ); break;
		case BIBL_BIBLATEXIN:   fprintf( fp, " (BIBL_BIBLATEXIN)\n" );   break;
		case BIBL_EBIIN:        fprintf( fp, " (BIBL_EBIIN)\n" );        break;
		case BIBL_WORDIN:       fprintf( fp, " (BIBL_WORDIN)\n" );       break;
		default:                fprintf( fp, " (Illegal)\n" );           break;
	}
	fprintf( fp, "\tcharsetin=%d\n", p->charsetin );
/*	fprintf( fp, "\tcharsetin=%d (%s)\n", p->charsetin, get_charsetname( p->charsetin ) );*/
	fprintf( fp, "\tcharsetin_src=%d", p->charsetin_src );
	switch ( p->charsetin_src ) {
		case 0:  fprintf( fp, " (BIBL_SRC_DEFAULT)\n" ); break;
		case 1:  fprintf( fp, " (BIBL_SRC_FILE)\n" );    break;
		case 2:  fprintf( fp, " (BIBL_SRC_USER)\n" );    break;
		default: fprintf( fp, " (Illegal value!)\n" );   break;
	}
	fprintf( fp, "\tutf8in=%d\n", p->utf8in );
	fprintf( fp, "\tlatexin=%d\n", p->latexin );
	fprintf( fp, "\txmlin=%d\n\n", p->xmlin );

	fprintf( fp, "\twriteformat=%d", p->writeformat );
	switch ( p->writeformat ) {
		case BIBL_INTERNALOUT:  fprintf( fp, " (BIBL_INTERNALOUT)\n" );  break;
		case BIBL_MODSOUT:      fprintf( fp, " (BIBL_MODSOUT)\n" );      break;
		case BIBL_BIBTEXOUT:    fprintf( fp, " (BIBL_BIBTEXOUT)\n" );    break;
		case BIBL_RISOUT:       fprintf( fp, " (BIBL_RISOUT)\n" );       break;
		case BIBL_ENDNOTEOUT:   fprintf( fp, " (BIBL_ENDNOTEOUT)\n" );   break;
		case BIBL_ISIOUT:       fprintf( fp, " (BIBL_ISIOUT)\n" );       break;
		case BIBL_WORD2007OUT:  fprintf( fp, " (BIBL_WORD2007OUT)\n" );  break;
		case BIBL_ADSABSOUT:    fprintf( fp, " (BIBL_ADSABSOUT)\n" );    break;
		default:                fprintf( fp, " (Illegal)\n" );           break;
	}
/*	fprintf( fp, "\tcharsetout=%d (%s)\n", p->charsetout, get_charsetname( p->charsetout ) );*/
	fprintf( fp, "\tcharsetout=%d\n", p->charsetout );
	fprintf( fp, "\tcharsetout_src=%d", p->charsetout_src );
	switch ( p->charsetout_src ) {
		case 0:  fprintf( fp, " (BIBL_SRC_DEFAULT)\n" ); break;
		case 1:  fprintf( fp, " (BIBL_SRC_FILE)\n" );    break;
		case 2:  fprintf( fp, " (BIBL_SRC_USER)\n" );    break;
		default: fprintf( fp, " (Illegal value!)\n" );   break;
	}
	fprintf( fp, "\tutf8out=%d\n", p->utf8out );
	fprintf( fp, "\tutf8bom=%d\n", p->utf8bom );
	fprintf( fp, "\tlatexout=%d\n", p->latexout );
	fprintf( fp, "\txmlout=%d\n", p->xmlout );
	fprintf( fp, "-------------------params end for %s\n", f );

	fflush( fp );
}

static void
bibl_duplicateparams( param *np, param *op )
{
	list_init( &(np->asis) );
	list_init( &(np->corps) );
	list_copy( &(np->asis), &(op->asis ) );
	list_copy( &(np->corps), &(op->corps ) );
	
	if ( !op->progname ) np->progname = NULL;
	else np->progname = strdup( op->progname );

	np->readformat = op->readformat;
	np->writeformat = op->writeformat;

	np->charsetin = op->charsetin;
	np->charsetin_src = op->charsetin_src;
	np->utf8in = op->utf8in;
	np->latexin = op->latexin;
	np->xmlin = op->xmlin;

	np->charsetout = op->charsetout;
	np->charsetout_src = op->charsetout_src;
	np->utf8out = op->utf8out;
	np->utf8bom = op->utf8bom;
	np->latexout = op->latexout;
	np->xmlout = op->xmlout;
	np->nosplittitle = op->nosplittitle;

	np->verbose = op->verbose;
	np->format_opts = op->format_opts;
	np->addcount = op->addcount;
	np->output_raw = op->output_raw;
	np->singlerefperfile = op->singlerefperfile;

	np->readf = op->readf;
	np->processf = op->processf;
	np->cleanf = op->cleanf;
	np->typef = op->typef;
	np->convertf = op->convertf;
	np->headerf = op->headerf;
	np->footerf = op->footerf;
	np->writef = op->writef;
	np->all = op->all;
	np->nall = op->nall;

}

static void
bibl_setreadparams( param *np, param *op )
{
	bibl_duplicateparams( np, op );
	np->utf8out = 1;
	np->charsetout = BIBL_CHARSET_UNICODE;
	np->charsetout_src = BIBL_SRC_DEFAULT;
	np->xmlout = 0;
	np->latexout = 0;
	np->writeformat = BIBL_INTERNALOUT;
}

static void
bibl_setwriteparams( param *np, param *op )
{
	bibl_duplicateparams( np, op );
	np->xmlin = 0;
	np->latexin = 0;
	np->utf8in = 1;
	np->charsetin = BIBL_CHARSET_UNICODE;
	np->charsetin_src = BIBL_SRC_DEFAULT;
	np->readformat = BIBL_INTERNALIN;
}

void
bibl_freeparams( param *p )
{
	list_free( &(p->asis) );
	list_free( &(p->corps) );
	if ( p->progname ) free( p->progname );
}

static void
bibl_readlist( list *pl, char *progname, char *filename )
{
	if ( !list_fill( pl, filename ) ) {
		fprintf( stderr, "%s: warning problems reading '%s' "
			"obtained %d elements\n", progname, filename,
			pl->n );
	}
}

void
bibl_readasis( param *p, char *filename )
{
	bibl_readlist( &(p->asis), p->progname, filename );
}

void
bibl_readcorps( param *p, char *filename )
{
	bibl_readlist( &(p->corps), p->progname, filename );
}

static void
bibl_addtolist( list *pl, char *entry )
{
	list_add( pl, entry );
}

void
bibl_addtoasis( param *p, char *entry )
{
	bibl_addtolist( &(p->asis), entry );
}

void
bibl_addtocorps( param *p, char *entry )
{
	bibl_addtolist( &(p->corps), entry );
}

void
bibl_reporterr( int err )
{
	fprintf( stderr, "Bibutils: " );
	switch( err ) {
		case BIBL_OK:
			fprintf( stderr, "No error." ); break;
		case BIBL_ERR_BADINPUT:
			fprintf( stderr, "Bad input." ); break;
		case BIBL_ERR_MEMERR:
			fprintf( stderr, "Memory error." ); break;
		case BIBL_ERR_CANTOPEN:
			fprintf( stderr, "Can't open." ); break;
		default:
			fprintf( stderr, "Cannot identify error code."); break;
	}
	fprintf( stderr, "\n" );
}

static int
bibl_illegalinmode( int mode )
{
	if ( mode < BIBL_FIRSTIN || mode > BIBL_LASTIN ) return 1;
	else return 0;
}

static int
bibl_illegaloutmode( int mode )
{
	if ( mode < BIBL_FIRSTOUT || mode > BIBL_LASTOUT ) return 1;
	else return 0;
}

void
bibl_verbose2( fields *f, char *filename, long nrefs )
{
	int i, n;
	n = fields_num( f );
	fprintf( stderr, "======== %s %ld : converted\n", filename, nrefs );
	for ( i=0; i<n; ++i ) {
		fprintf( stderr, "'%s'='%s' level=%d\n",
			(char*) fields_tag( f, i, FIELDS_CHRP_NOUSE ),
			(char*) fields_value( f, i, FIELDS_CHRP_NOUSE ),
			fields_level( f, i ) );
	}
	fprintf( stderr, "\n" );
	fflush( stderr );
}

void
bibl_verbose1( fields *f, fields *orig, char *filename, long nrefs )
{
	int i, n;
	n = fields_num( orig );
	fprintf( stderr, "======== %s %ld : processed\n", filename, nrefs );
	for ( i=0; i<n; ++i ) {
		fprintf( stderr, "'%s'='%s' level=%d\n",
			(char*) fields_tag( orig, i, FIELDS_CHRP_NOUSE ),
			(char*) fields_value( orig, i, FIELDS_CHRP_NOUSE ),
			fields_level( orig, i ) );
	}
	if ( f ) bibl_verbose2( f, filename, nrefs );
}

void
bibl_verbose0( bibl *bin )
{
	int i;
	for ( i=0; i<bin->nrefs; ++i )
		bibl_verbose2( bin->ref[i], "", i+1 );
}

/* extract_tag_value
 *
 * Extract the tag and the value for ALWAYS/DEFAULT
 * entries like: "NGENRE|Masters thesis"
 *
 * tag = "NGENRE"
 * value = "Masters thesis"
 */
static void
extract_tag_value( newstr *tag, newstr *value, char *p )
{
	newstr_empty( tag );
	while ( p && *p && *p!='|' ) {
		newstr_addchar( tag, *p );
		p++;
	}
	if ( p && *p=='|' ) p++;
	newstr_empty( value );
	while ( p && *p ) {
		newstr_addchar( value, *p );
		p++;
	}
}

/* process_defaultadd()
 *
 * Add tag/value pairs that have "DEFAULT" processing
 * unless a tag/value pair with the same tag has already
 * been adding during reference processing.
 */
static int
process_defaultadd( fields *f, int reftype, param *r )
{
	int i, n, process, level, ok = 1;
	newstr tag, value;
	char *p;

	newstrs_init( &tag, &value, NULL );

	for ( i=0; i<r->all[reftype].ntags; ++i ) {
		process = ((r->all[reftype]).tags[i]).processingtype;
		if ( process!=DEFAULT ) continue;
		level   = ((r->all[reftype]).tags[i]).level;
		p       = ((r->all[reftype]).tags[i]).newstr;
		extract_tag_value( &tag, &value, p );
		n = fields_find( f, tag.data, level );
		if ( n==-1 ) {
			ok = fields_add( f, tag.data, value.data, level );
			if ( !ok ) goto out;
		}
	}
out:
	newstrs_free( &tag, &value, NULL );

	if ( ok ) return BIBL_OK;
	else return BIBL_ERR_MEMERR;
}

/* process_alwaysadd()
 *
 * Add tag/value pair to reference from the ALWAYS 
 * processing type without exception (the difference from
 * DEFAULT processing).
 */
static int
process_alwaysadd( fields *f, int reftype, param *r )
{
	int i, process, level, ok = 1;
	newstr tag, value;
	char *p;

	newstrs_init( &tag, &value, NULL );

	for ( i=0; i<r->all[reftype].ntags; ++i ) {
		process = ((r->all[reftype]).tags[i]).processingtype;
		if ( process!=ALWAYS ) continue;
		level   = ((r->all[reftype]).tags[i]).level;
		p = ((r->all[reftype]).tags[i]).newstr;
		extract_tag_value( &tag, &value, p );
		ok = fields_add( f, tag.data, value.data, level );
		if ( !ok ) goto out;
	}

out:
	newstrs_free( &tag, &value, NULL );

	if ( ok ) return BIBL_OK;
	else return BIBL_ERR_MEMERR;
}

static int
read_ref( FILE *fp, bibl *bin, char *filename, param *p )
{
	int nrefs = 0, bufpos = 0, ok, ret=BIBL_OK, fcharset;/* = CHARSET_UNKNOWN;*/
	newstr reference, line;
	char buf[256]="";
	fields *ref;
	newstr_init( &reference );
	newstr_init( &line );
	while ( p->readf( fp, buf, sizeof(buf), &bufpos, &line, &reference, &fcharset ) ) {
		if ( reference.len==0 ) continue;
		ref = fields_new();
		if ( !ref ) {
			ret = BIBL_ERR_MEMERR;
			bibl_free( bin );
			goto out0;
		}
		if ( p->processf( ref, reference.data, filename, nrefs+1 )){
			ok = bibl_addref( bin, ref );
			if ( !ok ) {
				ret = BIBL_ERR_MEMERR;
				bibl_free( bin );
				fields_free( ref );
				free( ref );
				goto out0;
			}
		} else {
			fields_free( ref );
			free( ref );
		}
		newstr_empty( &reference );
		if ( fcharset!=CHARSET_UNKNOWN ) {
			/* charset from file takes priority over default, but
			 * not user-specified */
			if ( p->charsetin_src!=BIBL_SRC_USER ) {
				p->charsetin_src = BIBL_SRC_FILE;
				p->charsetin = fcharset;
				if ( fcharset!=CHARSET_UNICODE ) p->utf8in = 0;
			}
		}
	}
	if ( p->charsetin==CHARSET_UNICODE ) p->utf8in = 1;
out0:
	newstr_free( &line );
	newstr_free( &reference );
	return ret;
}

/* Don't manipulate latex for URL's and the like */
static int
bibl_notexify( char *tag )
{
	char *protected[] = { "DOI", "URL", "REFNUM" };
	int i, nprotected = sizeof( protected ) / sizeof( protected[0] );
	for ( i=0; i<nprotected; ++i )
		if ( !strcasecmp( tag, protected[i] ) ) return 1;
	return 0;
}

static int
bibl_fixcharsetfields( fields *ref, param *p )
{
	newstr *data;
	char *tag;
	long i, n;
	int ok;

	n = fields_num( ref );

	for ( i=0; i<n; ++i ) {

		tag  = fields_tag( ref, i, FIELDS_CHRP_NOUSE );
		data = fields_value( ref, i, FIELDS_STRP_NOUSE );

		if ( bibl_notexify( tag ) ) {
			ok = newstr_convert( data,
				p->charsetin,  0, p->utf8in,  p->xmlin,
				p->charsetout, 0, p->utf8out, p->xmlout );
		} else {
			ok = newstr_convert( data,
				p->charsetin,  p->latexin,  p->utf8in,  p->xmlin,
				p->charsetout, p->latexout, p->utf8out, p->xmlout );
		}

		if ( !ok ) return 0;
	}

	return 1;
}

static int
bibl_fixcharsets( bibl *b, param *p )
{
	long i;
	int ok;
	for ( i=0; i<b->nrefs; ++i ) {
		ok = bibl_fixcharsetfields( b->ref[i], p );
		if ( !ok ) return 0;
	}
	return 1;
}

static int
build_refnum( fields *f, long nrefs )
{
	char *year, *author, *p, num[512];
	newstr refnum;

	newstr_init( &refnum );

	year = fields_findv( f, LEVEL_MAIN, FIELDS_CHRP_NOUSE, "YEAR" );
	if ( !year )
		year = fields_findv_firstof( f, LEVEL_ANY, FIELDS_CHRP_NOUSE,
			"YEAR", "PARTYEAR", NULL );

	author = fields_findv( f, LEVEL_MAIN, FIELDS_CHRP_NOUSE, "AUTHOR" );
	if ( !author )
		author = fields_findv_firstof( f, LEVEL_ANY, FIELDS_CHRP_NOUSE,
			"AUTHOR", "AUTHOR:CORP", "AUTHOR:ASIS", NULL );

	if ( year && author ) {
		p = author;
		while ( *p && *p!='|' )
			newstr_addchar( &refnum, *p++ );
		p = year;
		while ( *p && *p!=' ' && *p!='\t' )
			newstr_addchar( &refnum, *p++ );
	} else {
		sprintf( num, "%ld", nrefs );
		newstr_mergestrs( &refnum, "ref", num, NULL );
	}

	fields_add( f, "REFNUM", refnum.data, 0 );
	newstr_free( &refnum );

	return fields_find( f, "REFNUM", 0 );
}

static void
bibl_checkrefid( bibl *b, param *p )
{
	fields *ref;
	long i;
	char buf[512];
	int n;
	for ( i=0; i<b->nrefs; ++i ) {
		ref = b->ref[i];
		n = fields_find( ref, "REFNUM", 0 );
		if ( n==-1 ) n = build_refnum( ref, i+1 );
		if ( p->addcount ) {
			sprintf( buf, "_%ld", i+1 );
			newstr_strcat( &(ref->data[n]), buf );
		}
	}
}

static int
generate_citekey( fields *f, int nref )
{
	newstr citekey;
	int n1, n2;
	char *p, buf[100];
	newstr_init( &citekey );
	n1 = fields_find( f, "AUTHOR", 0 );
	if ( n1==-1 ) n1 = fields_find( f, "AUTHOR", -1 );
	n2 = fields_find( f, "YEAR", 0 );
	if ( n2==-1 ) n2 = fields_find( f, "YEAR", -1 );
	if ( n2==-1 ) n2 = fields_find( f, "PARTYEAR", 0 );
	if ( n2==-1 ) n2 = fields_find( f, "PARTYEAR", -1 );
	if ( n1!=-1 && n2!=-1 ) {
		p = f->data[n1].data;
		while ( p && *p && *p!='|' ) {
			if ( !is_ws( *p ) ) newstr_addchar( &citekey, *p ); 
			p++;
		}
		p = f->data[n2].data;
		while ( p && *p ) {
			if ( !is_ws( *p ) ) newstr_addchar( &citekey, *p );
			p++;
		}
		fields_add( f, "REFNUM", citekey.data, 0 );
	} else {
		sprintf( buf, "ref%d\n", nref );
		newstr_strcpy( &citekey, buf );
	}
	newstr_free( &citekey );
	return fields_find( f, "REFNUM", -1 );
}

static void
resolve_citekeys( bibl *b, list *citekeys, int *dup )
{
	char abc[]="abcdefghijklmnopqrstuvwxyz";
	newstr tmp;
	int nsame, ntmp, n, i, j;

	newstr_init( &tmp );

	for ( i=0; i<citekeys->n; ++i ) {
		if ( dup[i]==-1 ) continue;
		nsame = 0;
		for ( j=i; j<citekeys->n; ++j ) {
			if ( dup[j]!=i ) continue;
			newstr_newstrcpy( &tmp, &(citekeys->str[j]) );
			ntmp = nsame;
			while ( ntmp >= 26 ) {
				newstr_addchar( &tmp, 'a' );
					ntmp -= 26;
			}
			if ( ntmp<26 && ntmp>=0 )
			newstr_addchar( &tmp, abc[ntmp] );
			nsame++;
			dup[j] = -1;
			n = fields_find( b->ref[j], "REFNUM", -1 );
			if ( n!=-1 )
				newstr_newstrcpy(&((b->ref[j])->data[n]),&tmp);
		}
	}
	newstr_free( &tmp );
}

static void
get_citekeys( bibl *b, list *citekeys )
{
	fields *f;
	int i, n;
	for ( i=0; i<b->nrefs; ++i ) {
		f = b->ref[i];
		n = fields_find( f, "REFNUM", -1 );
		if ( n==-1 ) n = generate_citekey( f, i );
		if ( n!=-1 && f->data[n].data )
			list_add( citekeys, f->data[n].data );
		else
			list_add( citekeys, "" );
	}
}

static int 
dup_citekeys( bibl *b, list *citekeys )
{
	int i, j, *dup, ndup=0;
	dup = ( int * ) malloc( sizeof( int ) * citekeys->n );
	if ( !dup ) return 0;
	for ( i=0; i<citekeys->n; ++i ) dup[i] = -1;
	for ( i=0; i<citekeys->n-1; ++i ) {
		if ( dup[i]!=-1 ) continue;
		for ( j=i+1; j<citekeys->n; ++j ) {
			if ( !strcmp( citekeys->str[i].data, 
				citekeys->str[j].data ) ) {
					dup[i] = i;
					dup[j] = i;
					ndup++;
			}
		}
	}
	if ( ndup ) resolve_citekeys( b, citekeys, dup );
	free( dup );
	return ndup;
}

static void
uniqueify_citekeys( bibl *b )
{
	list citekeys;
	list_init( &citekeys );
	get_citekeys( b, &citekeys );
	dup_citekeys( b, &citekeys );
	list_free( &citekeys );
}

static void
clean_ref( bibl *bin, param *p )
{
	if ( p->cleanf ) p->cleanf( bin, p );
}

static int 
convert_ref( bibl *bin, char *fname, bibl *bout, param *p )
{
	fields *rin, *rout;
	int reftype = 0, ok;
	long i;

	for ( i=0; i<bin->nrefs; ++i ) {
		rin = bin->ref[i];
		rout = fields_new();
		if ( !rout ) return BIBL_ERR_MEMERR;
		if ( p->typef ) 
			reftype = p->typef( rin, fname, i+1, p, p->all, p->nall );
		ok = p->convertf( rin, rout, reftype, p, p->all, p->nall );
		if ( ok!=BIBL_OK ) return ok;
		if ( p->all ) {
			ok = process_alwaysadd( rout, reftype, p );
			if ( ok!=BIBL_OK ) return ok;
			ok = process_defaultadd( rout, reftype, p );
			if ( ok!=BIBL_OK ) return ok;
		}
		bibl_addref( bout, rout );
	}
	uniqueify_citekeys( bout );
	return BIBL_OK;
}

int
bibl_read( bibl *b, FILE *fp, char *filename, param *p )
{
	int ret, ok;
	param lp;
	bibl bin;

	if ( !b ) return BIBL_ERR_BADINPUT;
	if ( !fp ) return BIBL_ERR_BADINPUT;
	if ( !p ) return BIBL_ERR_BADINPUT;
	if ( bibl_illegalinmode( p->readformat ) ) return BIBL_ERR_BADINPUT;

	bibl_setreadparams( &lp, p );
	bibl_init( &bin );

	ret = read_ref( fp, &bin, filename, &lp );
	if ( ret!=BIBL_OK ) return ret;

	if ( debug_set( p ) ) {
		fflush( stdout );
		report_params( stderr, "bibl_read", &lp );
		fprintf( stderr, "-------------------raw_input start for bibl_read\n");
		bibl_verbose0( &bin );
		fprintf( stderr, "-------------------raw_input end for bibl_read\n" );
		fflush( stderr );
	}

	if ( !lp.output_raw || ( lp.output_raw & BIBL_RAW_WITHCHARCONVERT ) ) {
		ok = bibl_fixcharsets( &bin, &lp );
		if ( !ok ) return BIBL_ERR_MEMERR;
		if ( debug_set( p ) ) {
			fprintf( stderr, "-------------------post_fixcharsets start for bibl_read\n");
			bibl_verbose0( &bin );
			fprintf( stderr, "-------------------post_fixcharsets end for bibl_read\n" );
			fflush( stderr );
		}
	}
	if ( !lp.output_raw ) {
		clean_ref( &bin, &lp );
		if ( debug_set( p ) ) {
			fprintf( stderr, "-------------------post_clean_ref start for bibl_read\n");
			bibl_verbose0( &bin );
			fprintf( stderr, "-------------------post_clean_ref end for bibl_read\n" );
			fflush( stderr );
		}
		ok = convert_ref( &bin, filename, b, &lp );
		if ( ok!=BIBL_OK ) return ok;
		if ( debug_set( p ) ) {
			fprintf( stderr, "-------------------post_convert_ref start for bibl_read\n");
			bibl_verbose0( &bin );
			fprintf( stderr, "-------------------post_convert_ref end for bibl_read\n" );
			fflush( stderr );
		}
	} else {
		if ( debug_set( p ) ) {
			fprintf( stderr, "-------------------here1 start for bibl_read\n");
			bibl_verbose0( &bin );
			fprintf( stderr, "-------------------here1 end for bibl_read\n" );
			fflush( stderr );
		}
		ok = bibl_copy( b, &bin );
		if ( !ok ) return BIBL_ERR_MEMERR;
	}
	if ( !lp.output_raw || ( lp.output_raw & BIBL_RAW_WITHMAKEREFID ) )
		bibl_checkrefid( b, &lp );

	bibl_free( &bin );

	return BIBL_OK;
}

static FILE *
singlerefname( fields *reffields, long nref, int mode )
{
	char outfile[2048];
	char suffix[5] = "xml";
	FILE *fp;
	long count;
	int  found;
	if      ( mode==BIBL_ADSABSOUT )     strcpy( suffix, "ads" );
	else if ( mode==BIBL_BIBTEXOUT )     strcpy( suffix, "bib" );
	else if ( mode==BIBL_ENDNOTEOUT )    strcpy( suffix, "end" );
	else if ( mode==BIBL_ISIOUT )        strcpy( suffix, "isi" );
	else if ( mode==BIBL_MODSOUT )       strcpy( suffix, "xml" );
	else if ( mode==BIBL_RISOUT )        strcpy( suffix, "ris" );
	else if ( mode==BIBL_WORD2007OUT )   strcpy( suffix, "xml" );
	found = fields_find( reffields, "REFNUM", 0 );
	/* find new filename based on reference */
	if ( found!=-1 ) {
		sprintf( outfile,"%s.%s",reffields->data[found].data, suffix );
	} else  sprintf( outfile,"%ld.%s",nref, suffix );
	count = 0;
	fp = fopen( outfile, "r" );
	while ( fp ) {
		fclose(fp);
		count++;
		if ( count==60000 ) return NULL;
		if ( found!=-1 )
			sprintf( outfile, "%s_%ld.%s", 
				reffields->data[found].data, count, suffix  );
		else sprintf( outfile,"%ld_%ld.%s",nref, count, suffix );
		fp = fopen( outfile, "r" );
	}
	return fopen( outfile, "w" );
}

static int
output_bibl( FILE *fp, bibl *b, param *p )
{
	long i;
	if ( !p->singlerefperfile && p->headerf ) p->headerf( fp, p );
	for ( i=0; i<b->nrefs; ++i ) {
		if ( p->singlerefperfile ) { 
			fp = singlerefname( b->ref[i], i, p->writeformat );
			if ( fp ) {
				if ( p->headerf ) p->headerf( fp, p );
			} else return BIBL_ERR_CANTOPEN;
		}
		p->writef( b->ref[i], fp, p, i );
		if ( p->singlerefperfile ) {
			if ( p->footerf ) p->footerf( fp );
			fclose( fp );
		}
	}
	if ( !p->singlerefperfile && p->footerf ) p->footerf( fp );
	return 1;
}

int
bibl_write( bibl *b, FILE *fp, param *p )
{
	param lp;
	int ok;

	if ( !b ) return BIBL_ERR_BADINPUT;
	if ( !p ) return BIBL_ERR_BADINPUT;
	if ( bibl_illegaloutmode( p->writeformat ) ) return BIBL_ERR_BADINPUT;
	if ( !fp && ( !p || !p->singlerefperfile ) ) return BIBL_ERR_BADINPUT;

	bibl_setwriteparams( &lp, p );

	ok = bibl_fixcharsets( b, &lp );
	if ( !ok ) return BIBL_ERR_MEMERR;

	if ( debug_set( p ) ) report_params( stderr, "bibl_write", &lp );

	ok = output_bibl( fp, b, &lp );
	if ( !ok ) return BIBL_ERR_MEMERR;

	return BIBL_OK;
}

