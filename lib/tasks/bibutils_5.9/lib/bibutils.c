/*
 * bibutils.c
 *
 * Copyright (c) Chris Putnam 2005-2016
 *
 * Source code released under the GPL version 2
 *
 */
#include <stdio.h>
#include <stdlib.h>
#include "bibutils.h"
#include "bibformats.h"

void
bibl_initparams( param *p, int readmode, int writemode, char *progname )
{

	switch ( readmode ) {
	case BIBL_BIBTEXIN:     bibtexin_initparams( p, progname ); break;
	case BIBL_BIBLATEXIN:   biblatexin_initparams( p, progname ); break;
	case BIBL_COPACIN:      copacin_initparams( p, progname ); break;
	case BIBL_EBIIN:        ebiin_initparams( p, progname ); break;
	case BIBL_ENDNOTEIN:    endin_initparams( p, progname ); break;
	case BIBL_ENDNOTEXMLIN: endxmlin_initparams( p, progname ); break;
	case BIBL_MEDLINEIN:    medin_initparams( p, progname ); break;
	case BIBL_MODSIN:       modsin_initparams( p, progname ); break;
	case BIBL_RISIN:        risin_initparams( p, progname ); break;
	case BIBL_WORDIN:       wordin_initparams( p, progname ); break;
	default: /* internal error */;
	}

	switch ( writemode ) {
	case BIBL_ADSABSOUT:   adsout_initparams( p, progname ); break;
	case BIBL_BIBTEXOUT:   bibtexout_initparams( p, progname ); break;
	case BIBL_ENDNOTEOUT:  endout_initparams( p, progname ); break;
	case BIBL_ISIOUT:      isiout_initparams( p, progname ); break;
	case BIBL_MODSOUT:     modsout_initparams( p, progname ); break;
	case BIBL_RISOUT:      risout_initparams( p, progname ); break;
	case BIBL_WORD2007OUT: wordout_initparams( p, progname ); break;
	default: /* internal error */;
	}
}

